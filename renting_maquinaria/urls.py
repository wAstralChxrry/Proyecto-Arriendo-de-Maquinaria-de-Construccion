"""
URL configuration for renting_maquinaria project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
import os
from django.contrib import admin
from django.urls import path, include, re_path
from django.http import HttpResponse
from django.views.static import serve
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'frontend')
FRONTEND_INDEX = os.path.join(FRONTEND_DIR, 'index.html')

def frontend_view(request):
    with open(FRONTEND_INDEX, 'r', encoding='utf-8') as f:
        return HttpResponse(f.read(), content_type='text/html')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', frontend_view, name='frontend'),
    path('', include('api.urls')),
    # Exposición de Swagger/OpenAPI
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    # Archivos estáticos del frontend (style.css, app.js, imágenes, etc.)
    re_path(r'^(?P<path>.+)$', serve, {'document_root': FRONTEND_DIR}),
]
