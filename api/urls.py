"""
Configuración de rutas (URLs) de la aplicación.
Conecta los endpoints con sus respectivos ViewSets mediante el DefaultRouter de DRF.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from api.views import MaquinariaViewSet, CarroViewSet, ContratoViewSet

# El DefaultRouter genera automáticamente las rutas CRUD estándar para cada ViewSet
router = DefaultRouter()
router.register(r'maquinarias', MaquinariaViewSet, basename='maquinaria')
router.register(r'carro-arriendo', CarroViewSet, basename='carro')
router.register(r'contratos', ContratoViewSet, basename='contrato')

urlpatterns = [
    # Inclusión de todas las rutas generadas por el router
    path('api/', include(router.urls)),
    
    # Ruta auxiliar para que los Clientes accedan directamente a sus contratos
    path('api/mis-contratos/', ContratoViewSet.as_view({'get': 'list'}), name='mis-contratos'),
    
    # Endpoints de autenticación JWT
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
