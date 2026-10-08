"""Pruebas de roles, carro persistente, filtros y ciclo de contratos."""
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils.timezone import localdate
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from .models import Carro, Contrato, DetalleContrato, ItemCarro, Maquinaria


Usuario = get_user_model()


class BaseApiTestCase(TestCase):
    """Prepara cuentas y maquinaria aisladas para cada prueba."""

    def setUp(self):
        self.cliente = Usuario.objects.create_user(
            username='cliente_prueba',
            email='cliente@example.test',
            password='ClaveLocal-Segura-2026',
            rol='CLIENTE',
        )
        self.ejecutivo = Usuario.objects.create_user(
            username='ejecutivo_prueba',
            email='ejecutivo@example.test',
            password='ClaveLocal-Segura-2026',
            rol='ADMIN',
        )
        self.maquinaria = Maquinaria.objects.create(
            nombre='Excavadora de prueba',
            categoria='Excavadoras',
            tarifa_diaria=Decimal('120000.00'),
            garantia_fija=Decimal('250000.00'),
            stock_disponible=2,
        )
        self.api = APIClient()

    def crear_contrato(self, usuario=None, maquinaria=None, inicio=None, fin=None):
        """Crea una orden con un detalle para probar sus transiciones."""
        usuario = usuario or self.cliente
        maquinaria = maquinaria or self.maquinaria
        inicio = inicio or localdate() + timedelta(days=20)
        fin = fin or inicio + timedelta(days=3)
        contrato = Contrato.objects.create(usuario=usuario, total=Decimal('610000.00'))
        DetalleContrato.objects.create(
            contrato=contrato,
            maquinaria=maquinaria,
            fecha_inicio=inicio,
            fecha_fin=fin,
            subtotal=Decimal('610000.00'),
        )
        return contrato


class AuthenticationAndPermissionTests(BaseApiTestCase):
    """Comprueba los tokens JWT y la separación de permisos por rol."""

    def test_login_and_refresh_include_role_claim(self):
        login = self.api.post('/api/token/', {
            'username': self.cliente.username,
            'password': 'ClaveLocal-Segura-2026',
        }, format='json')

        self.assertEqual(login.status_code, 200)
        access = AccessToken(login.data['access'])
        self.assertEqual(access['rol'], 'CLIENTE')
        self.assertFalse(access['is_superuser'])

        refreshed = self.api.post('/api/token/refresh/', {
            'refresh': login.data['refresh'],
        }, format='json')

        self.assertEqual(refreshed.status_code, 200)
        self.assertEqual(AccessToken(refreshed.data['access'])['rol'], 'CLIENTE')

    def test_catalog_is_public_and_management_is_role_protected(self):
        self.assertEqual(self.api.get('/api/maquinarias/').status_code, 200)
        self.assertEqual(self.api.get('/api/carro-arriendo/').status_code, 401)

        self.api.force_authenticate(user=self.cliente)
        denied_inventory = self.api.post('/api/maquinarias/', {}, format='json')
        denied_state = self.api.patch('/api/contratos/999999/estado/', {'estado': 'PAGADO'}, format='json')
        self.assertEqual(denied_inventory.status_code, 403)
        self.assertEqual(denied_state.status_code, 403)

        self.api.force_authenticate(user=self.ejecutivo)
        self.assertEqual(self.api.get('/api/contratos/').status_code, 200)
        self.assertEqual(self.api.get('/api/carro-arriendo/').status_code, 403)


class CatalogFilterTests(BaseApiTestCase):
    """Verifica filtros numéricos y búsqueda del catálogo público."""

    def test_category_price_and_search_filters(self):
        Maquinaria.objects.create(
            nombre='Generador de prueba',
            categoria='Generadores',
            tarifa_diaria=Decimal('45000.00'),
            garantia_fija=Decimal('80000.00'),
            stock_disponible=1,
        )

        filtered = self.api.get('/api/maquinarias/', {
            'categoria': 'Excavadoras',
            'tarifa_min': '100000',
            'tarifa_max': '150000',
        })
        searched = self.api.get('/api/maquinarias/', {'search': 'Generador'})

        self.assertEqual(filtered.status_code, 200)
        self.assertEqual([row['id'] for row in filtered.data], [self.maquinaria.id])
        self.assertEqual(searched.status_code, 200)
        self.assertEqual([row['nombre'] for row in searched.data], ['Generador de prueba'])


