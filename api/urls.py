"""
Este archivo define las 'Rutas' (URLs) del sistema.
Conecta los enlaces de internet con las vistas correspondientes.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from api.views import MaquinariaViewSet, CarroViewSet, ContratoViewSet

# DefaultRouter se encarga de crear las URLs automáticamente para los ViewSets
router = DefaultRouter()
router.register(r'maquinarias', MaquinariaViewSet, basename='maquinaria')
router.register(r'carro-arriendo', CarroViewSet, basename='carro')
router.register(r'contratos', ContratoViewSet, basename='contrato')

urlpatterns = [
    # Incluimos todas las rutas que creó el router
    path('api/', include(router.urls)),
    
    # Ruta específica para que la Empresa Constructora pueda ver rápido solo SUS contratos
    path('api/mis-contratos/', ContratoViewSet.as_view({'get': 'list'}), name='mis-contratos'),
    
    # Rutas para el inicio de sesión (Generar el Token de seguridad JWT)
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
