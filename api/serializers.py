"""
Serializadores DRF. Gestionan la conversión de objetos de la base de datos a JSON
y manejan la inyección de claims personalizados en los tokens JWT.
"""
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import Maquinaria, Carro, ItemCarro, Contrato, DetalleContrato

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    # Personalización del payload del Token JWT
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Inyección del rol del usuario para el control de accesos frontend/backend
        token['rol'] = user.rol
        return token

class MaquinariaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Maquinaria
        fields = '__all__'

class ItemCarroSerializer(serializers.ModelSerializer):
    # Definición de campos de solo lectura calculados a nivel de modelo
    costo_calculado = serializers.ReadOnlyField()
    dias_arriendo = serializers.ReadOnlyField()

    class Meta:
        model = ItemCarro
        fields = ['id', 'maquinaria', 'fecha_inicio', 'fecha_fin', 'costo_calculado', 'dias_arriendo']

    def validate(self, data):
        # Validación de coherencia temporal en las fechas de arriendo
        if data['fecha_inicio'] >= data['fecha_fin']:
            raise serializers.ValidationError("La fecha de inicio debe ser anterior a la fecha de fin.")
        return data

class CarroSerializer(serializers.ModelSerializer):
    # Relación anidada para exponer los ítems del carro
    items = ItemCarroSerializer(many=True, read_only=True)

    class Meta:
        model = Carro
        fields = ['id', 'items']

class DetalleContratoSerializer(serializers.ModelSerializer):
    class Meta:
        model = DetalleContrato
        fields = '__all__'

class ContratoSerializer(serializers.ModelSerializer):
    detalles = DetalleContratoSerializer(many=True, read_only=True)

    class Meta:
        model = Contrato
        fields = ['id', 'estado', 'fecha_creacion', 'total', 'detalles']