class PersistentCartTests(BaseApiTestCase):
    """Comprueba persistencia entre sesiones y rechazo de duplicados."""

    def test_two_companies_keep_separate_carts(self):
        """Cada sesión ve y modifica únicamente el carro de su empresa."""
        otra_empresa = Usuario.objects.create_user(
            username='otra_empresa_prueba',
            email='otra_empresa@example.test',
            password='ClaveLocal-Segura-2026',
            rol='CLIENTE',
        )
        empresa_uno = APIClient()
        empresa_dos = APIClient()
        empresa_uno.force_authenticate(user=self.cliente)
        empresa_dos.force_authenticate(user=otra_empresa)
        fechas = {
            'maquinaria': self.maquinaria.id,
            'fecha_inicio': (localdate() + timedelta(days=10)).isoformat(),
            'fecha_fin': (localdate() + timedelta(days=14)).isoformat(),
        }

        agregado = empresa_uno.post('/api/carro-arriendo/', fechas, format='json')
        carro_uno = empresa_uno.get('/api/carro-arriendo/')
        carro_dos = empresa_dos.get('/api/carro-arriendo/')
        intento_eliminar = empresa_dos.delete(
            f"/api/carro-arriendo/{carro_uno.data['items'][0]['id']}/"
        )
        carro_uno_despues = empresa_uno.get('/api/carro-arriendo/')

        self.assertEqual(agregado.status_code, 201)
        self.assertEqual(len(carro_uno.data['items']), 1)
        self.assertEqual(carro_dos.data['items'], [])
        self.assertEqual(intento_eliminar.status_code, 404)
        self.assertEqual(len(carro_uno_despues.data['items']), 1)
        self.assertNotEqual(carro_uno.data['id'], carro_dos.data['id'])
        self.assertEqual(Carro.objects.filter(usuario=self.cliente).count(), 1)
        self.assertEqual(Carro.objects.filter(usuario=otra_empresa).count(), 1)

    def test_cart_survives_logout_and_duplicate_period_is_rejected(self):
        fecha_inicio = localdate() + timedelta(days=10)
        fecha_fin = fecha_inicio + timedelta(days=4)
        self.api.force_authenticate(user=self.cliente)
        payload = {
            'maquinaria': self.maquinaria.id,
            'fecha_inicio': fecha_inicio.isoformat(),
            'fecha_fin': fecha_fin.isoformat(),
        }

        added = self.api.post('/api/carro-arriendo/', payload, format='json')
        duplicate = self.api.post('/api/carro-arriendo/', payload, format='json')
        self.assertEqual(added.status_code, 201)
        self.assertEqual(duplicate.status_code, 400)
        self.assertEqual(self.maquinaria.stock_disponible, 2)

        self.api.force_authenticate(user=None)
        another_session = APIClient()
        another_session.force_authenticate(user=self.cliente)
        persisted = another_session.get('/api/carro-arriendo/')

        self.assertEqual(persisted.status_code, 200)
        self.assertEqual(len(persisted.data['items']), 1)
        self.assertEqual(ItemCarro.objects.filter(carro__usuario=self.cliente).count(), 1)
        self.assertTrue(Carro.objects.filter(usuario=self.cliente).exists())


class CheckoutAndInventoryTests(BaseApiTestCase):
    """Valida checkout, descuento al pagar, rechazo por falta de stock y reposición."""

    def test_checkout_creates_historical_contract_without_reducing_stock(self):
        self.api.force_authenticate(user=self.cliente)
        fecha_inicio = localdate() + timedelta(days=12)
        fecha_fin = fecha_inicio + timedelta(days=3)
        self.api.post('/api/carro-arriendo/', {
            'maquinaria': self.maquinaria.id,
            'fecha_inicio': fecha_inicio.isoformat(),
            'fecha_fin': fecha_fin.isoformat(),
        }, format='json')

        response = self.api.post('/api/contratos/checkout/', {}, format='json')

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['estado'], 'PENDIENTE')
        self.assertTrue(response.data['codigo_uuid'])
        self.assertEqual(response.data['total'], '610000.00')
        self.assertEqual(self.maquinaria.stock_disponible, 2)
        self.assertFalse(ItemCarro.objects.filter(carro__usuario=self.cliente).exists())
        self.assertEqual(Contrato.objects.get(pk=response.data['id']).detalles.count(), 1)

    def test_payment_deducts_stock_and_completion_restores_it(self):
        contrato = self.crear_contrato()
        self.api.force_authenticate(user=self.ejecutivo)

        paid = self.api.patch(f'/api/contratos/{contrato.id}/estado/', {'estado': 'PAGADO'}, format='json')
        self.assertEqual(paid.status_code, 200)
        self.maquinaria.refresh_from_db()
        self.assertEqual(self.maquinaria.stock_disponible, 1)

        delivered = self.api.patch(f'/api/contratos/{contrato.id}/estado/', {'estado': 'ENTREGADO'}, format='json')
        self.assertEqual(delivered.status_code, 200)
        completed = self.api.patch(f'/api/contratos/{contrato.id}/estado/', {'estado': 'COMPLETADO'}, format='json')
        self.assertEqual(completed.status_code, 200)
        self.maquinaria.refresh_from_db()
        self.assertEqual(self.maquinaria.stock_disponible, 2)

    def test_paid_contract_cancellation_restores_stock(self):
        contrato = self.crear_contrato()
        self.api.force_authenticate(user=self.ejecutivo)

        paid = self.api.patch(f'/api/contratos/{contrato.id}/estado/', {'estado': 'PAGADO'}, format='json')
        cancelled = self.api.patch(f'/api/contratos/{contrato.id}/estado/', {'estado': 'CANCELADO'}, format='json')

        self.assertEqual(paid.status_code, 200)
        self.assertEqual(cancelled.status_code, 200)
        self.maquinaria.refresh_from_db()
        self.assertEqual(self.maquinaria.stock_disponible, 2)

    def test_insufficient_stock_rejects_payment_without_changing_contract(self):
        contrato = self.crear_contrato()
        Maquinaria.objects.filter(pk=self.maquinaria.pk).update(stock_disponible=0)
        self.api.force_authenticate(user=self.ejecutivo)

        response = self.api.patch(f'/api/contratos/{contrato.id}/estado/', {'estado': 'PAGADO'}, format='json')

        self.assertEqual(response.status_code, 400)
        contrato.refresh_from_db()
        self.assertEqual(contrato.estado, 'PENDIENTE')
        self.assertEqual(Maquinaria.objects.get(pk=self.maquinaria.pk).stock_disponible, 0)

    def test_invalid_transition_is_rejected(self):
        contrato = self.crear_contrato()
        self.api.force_authenticate(user=self.ejecutivo)

        response = self.api.patch(f'/api/contratos/{contrato.id}/estado/', {'estado': 'COMPLETADO'}, format='json')

        self.assertEqual(response.status_code, 400)
        contrato.refresh_from_db()
        self.assertEqual(contrato.estado, 'PENDIENTE')
