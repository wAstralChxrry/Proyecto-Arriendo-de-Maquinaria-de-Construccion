"""
En este archivo definimos las tablas de la base de datos (Modelos).
Cada 'class' representa una tabla en PostgreSQL.
"""
from django.db import models
from django.contrib.auth.models import AbstractUser

class Usuario(AbstractUser):
    # Aquí definimos los dos tipos de usuarios que pide el negocio.
    ROLE_CHOICES = (
        ('CLIENTE', 'Empresa Constructora'),
        ('ADMIN', 'Ejecutivo de Arriendos'),
    )
    # Por defecto, cualquier usuario nuevo será un CLIENTE.
    rol = models.CharField(max_length=10, choices=ROLE_CHOICES, default='CLIENTE')

class Maquinaria(models.Model):
    # Catálogo de las máquinas disponibles para arrendar.
    nombre = models.CharField(max_length=100)
    categoria = models.CharField(max_length=50)
    tarifa_diaria = models.DecimalField(max_digits=10, decimal_places=2)
    garantia_fija = models.DecimalField(max_digits=10, decimal_places=2)
    stock_disponible = models.PositiveIntegerField(default=0)

class Carro(models.Model):
    # Relación de 1 a 1: Cada Usuario tiene un único carrito.
    # Como está guardado en la base de datos, el carrito "no se borra" al cerrar sesión.
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE, related_name='carro')
    creado_en = models.DateTimeField(auto_now_add=True)

class ItemCarro(models.Model):
    # Son los productos que el cliente metió en su carrito.
    carro = models.ForeignKey(Carro, on_delete=models.CASCADE, related_name='items')
    maquinaria = models.ForeignKey(Maquinaria, on_delete=models.CASCADE)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()

    @property
    def dias_arriendo(self):
        # Calcula cuántos días dura el arriendo
        return (self.fecha_fin - self.fecha_inicio).days

    @property
    def costo_calculado(self):
        # Lógica de cobro: Días * Precio Diario + La Garantía
        return (self.maquinaria.tarifa_diaria * self.dias_arriendo) + self.maquinaria.garantia_fija

class Contrato(models.Model):
    # Estados por los que pasa un arriendo.
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
    # El detalle de lo que se arrendó dentro de un contrato específico.
    contrato = models.ForeignKey(Contrato, on_delete=models.CASCADE, related_name='detalles')
    maquinaria = models.ForeignKey(Maquinaria, on_delete=models.SET_NULL, null=True)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
