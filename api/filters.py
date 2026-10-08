"""Filtros públicos de categoría y tarifa para el catálogo de maquinaria."""
import django_filters
from .models import Maquinaria


class MaquinariaFilter(django_filters.FilterSet):
    """Permite acotar tarifas con límites inclusivos y filtrar por categoría."""
    tarifa_min = django_filters.NumberFilter(field_name='tarifa_diaria', lookup_expr='gte')
    tarifa_max = django_filters.NumberFilter(field_name='tarifa_diaria', lookup_expr='lte')

    class Meta:
        model = Maquinaria
        fields = ['categoria']
