"""
Definición de modelos y esquemas relacionales de la base de datos.
Incluye el control de roles de usuario, catálogo y transacciones.
"""
import uuid

from django.db import models
from django.contrib.auth.models import AbstractUser

class Usuario(AbstractUser):
    # Definición de roles de acceso al sistema (RBAC)
    ROLE_CHOICES = (
        ('CLIENTE', 'Empresa Constructora'),
        ('ADMIN', 'Ejecutivo de Arriendos'),
    )
    rol = models.CharField(max_length=10, choices=ROLE_CHOICES, default='CLIENTE')

class Maquinaria(models.Model):
    """Equipo arrendable con tarifa, garantía, stock y fotografía de catálogo."""
    nombre = models.CharField(max_length=100)
    categoria = models.CharField(max_length=50)
    tarifa_diaria = models.DecimalField(max_digits=10, decimal_places=2)
    garantia_fija = models.DecimalField(max_digits=10, decimal_places=2)
    stock_disponible = models.PositiveIntegerField(default=0)
    # El catálogo usa esta URL para mostrar la fotografía de cada unidad/equipo.
    imagen_url = models.URLField(max_length=500, blank=True, default='')

class Carro(models.Model):
    """Carro persistente único asociado a una cuenta de usuario."""
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE, related_name='carro')
    creado_en = models.DateTimeField(auto_now_add=True)

class ItemCarro(models.Model):
    """Período solicitado para una maquinaria dentro del carro."""
    carro = models.ForeignKey(Carro, on_delete=models.CASCADE, related_name='items')
    maquinaria = models.ForeignKey(Maquinaria, on_delete=models.CASCADE)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['carro', 'maquinaria', 'fecha_inicio', 'fecha_fin'],
                name='item_carro_unico_por_periodo',
            ),
        ]

    @property
    def dias_arriendo(self):
        """Devuelve los días entre las fechas de inicio y fin."""
        return (self.fecha_fin - self.fecha_inicio).days

    @property
    def costo_calculado(self):
        """Suma la tarifa diaria del período y la garantía fija."""
        return (self.maquinaria.tarifa_diaria * self.dias_arriendo) + self.maquinaria.garantia_fija

class Contrato(models.Model):
    """Orden histórica con estados válidos del ciclo de arriendo."""
    ESTADOS = (
        ('PENDIENTE', 'Pendiente'),
        ('PAGADO', 'Pagado'),
        ('ENTREGADO', 'Entregado'),
        ('COMPLETADO', 'Completado'),
        ('CANCELADO', 'Cancelado'),
    )
    codigo_uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    estado = models.CharField(max_length=15, choices=ESTADOS, default='PENDIENTE')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    total = models.DecimalField(max_digits=12, decimal_places=2)

class DetalleContrato(models.Model):
    """Conserva máquina, período y subtotal de cada contrato."""
    contrato = models.ForeignKey(Contrato, on_delete=models.CASCADE, related_name='detalles')
    maquinaria = models.ForeignKey(Maquinaria, on_delete=models.SET_NULL, null=True)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
