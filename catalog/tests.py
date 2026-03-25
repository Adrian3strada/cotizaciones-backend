from decimal import Decimal
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.urls import reverse
from catalog.models import CameraModel
from customers.models import Customer, CustomerContact
from quotes.models import Quote, QuoteItem
User = get_user_model()

def _add_catalog_permissions(user):
    ct = ContentType.objects.get(app_label='catalog', model='cameramodel')
    perms = Permission.objects.filter(content_type=ct, codename__in=('view_cameramodel', 'add_cameramodel', 'change_cameramodel', 'delete_cameramodel'))
    user.user_permissions.add(*perms)

class CameraModelTests(TestCase):

    def test_str_returns_name_or_model_code(self):
        c = CameraModel.objects.create(model_code='CAM-001', name='Cámara IP', base_price=Decimal('5000'))
        self.assertEqual(str(c), 'Cámara IP')

    def test_str_falls_back_to_model_code(self):
        c = CameraModel.objects.create(model_code='CAM-002', base_price=Decimal('3000'))
        self.assertEqual(str(c), 'CAM-002')

    def test_get_absolute_url(self):
        c = CameraModel.objects.create(model_code='CAM-X', base_price=Decimal('1000'))
        self.assertIn(str(c.pk), c.get_absolute_url())
        self.assertIn('catalogo', c.get_absolute_url())

class CameraModelViewTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='vendedor', password='testpass123')
        _add_catalog_permissions(self.user)
        self.camera = CameraModel.objects.create(model_code='CAM-001', name='Cámara Test', base_price=Decimal('10000'))

    def test_list_requires_login(self):
        response = self.client.get(reverse('catalog:list'))
        self.assertEqual(response.status_code, 302)

    def test_list_ok_when_logged_in(self):
        self.client.login(username='vendedor', password='testpass123')
        response = self.client.get(reverse('catalog:list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'CAM-001')

    def test_detail_ok(self):
        self.client.login(username='vendedor', password='testpass123')
        response = self.client.get(reverse('catalog:detail', kwargs={'pk': self.camera.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Cámara Test')

    def test_create_redirects_to_list(self):
        self.client.login(username='vendedor', password='testpass123')
        response = self.client.post(reverse('catalog:create'), {'model_code': 'CAM-NEW', 'name': 'Nueva Cámara', 'base_price': '15000'}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(CameraModel.objects.filter(model_code='CAM-NEW').exists())

    def test_delete_without_quotes_succeeds(self):
        self.client.login(username='vendedor', password='testpass123')
        response = self.client.post(reverse('catalog:delete', kwargs={'pk': self.camera.pk}), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(CameraModel.objects.filter(pk=self.camera.pk).exists())

    def test_delete_with_quotes_shows_error(self):
        customer = Customer.objects.create(name='Cliente')
        contact = CustomerContact.objects.create(customer=customer, full_name='Contacto')
        quote = Quote.objects.create(quote_number='SCP-2026-000001', customer=customer, contact=contact, sales_user=self.user, status=Quote.STATUS_DRAFT, currency=Quote.CURRENCY_MXN, usd_mxn_rate=Decimal('20.00'))
        QuoteItem.objects.create(quote=quote, camera_model=self.camera, quantity=1, unit_price=Decimal('10000'))
        self.client.login(username='vendedor', password='testpass123')
        response = self.client.post(reverse('catalog:delete', kwargs={'pk': self.camera.pk}), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(CameraModel.objects.filter(pk=self.camera.pk).exists())
        self.assertContains(response, 'cotizaciones')
