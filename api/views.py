"""
Vistas de la API (ViewSets). Contienen la lógica principal del sistema.
Gestionan las peticiones HTTP, aplican permisos y ejecutan operaciones sobre la base de datos.
"""
from rest_framework import mixins, viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter
from django.db import IntegrityError, transaction
from django.db.models import F
import uuid
import logging
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP
from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from transbank.common.integration_api_keys import IntegrationApiKeys
from transbank.common.integration_commerce_codes import IntegrationCommerceCodes
from transbank.common.integration_type import IntegrationType
from transbank.common.options import WebpayOptions
from transbank.webpay.webpay_plus.transaction import Transaction as WebpayTransaction
from transbank.error.transbank_error import TransbankError
from .filters import MaquinariaFilter
from .models import Maquinaria, Carro, ItemCarro, Contrato, DetalleContrato

logger = logging.getLogger(__name__)


def _webpay_transaction():
    """Crea el cliente Webpay con credenciales públicas de integración de Transbank."""
    options = WebpayOptions(
        IntegrationCommerceCodes.WEBPAY_PLUS,
        IntegrationApiKeys.WEBPAY,
        IntegrationType.TEST,
        timeout=30,
    )
    return WebpayTransaction(options)


def _webpay_amount(contrato):
    """Webpay recibe el monto en pesos como entero."""
    return int(Decimal(contrato.total).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def _webpay_buy_order(contrato):
    return f"TW{contrato.pk}-{contrato.codigo_uuid.hex[:12]}"


def _release_webpay_attempt(contrato, token):
    Contrato.objects.filter(pk=contrato.pk, webpay_token=token).update(
        webpay_token='', webpay_url='', webpay_token_created_at=None
    )
from .serializers import MaquinariaSerializer, CarroSerializer, ItemCarroSerializer, ContratoSerializer, RegistroSerializer

class IsEjecutivo(permissions.BasePermission):
    """Limita las operaciones de gestión al Ejecutivo de Arriendos."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and (request.user.rol == 'ADMIN' or request.user.is_superuser))

class IsCliente(permissions.BasePermission):
    """Limita las operaciones de arriendo a cuentas de cliente."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.rol == 'CLIENTE' and not request.user.is_superuser)

class MaquinariaViewSet(viewsets.ModelViewSet):
    """Expone el catálogo público y reserva su edición al Ejecutivo."""
    queryset = Maquinaria.objects.all()
    serializer_class = MaquinariaSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = MaquinariaFilter
    search_fields = ['nombre', 'categoria']

    def get_permissions(self):
        """Deja público el catálogo y limita cualquier escritura al Ejecutivo."""
        if self.action in ['list', 'retrieve']:
            permission_classes = [permissions.AllowAny]
        else:
            permission_classes = [IsEjecutivo]
        return [permission() for permission in permission_classes]

class CarroViewSet(viewsets.ViewSet):
    """Permite a cada cliente consultar y modificar su carro persistente."""
    permission_classes = [IsCliente]
    serializer_class = CarroSerializer
    lookup_value_regex = '[0-9]+'

    @extend_schema(responses=CarroSerializer)
    def list(self, request):
        """Devuelve el carro del cliente y lo crea si aún no existe."""
        carro, _ = Carro.objects.get_or_create(usuario=request.user)
        serializer = CarroSerializer(carro)
        return Response(serializer.data)

    @extend_schema(request=ItemCarroSerializer, responses=ItemCarroSerializer)
    def create(self, request):
        """Valida y guarda un período de arriendo en el carro del cliente."""
        carro, _ = Carro.objects.get_or_create(usuario=request.user)
        serializer = ItemCarroSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            try:
                serializer.save(carro=carro)
            except IntegrityError:
                return Response(
                    {"non_field_errors": ["Esa maquinaria ya está en el carro para ese período."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        parameters=[OpenApiParameter('pk', int, OpenApiParameter.PATH)],
        responses={204: None, 404: None},
    )
    def destroy(self, request, pk=None):
        """Elimina un ítem solo si pertenece al cliente autenticado."""
        try:
            item = ItemCarro.objects.get(pk=pk, carro__usuario=request.user)
            item.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ItemCarro.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

class ContratoViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """Expone lectura, checkout y cambios controlados de estado del contrato."""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ContratoSerializer
    queryset = Contrato.objects.none()

    def get_queryset(self):
        """Restringe los contratos propios, salvo para el Ejecutivo."""
        if getattr(self, 'swagger_fake_view', False) or not self.request.user.is_authenticated:
            return Contrato.objects.none()
        if self.request.user.rol == 'ADMIN' or self.request.user.is_superuser:
            return Contrato.objects.all()
        return Contrato.objects.filter(usuario=self.request.user)

    @action(detail=False, methods=['post'], permission_classes=[IsCliente])
    def checkout(self, request):
        """Convierte el carro en un contrato pendiente con sus detalles históricos."""
        carro = Carro.objects.filter(usuario=request.user).first()
        if not carro or not carro.items.exists():
            return Response({"error": "El carro está vacío."}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            # El bloqueo impide convertir el mismo carro en dos contratos simultáneos.
            carro = Carro.objects.select_for_update().get(pk=carro.pk)
            # Los bloqueos de inventario serializan las confirmaciones concurrentes.
            items = list(carro.items.select_related('maquinaria').order_by('maquinaria_id'))
            ids = sorted({item.maquinaria_id for item in items})
            maquinarias = {m.id: m for m in Maquinaria.objects.select_for_update().filter(id__in=ids).order_by('id')}
            for item in items:
                item.maquinaria = maquinarias[item.maquinaria_id]
                activos = DetalleContrato.objects.filter(
                    maquinaria=item.maquinaria, contrato__estado__in=['PAGADO', 'ENTREGADO']
                )
                unidades_fisicas = item.maquinaria.stock_disponible + activos.count()
                ocupadas = activos.filter(fecha_inicio__lt=item.fecha_fin, fecha_fin__gt=item.fecha_inicio).count()
                nuevas = sum(
                    1 for otro in items
                    if otro.maquinaria_id == item.maquinaria_id
                    and otro.fecha_inicio < item.fecha_fin and otro.fecha_fin > item.fecha_inicio
                )
                if ocupadas + nuevas > unidades_fisicas:
                    return Response({"error": f"{item.maquinaria.nombre} ya no está disponible para esas fechas."}, status=status.HTTP_400_BAD_REQUEST)

            # El servidor calcula el total con tarifas y garantías vigentes.
            total = sum((item.costo_calculado for item in items), start=0)
            contrato = Contrato.objects.create(usuario=request.user, total=total, estado='PENDIENTE')

            # Cada detalle conserva la máquina, sus fechas y su subtotal histórico.
            for item in items:
                DetalleContrato.objects.create(
                    contrato=contrato,
                    maquinaria=item.maquinaria,
                    fecha_inicio=item.fecha_inicio,
                    fecha_fin=item.fecha_fin,
                    subtotal=item.costo_calculado
                )
            
            # La solicitud queda pendiente y no reserva stock hasta el pago demo.
            carro.items.all().delete()
            return Response(ContratoSerializer(contrato).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='pago-demo', permission_classes=[IsCliente])
    def pago_demo(self, request, pk=None):
        """Inicia un pago Webpay Plus en el ambiente de integración."""
        contrato = self.get_object()
        return_url = getattr(settings, 'WEBPAY_RETURN_URL', '') or request.build_absolute_uri(
            reverse('webpay-return')
        )
        # El bloqueo de contrato evita que dos clics creen sesiones Webpay distintas.
        with transaction.atomic():
            contrato = Contrato.objects.select_for_update().get(pk=contrato.pk)
            if contrato.estado != 'APROBADO':
                return Response(
                    {"error": "El ejecutivo debe aprobar el arriendo antes del pago."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if (contrato.webpay_token and contrato.webpay_url and contrato.webpay_token_created_at
                    and contrato.webpay_token_created_at > timezone.now() - timedelta(minutes=15)):
                return Response({"url": contrato.webpay_url, "token": contrato.webpay_token})
            try:
                response = _webpay_transaction().create(
                    _webpay_buy_order(contrato),
                    str(contrato.codigo_uuid),
                    _webpay_amount(contrato),
                    return_url,
                )
            except TransbankError:
                logger.exception('Transbank rechazó la creación del pago para contrato %s', contrato.pk)
                return Response(
                    {"error": "Webpay no pudo iniciar el pago. Intenta nuevamente en unos minutos."},
                    status=status.HTTP_502_BAD_GATEWAY,
                )
            except Exception:
                logger.exception('No se pudo iniciar el pago Webpay para contrato %s', contrato.pk)
                return Response(
                    {"error": "No se pudo conectar con Webpay. Intenta nuevamente en unos minutos."},
                    status=status.HTTP_502_BAD_GATEWAY,
                )
            if (not response.get('token') or not response.get('url')
                    or not response['url'].startswith('https://webpay3gint.transbank.cl/')):
                logger.error('Transbank devolvió una respuesta incompleta al iniciar contrato %s', contrato.pk)
                return Response(
                    {"error": "Webpay devolvió una respuesta incompleta."},
                    status=status.HTTP_502_BAD_GATEWAY,
                )
            contrato.webpay_token = response['token']
            contrato.webpay_url = response['url']
            contrato.webpay_token_created_at = timezone.now()
            contrato.save(update_fields=['webpay_token', 'webpay_url', 'webpay_token_created_at'])

        return Response({"url": response['url'], "token": response['token']})

    @action(detail=True, methods=['patch'], permission_classes=[IsEjecutivo])
    def estado(self, request, pk=None):
        """Aplica transiciones válidas y ajusta stock dentro de una transacción."""
        contrato = self.get_object()
        nuevo_estado = request.data.get('estado')
        
        with transaction.atomic():
            # El bloqueo evita ejecutar dos veces una transición concurrente.
            contrato = Contrato.objects.select_for_update().get(pk=contrato.pk)
            if contrato.estado == 'APROBADO' and contrato.webpay_token:
                intento_activo = (
                    contrato.webpay_token_created_at
                    and contrato.webpay_token_created_at > timezone.now() - timedelta(minutes=15)
                )
                if nuevo_estado == 'CANCELADO' and intento_activo:
                    return Response(
                        {"error": "Hay un pago Webpay en curso. Espera a que termine antes de cancelar."},
                        status=status.HTTP_409_CONFLICT,
                    )
                if not intento_activo:
                    contrato.webpay_token = ''
                    contrato.webpay_url = ''
                    contrato.webpay_token_created_at = None
            estados_permitidos = {
                'PENDIENTE': {'APROBADO', 'CANCELADO'},
                'APROBADO': {'CANCELADO'},
                'PAGADO': {'ENTREGADO', 'CANCELADO'},
                'ENTREGADO': {'COMPLETADO', 'CANCELADO'},
            }
            if nuevo_estado not in estados_permitidos.get(contrato.estado, set()):
                return Response({"error": f"Transición no permitida: {contrato.estado} → {nuevo_estado}."}, status=status.HTTP_400_BAD_REQUEST)
            detalles = list(contrato.detalles.select_related('maquinaria').order_by('maquinaria_id'))
            ids = sorted({d.maquinaria_id for d in detalles if d.maquinaria_id})
            maquinarias = {m.id: m for m in Maquinaria.objects.select_for_update().filter(id__in=ids).order_by('id')}
            # Cancelar o completar devuelve las unidades descontadas al pagar.
            if nuevo_estado in ['CANCELADO', 'COMPLETADO'] and contrato.estado in ['PAGADO', 'ENTREGADO']:
                for maquina_id in ids:
                    cantidad = sum(1 for d in detalles if d.maquinaria_id == maquina_id)
                    Maquinaria.objects.filter(pk=maquina_id).update(stock_disponible=F('stock_disponible') + cantidad)

            contrato.estado = nuevo_estado
            contrato.save()
            return Response(ContratoSerializer(contrato).data)

class RegistroViewSet(viewsets.ViewSet):
    """Crea cuentas cliente y no permite asignar el rol de Ejecutivo."""
    permission_classes = [permissions.AllowAny]
    serializer_class = RegistroSerializer

    @extend_schema(request=RegistroSerializer, responses={201: RegistroSerializer})
    def create(self, request):
        """Valida las credenciales y crea una cuenta con rol cliente."""
        serializer = RegistroSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        usuario = serializer.save()
        return Response({"id": usuario.id, "username": usuario.username, "email": usuario.email}, status=status.HTTP_201_CREATED)


def _complete_webpay_payment(contrato, token, result):
    """Valida la respuesta de Transbank y descuenta inventario una sola vez."""
    try:
        response_code = int(result.get('response_code', -1))
        response_amount = int(Decimal(str(result.get('amount', 0))))
    except (ValueError, TypeError, ArithmeticError):
        response_code = -1
        response_amount = -1
    if (result.get('status') != 'AUTHORIZED'
            or response_code != 0
            or result.get('buy_order') != _webpay_buy_order(contrato)
            or response_amount != _webpay_amount(contrato)):
        _release_webpay_attempt(contrato, token)
        return 'rechazado'

    with transaction.atomic():
        contrato = Contrato.objects.select_for_update().get(pk=contrato.pk)
        if contrato.webpay_token != token or contrato.estado != 'APROBADO':
            return 'invalido'

        detalles = list(contrato.detalles.select_related('maquinaria').order_by('maquinaria_id'))
        if not detalles or any(detalle.maquinaria_id is None for detalle in detalles):
            return 'sin_stock'

        ids = sorted({detalle.maquinaria_id for detalle in detalles})
        maquinarias = {
            maquinaria.id: maquinaria
            for maquinaria in Maquinaria.objects.select_for_update().filter(id__in=ids).order_by('id')
        }
        requeridas = {}
        for detalle in detalles:
            requeridas[detalle.maquinaria_id] = requeridas.get(detalle.maquinaria_id, 0) + 1

        for maquinaria_id, cantidad in requeridas.items():
            maquinaria = maquinarias.get(maquinaria_id)
            if not maquinaria or maquinaria.stock_disponible < cantidad:
                return 'sin_stock'

            activos = DetalleContrato.objects.filter(
                maquinaria_id=maquinaria_id,
                contrato__estado__in=['PAGADO', 'ENTREGADO'],
            )
            unidades_fisicas = maquinaria.stock_disponible + activos.count()
            solicitados = [detalle for detalle in detalles if detalle.maquinaria_id == maquinaria_id]
            for detalle in solicitados:
                ocupadas = activos.filter(
                    fecha_inicio__lt=detalle.fecha_fin,
                    fecha_fin__gt=detalle.fecha_inicio,
                ).count()
                nuevas = sum(
                    1 for otro in solicitados
                    if otro.fecha_inicio < detalle.fecha_fin and otro.fecha_fin > detalle.fecha_inicio
                )
                if ocupadas + nuevas > unidades_fisicas:
                    return 'sin_stock'

        for maquinaria_id, cantidad in requeridas.items():
            Maquinaria.objects.filter(pk=maquinaria_id).update(stock_disponible=F('stock_disponible') - cantidad)

        contrato.estado = 'PAGADO'
        contrato.referencia_pago = f"WEBPAY-{result.get('authorization_code', 'OK')}"
        contrato.webpay_token = ''
        contrato.webpay_url = ''
        contrato.webpay_token_created_at = None
        contrato.save(update_fields=[
            'estado', 'referencia_pago', 'webpay_token', 'webpay_url', 'webpay_token_created_at'
        ])
    return 'exitoso'


@csrf_exempt
def webpay_return(request):
    """Recibe el retorno de Webpay y confirma el pago directamente con Transbank."""
    token = request.POST.get('token_ws') or request.GET.get('token_ws')
    if not token:
        aborted_token = request.POST.get('TBK_TOKEN') or request.GET.get('TBK_TOKEN')
        if aborted_token:
            contrato = Contrato.objects.filter(webpay_token=aborted_token).first()
            if contrato:
                _release_webpay_attempt(contrato, aborted_token)
            return redirect('/?pago=cancelado#mis-arriendos')
        return redirect('/?pago=error#mis-arriendos')

    contrato = Contrato.objects.filter(webpay_token=token).first()
    if not contrato:
        return redirect('/?pago=error#mis-arriendos')

    try:
        result = _webpay_transaction().commit(token)
    except TransbankError:
        logger.exception('Transbank no pudo confirmar el pago del contrato %s', contrato.pk)
        return redirect('/?pago=error#mis-arriendos')
    except Exception:
        logger.exception('Falló la confirmación Webpay del contrato %s', contrato.pk)
        return redirect('/?pago=error#mis-arriendos')

    outcome = _complete_webpay_payment(contrato, token, result)
    if outcome in ('sin_stock', 'invalido'):
        try:
            _webpay_transaction().refund(token, _webpay_amount(contrato))
            _release_webpay_attempt(contrato, token)
            outcome = 'sin_stock' if outcome == 'sin_stock' else 'invalido'
        except Exception:
            logger.exception('No se pudo revertir un pago autorizado sin stock para contrato %s', contrato.pk)
            outcome = 'error'
    return redirect(f'/?pago={outcome}#mis-arriendos')
