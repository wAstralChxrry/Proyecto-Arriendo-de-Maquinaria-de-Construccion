"""
Vistas de la API (ViewSets). Contienen la lógica principal del sistema.
Gestionan las peticiones HTTP, aplican permisos y ejecutan operaciones sobre la base de datos.
"""
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from .models import Maquinaria, Carro, ItemCarro, Contrato, DetalleContrato
from .serializers import MaquinariaSerializer, CarroSerializer, ItemCarroSerializer, ContratoSerializer

class IsEjecutivo(permissions.BasePermission):
    # Permiso personalizado (RBAC): permite el acceso únicamente a usuarios con rol ADMIN o con permisos de superusuario.
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and (request.user.rol == 'ADMIN' or request.user.is_superuser))

class MaquinariaViewSet(viewsets.ModelViewSet):
    # Endpoint para la gestión del catálogo de maquinarias
    queryset = Maquinaria.objects.all()
    serializer_class = MaquinariaSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['categoria', 'tarifa_diaria']

    def get_permissions(self):
        # Las operaciones de lectura (list, retrieve) son públicas y no requieren autenticación
        if self.action in ['list', 'retrieve']:
            permission_classes = [permissions.AllowAny]
        else:
            # Las operaciones de escritura (create, update, delete) requieren rol de Ejecutivo (Admin)
            permission_classes = [IsEjecutivo]
        return [permission() for permission in permission_classes]

class CarroViewSet(viewsets.ViewSet):
    # Endpoint para la gestión del carro de compras. Requiere autenticación.
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        # Retorna el carro persistente del usuario. Si no existe, lo crea automáticamente.
        carro, created = Carro.objects.get_or_create(usuario=request.user)
        serializer = CarroSerializer(carro)
        return Response(serializer.data)

    def create(self, request):
        # Agrega un nuevo ítem (maquinaria) al carro del usuario autenticado
        carro, _ = Carro.objects.get_or_create(usuario=request.user)
        serializer = ItemCarroSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(carro=carro)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        # Elimina un ítem específico del carro del usuario autenticado
        try:
            item = ItemCarro.objects.get(pk=pk, carro__usuario=request.user)
            item.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ItemCarro.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

class ContratoViewSet(viewsets.ModelViewSet):
    # Endpoint para la gestión de contratos. Requiere autenticación.
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ContratoSerializer

    def get_queryset(self):
        # Los Administradores visualizan todos los contratos; los Clientes solo los propios
        if self.request.user.rol == 'ADMIN' or self.request.user.is_superuser:
            return Contrato.objects.all()
        return Contrato.objects.filter(usuario=self.request.user)

    @action(detail=False, methods=['post'])
    def checkout(self, request):
        # Procesa el carro activo y genera un contrato formal en estado PENDIENTE
        carro = Carro.objects.filter(usuario=request.user).first()
        if not carro or not carro.items.exists():
            return Response({"error": "El carro está vacío."}, status=status.HTTP_400_BAD_REQUEST)

        # transaction.atomic() garantiza que la operación sea atómica: si ocurre un error, se revierten todos los cambios
        with transaction.atomic():
            # Validación previa de disponibilidad de stock por cada ítem del carro
            for item in carro.items.all():
                if item.maquinaria.stock_disponible < 1:
                    return Response(
                        {"error": f"La maquinaria {item.maquinaria.nombre} no tiene stock disponible para arriendo."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            # Cálculo del total y creación del contrato
            total = sum([item.costo_calculado for item in carro.items.all()])
            contrato = Contrato.objects.create(usuario=request.user, total=total, estado='PENDIENTE')

            # Registro del detalle de cada máquina arrendada en el contrato
            for item in carro.items.all():
                DetalleContrato.objects.create(
                    contrato=contrato,
                    maquinaria=item.maquinaria,
                    fecha_inicio=item.fecha_inicio,
                    fecha_fin=item.fecha_fin,
                    subtotal=item.costo_calculado
                )
            
            # Liquidación del carro. El stock físico no se descuenta en esta etapa.
            carro.items.all().delete()
            return Response(ContratoSerializer(contrato).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['patch'], permission_classes=[IsEjecutivo])
    def estado(self, request, pk=None):
        # Actualiza el estado de un contrato. Operación restringida al rol Ejecutivo (Admin).
        contrato = self.get_object()
        nuevo_estado = request.data.get('estado')
        
        with transaction.atomic():
            # Al transición a PAGADO: se verifica stock y se descuenta el inventario físico
            if nuevo_estado == 'PAGADO' and contrato.estado == 'PENDIENTE':
                for detalle in contrato.detalles.all():
                    if detalle.maquinaria.stock_disponible < 1:
                        return Response({"error": f"Stock insuficiente para {detalle.maquinaria.nombre}."}, status=status.HTTP_400_BAD_REQUEST)
                    detalle.maquinaria.stock_disponible -= 1
                    detalle.maquinaria.save()

            # Al transición a CANCELADO o COMPLETADO: se repone el stock al inventario
            elif nuevo_estado in ['CANCELADO', 'COMPLETADO'] and contrato.estado in ['PAGADO', 'ENTREGADO']:
                for detalle in contrato.detalles.all():
                    detalle.maquinaria.stock_disponible += 1
                    detalle.maquinaria.save()

            contrato.estado = nuevo_estado
            contrato.save()
            return Response(ContratoSerializer(contrato).data)
