"""
Serializadores DRF. Gestionan la conversión de objetos de la base de datos a JSON
y manejan la inyección de claims personalizados en los tokens JWT.
"""
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import Maquinaria, Carro, ItemCarro, Contrato, DetalleContrato, Usuario
from django.contrib.auth.password_validation import validate_password
from django.utils.timezone import localdate

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Añade el rol del usuario a los tokens emitidos por la API."""
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['rol'] = user.rol
        token['is_superuser'] = user.is_superuser
        return token

class RegistroSerializer(serializers.ModelSerializer):
    """Valida el alta pública y asigna siempre el rol de cliente."""
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = Usuario
        fields = ['id', 'username', 'email', 'password']

    def create(self, validated_data):
        return self.Meta.model.objects.create_user(**validated_data, rol='CLIENTE')

class MaquinariaSerializer(serializers.ModelSerializer):
    """Serializa los datos públicos y administrativos de una maquinaria."""
    class Meta:
        model = Maquinaria
        fields = '__all__'

class ItemCarroSerializer(serializers.ModelSerializer):
    """Valida fechas y disponibilidad antes de guardar un ítem del carro."""
    costo_calculado = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    dias_arriendo = serializers.IntegerField(read_only=True)

    class Meta:
        model = ItemCarro
        fields = ['id', 'maquinaria', 'fecha_inicio', 'fecha_fin', 'costo_calculado', 'dias_arriendo']

    def validate(self, data):
        """Rechaza períodos inválidos o que excedan las unidades disponibles."""
        if data['fecha_inicio'] >= data['fecha_fin']:
            raise serializers.ValidationError("La fecha de inicio debe ser anterior a la fecha de fin.")
        if data['fecha_inicio'] < localdate():
            raise serializers.ValidationError("La fecha de inicio no puede ser anterior a hoy.")
        # Suma reservas activas y solicitudes del mismo carro para el período.
        maquinaria = data.get('maquinaria')
        carro = self.context['request'].user.carro if hasattr(self.context['request'].user, 'carro') else None
        if maquinaria and carro:
            duplicado = carro.items.filter(
                maquinaria=maquinaria,
                fecha_inicio=data['fecha_inicio'],
                fecha_fin=data['fecha_fin'],
            )
            if self.instance:
                duplicado = duplicado.exclude(pk=self.instance.pk)
            if duplicado.exists():
                raise serializers.ValidationError("Esa maquinaria ya está en el carro para ese período.")

            contratos_activos = DetalleContrato.objects.filter(
                maquinaria=maquinaria, contrato__estado__in=['PAGADO', 'ENTREGADO'],
            )
            activos = contratos_activos.filter(
                fecha_inicio__lt=data['fecha_fin'], fecha_fin__gt=data['fecha_inicio'],
            ).count()
            en_carro = carro.items.filter(
                maquinaria=maquinaria, fecha_inicio__lt=data['fecha_fin'], fecha_fin__gt=data['fecha_inicio'],
            ).count()
            unidades_fisicas = maquinaria.stock_disponible + contratos_activos.count()
            if activos + en_carro + 1 > unidades_fisicas:
                raise serializers.ValidationError("No hay unidades disponibles para esas fechas.")
        return data

class CarroSerializer(serializers.ModelSerializer):
    """Expone el carro con sus ítems y costos calculados."""
    items = ItemCarroSerializer(many=True, read_only=True)

    class Meta:
        model = Carro
        fields = ['id', 'items']

class DetalleContratoSerializer(serializers.ModelSerializer):
    """Serializa el detalle histórico asociado a un contrato."""
    class Meta:
        model = DetalleContrato
        fields = '__all__'

class ContratoSerializer(serializers.ModelSerializer):
    """Expone contratos sin permitir alterar estado, propietario o total."""
    detalles = DetalleContratoSerializer(many=True, read_only=True)
    cliente = serializers.CharField(source='usuario.username', read_only=True)
    cliente_email = serializers.EmailField(source='usuario.email', read_only=True)

    class Meta:
        model = Contrato
        fields = ['id', 'codigo_uuid', 'cliente', 'cliente_email', 'estado', 'fecha_creacion', 'total', 'detalles']
        read_only_fields = fields
