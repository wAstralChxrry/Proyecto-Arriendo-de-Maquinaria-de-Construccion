"""
Aquí están las 'Vistas' (Endpoints). Es la lógica principal del sistema.
Reciben peticiones web y deciden qué hacer con la base de datos.
"""
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from .models import Maquinaria, Carro, ItemCarro, Contrato, DetalleContrato
from .serializers import MaquinariaSerializer, CarroSerializer, ItemCarroSerializer, ContratoSerializer

class IsEjecutivo(permissions.BasePermission):
    # Permiso de seguridad: Solo deja pasar si el usuario es 'ADMIN' o un Superusuario.
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and (request.user.rol == 'ADMIN' or request.user.is_superuser))

class MaquinariaViewSet(viewsets.ModelViewSet):
    # Punto de acceso para el catálogo de máquinas
    queryset = Maquinaria.objects.all()
    serializer_class = MaquinariaSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['categoria', 'tarifa_diaria']

    def get_permissions(self):
        # Si alguien solo quiere "ver" el catálogo (list) se permite a cualquiera.
        if self.action == 'list' or self.action == 'retrieve':
            permission_classes = [permissions.AllowAny]
        else:
            # Si alguien quiere crear, editar o borrar una máquina, DEBE ser Ejecutivo (Admin).
            permission_classes = [IsEjecutivo]
        return [permission() for permission in permission_classes]

class CarroViewSet(viewsets.ViewSet):
    # Controla el carrito de compras. Solo usuarios logueados pueden usarlo.
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        # Busca el carrito persistente del usuario, si no tiene, le crea uno nuevo.
        carro, created = Carro.objects.get_or_create(usuario=request.user)
        serializer = CarroSerializer(carro)
        return Response(serializer.data)

    def create(self, request):
        # Añadir un nuevo producto al carrito
        carro, _ = Carro.objects.get_or_create(usuario=request.user)
        serializer = ItemCarroSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(carro=carro)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        # Eliminar una máquina del carrito
        try:
            item = ItemCarro.objects.get(pk=pk, carro__usuario=request.user)
            item.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ItemCarro.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

class ContratoViewSet(viewsets.ModelViewSet):
    # Gestiona las compras (Contratos). Solo usuarios logueados.
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ContratoSerializer

    def get_queryset(self):
        # Un Ejecutivo puede ver TODOS los contratos. El Cliente solo ve los suyos.
        if self.request.user.rol == 'ADMIN' or self.request.user.is_superuser:
            return Contrato.objects.all()
        return Contrato.objects.filter(usuario=self.request.user)

    @action(detail=False, methods=['post'])
    def checkout(self, request):
        # 'Checkout' es cuando el Cliente le da a "Confirmar Compra".
        carro = Carro.objects.filter(usuario=request.user).first()
        if not carro or not carro.items.exists():
            return Response({"error": "El carro está vacío."}, status=status.HTTP_400_BAD_REQUEST)

        # transaction.atomic() sirve para que si algo falla, no se guarde nada a medias (seguridad).
        with transaction.atomic():
            # 1. Validamos que las máquinas que quiere tengan stock libre.
            for item in carro.items.all():
                if item.maquinaria.stock_disponible < 1:
                    return Response(
                        {"error": f"La maquinaria {item.maquinaria.nombre} no tiene stock disponible para arriendo."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            # 2. Sumamos todo el dinero y creamos el Contrato en estado PENDIENTE.
            total = sum([item.costo_calculado for item in carro.items.all()])
            contrato = Contrato.objects.create(usuario=request.user, total=total, estado='PENDIENTE')

            # 3. Guardamos los detalles de las máquinas arrendadas.
            for item in carro.items.all():
                DetalleContrato.objects.create(
                    contrato=contrato,
                    maquinaria=item.maquinaria,
                    fecha_inicio=item.fecha_inicio,
                    fecha_fin=item.fecha_fin,
                    subtotal=item.costo_calculado
                )
            
            # 4. Vaciamos el carrito del cliente. (¡OJO! El stock NO se ha descontado aún).
            carro.items.all().delete()
            return Response(ContratoSerializer(contrato).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['patch'], permission_classes=[IsEjecutivo])
    def estado(self, request, pk=None):
        # Cambiar el estado del contrato. SOLO puede hacerlo el Ejecutivo (IsEjecutivo).
        contrato = self.get_object()
        nuevo_estado = request.data.get('estado')
        
        with transaction.atomic():
            # Si el Ejecutivo marca que el cliente ya PAGÓ:
            if nuevo_estado == 'PAGADO' and contrato.estado == 'PENDIENTE':
                for detalle in contrato.detalles.all():
                    if detalle.maquinaria.stock_disponible < 1:
                        return Response({"error": f"Stock insuficiente para {detalle.maquinaria.nombre}."}, status=status.HTTP_400_BAD_REQUEST)
                    
                    # ¡AQUÍ descontamos el stock físico del catálogo!
                    detalle.maquinaria.stock_disponible -= 1
                    detalle.maquinaria.save()

            # Si el Ejecutivo CANCELA el contrato o lo da por COMPLETADO (ya devolvieron la máquina):
            elif nuevo_estado in ['CANCELADO', 'COMPLETADO'] and contrato.estado in ['PAGADO', 'ENTREGADO']:
                for detalle in contrato.detalles.all():
                    # ¡AQUÍ devolvemos el stock físico al catálogo!
                    detalle.maquinaria.stock_disponible += 1
                    detalle.maquinaria.save()

            contrato.estado = nuevo_estado
            contrato.save()
            return Response(ContratoSerializer(contrato).data)
