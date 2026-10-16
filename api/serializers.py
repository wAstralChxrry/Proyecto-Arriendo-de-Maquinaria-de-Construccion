"""
Serializadores DRF. Gestionan la conversión de objetos de la base de datos a JSON
y manejan la inyección de claims personalizados en los tokens JWT.
"""
import re
from datetime import date

from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import Maquinaria, Carro, ItemCarro, Contrato, DetalleContrato, Usuario
from django.contrib.auth.password_validation import validate_password
from django.utils.timezone import localdate

from .inventory import available_units_for_period


class PagoDemoSerializer(serializers.Serializer):
    """Valida una tarjeta ficticia sin almacenar datos sensibles."""

    titular = serializers.CharField(max_length=120)
    numero = serializers.CharField(max_length=23, write_only=True)
    vencimiento = serializers.CharField(max_length=7, write_only=True)
    cvv = serializers.CharField(max_length=4, write_only=True)

    def validate_numero(self, value):
        digits = re.sub(r'\D', '', value)
        if not 13 <= len(digits) <= 19:
            raise serializers.ValidationError('El número demo debe tener entre 13 y 19 dígitos.')
        checksum = 0
        doubled = False
        for digit in reversed(digits):
            number = int(digit)
            if doubled:
                number *= 2
                if number > 9:
                    number -= 9
            checksum += number
            doubled = not doubled
        if checksum % 10 != 0:
            raise serializers.ValidationError('El número de tarjeta demo no es válido.')
        return digits

    def validate_vencimiento(self, value):
        match = re.fullmatch(r'(0[1-9]|1[0-2])/(\d{2}|\d{4})', value.strip())
        if not match:
            raise serializers.ValidationError('Usa el formato MM/AA, por ejemplo 12/30.')
        month = int(match.group(1))
        year = int(match.group(2))
        year += 2000 if year < 100 else 0
        today = date.today()
        if (year, month) < (today.year, today.month):
            raise serializers.ValidationError('La tarjeta demo está vencida.')
        return f'{month:02d}/{year % 100:02d}'

    def validate_cvv(self, value):
        if not re.fullmatch(r'\d{3,4}', value.strip()):
            raise serializers.ValidationError('El CVV demo debe tener 3 o 4 dígitos.')
        return value.strip()

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

            en_carro = carro.items.filter(
                maquinaria=maquinaria, fecha_inicio__lt=data['fecha_fin'], fecha_fin__gt=data['fecha_inicio'],
            ).count()
            if available_units_for_period(
                maquinaria,
                data['fecha_inicio'],
                data['fecha_fin'],
                extra_units=en_carro + 1,
            ) < 0:
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
        fields = [
            'id', 'codigo_uuid', 'cliente', 'cliente_email', 'estado',
            'metodo_pago', 'fecha_pago', 'fecha_creacion', 'total', 'detalles',
        ]
        read_only_fields = fields
