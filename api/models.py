"""
Definición de modelos y esquemas relacionales de la base de datos.
Incluye el control de roles de usuario, catálogo y transacciones.
"""
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
    # Catálogo de inventario de maquinarias disponibles
    nombre = models.CharField(max_length=100)
    categoria = models.CharField(max_length=50)
    tarifa_diaria = models.DecimalField(max_digits=10, decimal_places=2)
    garantia_fija = models.DecimalField(max_digits=10, decimal_places=2)
    stock_disponible = models.PositiveIntegerField(default=0)

class Carro(models.Model):
    # Relación uno a uno para garantizar la persistencia del carro por usuario
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE, related_name='carro')
    creado_en = models.DateTimeField(auto_now_add=True)

class ItemCarro(models.Model):
    # Ítems individuales dentro del carro de compras
    carro = models.ForeignKey(Carro, on_delete=models.CASCADE, related_name='items')
    maquinaria = models.ForeignKey(Maquinaria, on_delete=models.CASCADE)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()

    @property
    def dias_arriendo(self):
        # Cálculo de la duración total del arriendo
        return (self.fecha_fin - self.fecha_inicio).days

    @property
    def costo_calculado(self):
        # Cálculo del costo total (Tarifa diaria * días + Garantía)
        return (self.maquinaria.tarifa_diaria * self.dias_arriendo) + self.maquinaria.garantia_fija

class Contrato(models.Model):
    # Definición de estados para el ciclo de vida del contrato
    ESTADOS = (
        ('PENDIENTE', 'Pendiente'),
        ('PAGADO', 'Pagado'),
        ('ENTREGADO', 'Entregado'),
        ('COMPLETADO', 'Completado'),
        ('CANCELADO', 'Cancelado'),
    )
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    estado = models.CharField(max_length=15, choices=ESTADOS, default='PENDIENTE')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    total = models.DecimalField(max_digits=12, decimal_places=2)

class DetalleContrato(models.Model):
    # Registro histórico inmutable de las máquinas arrendadas por contrato
    contrato = models.ForeignKey(Contrato, on_delete=models.CASCADE, related_name='detalles')
    maquinaria = models.ForeignKey(Maquinaria, on_delete=models.SET_NULL, null=True)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
