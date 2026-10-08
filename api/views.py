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
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from .filters import MaquinariaFilter
from .models import Maquinaria, Carro, ItemCarro, Contrato, DetalleContrato
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
            
            # El stock se descuenta cuando el Ejecutivo registra el pago.
            carro.items.all().delete()
            return Response(ContratoSerializer(contrato).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['patch'], permission_classes=[IsEjecutivo])
    def estado(self, request, pk=None):
        """Aplica transiciones válidas y ajusta stock dentro de una transacción."""
        contrato = self.get_object()
        nuevo_estado = request.data.get('estado')
        
        with transaction.atomic():
            # El bloqueo evita ejecutar dos veces una transición concurrente.
            contrato = Contrato.objects.select_for_update().get(pk=contrato.pk)
            estados_permitidos = {
                'PENDIENTE': {'PAGADO', 'CANCELADO'},
                'PAGADO': {'ENTREGADO', 'CANCELADO'},
                'ENTREGADO': {'COMPLETADO', 'CANCELADO'},
            }
            if nuevo_estado not in estados_permitidos.get(contrato.estado, set()):
                return Response({"error": f"Transición no permitida: {contrato.estado} → {nuevo_estado}."}, status=status.HTTP_400_BAD_REQUEST)
            detalles = list(contrato.detalles.select_related('maquinaria').order_by('maquinaria_id'))
            ids = sorted({d.maquinaria_id for d in detalles if d.maquinaria_id})
            maquinarias = {m.id: m for m in Maquinaria.objects.select_for_update().filter(id__in=ids).order_by('id')}
            # Solo la transición a PAGADO descuenta unidades del inventario.
            if nuevo_estado == 'PAGADO':
                requeridas = {}
                for detalle in detalles:
                    if detalle.maquinaria_id:
                        requeridas[detalle.maquinaria_id] = requeridas.get(detalle.maquinaria_id, 0) + 1
                for maquina_id, cantidad in requeridas.items():
                    if maquinarias[maquina_id].stock_disponible < cantidad:
                        return Response({"error": f"Stock insuficiente para {maquinarias[maquina_id].nombre}."}, status=status.HTTP_400_BAD_REQUEST)
                    # La validación combina stock libre y reservas con fechas solapadas.
                    contratos_activos = DetalleContrato.objects.filter(
                        maquinaria_id=maquina_id, contrato__estado__in=['PAGADO', 'ENTREGADO']
                    )
                    unidades_fisicas = maquinarias[maquina_id].stock_disponible + contratos_activos.count()
                    nuevos = [d for d in detalles if d.maquinaria_id == maquina_id]
                    for detalle in nuevos:
                        ocupadas_en_periodo = contratos_activos.filter(
                            fecha_inicio__lt=detalle.fecha_fin, fecha_fin__gt=detalle.fecha_inicio
                        ).count()
                        nuevas_en_periodo = sum(
                            1 for otro in nuevos
                            if otro.fecha_inicio < detalle.fecha_fin and otro.fecha_fin > detalle.fecha_inicio
                        )
                        if ocupadas_en_periodo + nuevas_en_periodo > unidades_fisicas:
                            return Response({"error": f"No hay unidades de {maquinarias[maquina_id].nombre} disponibles para las fechas solicitadas."}, status=status.HTTP_400_BAD_REQUEST)
                for maquina_id, cantidad in requeridas.items():
                    Maquinaria.objects.filter(pk=maquina_id).update(stock_disponible=F('stock_disponible') - cantidad)

            # Cancelar o completar devuelve las unidades previamente descontadas.
            elif nuevo_estado in ['CANCELADO', 'COMPLETADO'] and contrato.estado in ['PAGADO', 'ENTREGADO']:
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
