from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.urls import reverse
from customers.models import Customer, CustomerContact
from quotes.models import Quote
User = get_user_model()

def _add_customer_permissions(user):
    ct = ContentType.objects.get(app_label='customers', model='customer')
    perms = Permission.objects.filter(content_type=ct, codename__in=('view_customer', 'add_customer', 'change_customer', 'delete_customer'))
    user.user_permissions.add(*perms)
    ct_contact = ContentType.objects.get(app_label='customers', model='customercontact')
    perms_contact = Permission.objects.filter(content_type=ct_contact, codename__in=('view_customercontact', 'add_customercontact', 'change_customercontact'))
    user.user_permissions.add(*perms_contact)

class CustomerModelTests(TestCase):

    def test_str_returns_name(self):
        c = Customer.objects.create(name='Acme Corp')
        self.assertEqual(str(c), 'Acme Corp')

    def test_get_absolute_url(self):
        c = Customer.objects.create(name='Test')
        self.assertIn(str(c.pk), c.get_absolute_url())
        self.assertIn('clientes', c.get_absolute_url())

class CustomerContactModelTests(TestCase):

    def setUp(self):
        self.customer = Customer.objects.create(name='Cliente')

    def test_str_includes_contact_and_customer(self):
        contact = CustomerContact.objects.create(customer=self.customer, full_name='Juan Pérez')
        self.assertIn('Juan Pérez', str(contact))
        self.assertIn('Cliente', str(contact))

class CustomerViewTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='vendedor', password='testpass123')
        _add_customer_permissions(self.user)
        self.customer = Customer.objects.create(name='Cliente Test', phone='123')

    def test_list_requires_login(self):
        response = self.client.get(reverse('customers:list'))
        self.assertEqual(response.status_code, 302)

    def test_list_ok_when_logged_in(self):
        self.client.login(username='vendedor', password='testpass123')
        response = self.client.get(reverse('customers:list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Cliente Test')

    def test_detail_ok(self):
        self.client.login(username='vendedor', password='testpass123')
        response = self.client.get(reverse('customers:detail', kwargs={'pk': self.customer.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Cliente Test')

    def test_create_redirects_to_detail(self):
        self.client.login(username='vendedor', password='testpass123')
        response = self.client.post(reverse('customers:create'), {'name': 'Nuevo Cliente', 'phone': '555'}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Customer.objects.filter(name='Nuevo Cliente').exists())

    def test_delete_without_quotes_succeeds(self):
        self.client.login(username='vendedor', password='testpass123')
        response = self.client.post(reverse('customers:delete', kwargs={'pk': self.customer.pk}), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Customer.objects.filter(pk=self.customer.pk).exists())

    def test_delete_with_quotes_shows_error(self):
        Quote.objects.create(quote_number='SCP-2026-000001', customer=self.customer, sales_user=self.user, status=Quote.STATUS_DRAFT, currency=Quote.CURRENCY_MXN)
        self.client.login(username='vendedor', password='testpass123')
        response = self.client.post(reverse('customers:delete', kwargs={'pk': self.customer.pk}), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Customer.objects.filter(pk=self.customer.pk).exists())
        self.assertContains(response, 'cotizaciones')

class CustomerContactViewTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='vendedor', password='testpass123')
        _add_customer_permissions(self.user)
        self.customer = Customer.objects.create(name='Cliente')
        self.contact = CustomerContact.objects.create(customer=self.customer, full_name='Contacto 1')

    def test_contacts_json_ok(self):
        self.client.login(username='vendedor', password='testpass123')
        response = self.client.get(reverse('customers:contacts', kwargs={'pk': self.customer.pk}))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('contacts', data)
        self.assertEqual(len(data['contacts']), 1)
        self.assertEqual(data['contacts'][0]['full_name'], 'Contacto 1')
