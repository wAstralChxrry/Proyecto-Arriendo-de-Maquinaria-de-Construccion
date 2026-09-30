"""
Los Serializadores sirven para convertir la información de la Base de Datos (PostgreSQL)
a un formato fácil de leer por internet (formato JSON), y viceversa.
"""
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import Maquinaria, Carro, ItemCarro, Contrato, DetalleContrato

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    # Personalizamos el Token JWT de inicio de sesión
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Aquí inyectamos el ROL del usuario dentro del token de forma encriptada
        token['rol'] = user.rol
        return token

class MaquinariaSerializer(serializers.ModelSerializer):
    # Serializador básico para ver y crear máquinas
    class Meta:
        model = Maquinaria
        fields = '__all__'

class ItemCarroSerializer(serializers.ModelSerializer):
    # Campos que el sistema calcula solo, el cliente no los puede editar
    costo_calculado = serializers.ReadOnlyField()
    dias_arriendo = serializers.ReadOnlyField()

    class Meta:
        model = ItemCarro
        fields = ['id', 'maquinaria', 'fecha_inicio', 'fecha_fin', 'costo_calculado', 'dias_arriendo']

    def validate(self, data):
        # Evitamos que el cliente ponga una fecha de inicio que sea después de la fecha de fin
        if data['fecha_inicio'] >= data['fecha_fin']:
            raise serializers.ValidationError("La fecha de inicio debe ser anterior a la fecha de fin.")
        return data

class CarroSerializer(serializers.ModelSerializer):
    # Un carro tiene muchos "ítems" adentro. Aquí los mostramos todos.
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
