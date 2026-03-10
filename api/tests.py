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


class ApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="apiuser", password="testpass123")
        ct_quote = ContentType.objects.get(app_label="quotes", model="quote")
        perms = Permission.objects.filter(
            content_type=ct_quote,
            codename__in=("add_quote", "change_quote", "view_quote"),
        )
        self.user.user_permissions.add(*perms)
        self.customer = Customer.objects.create(name="Cliente API")
        self.contact = CustomerContact.objects.create(
            customer=self.customer, full_name="Contacto API"
        )
        self.camera = CameraModel.objects.create(
            model_code="CAM-API",
            name="Cámara API",
            base_price=Decimal("8000.00"),
            currency=CameraModel.CURRENCY_MXN,
        )
        self.quote = Quote.objects.create(
            quote_number="SCP-2026-000100",
            customer=self.customer,
            contact=self.contact,
            sales_user=self.user,
            status=Quote.STATUS_ACCEPTED,
            currency=Quote.CURRENCY_MXN,
        )
        QuoteItem.objects.create(
            quote=self.quote,
            camera_model=self.camera,
            quantity=1,
            unit_price=Decimal("8000.00"),
        )
        self.quote.recalculate_totals()

    def test_api_quotes_list_requires_auth(self):
        response = self.client.get("/api/quotes/")
        self.assertIn(response.status_code, (401, 403))

    def test_api_quotes_list_ok(self):
        self.client.login(username="apiuser", password="testpass123")
        response = self.client.get("/api/quotes/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("results", data)
        self.assertGreaterEqual(len(data["results"]), 1)
        self.assertEqual(data["results"][0]["quote_number"], "SCP-2026-000100")

    def test_api_quotes_detail_ok(self):
        self.client.login(username="apiuser", password="testpass123")
        response = self.client.get(f"/api/quotes/{self.quote.pk}/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["quote_number"], "SCP-2026-000100")
        self.assertIn("items", data)
        self.assertEqual(len(data["items"]), 1)

    def test_api_catalog_list_ok(self):
        self.client.login(username="apiuser", password="testpass123")
        response = self.client.get("/api/catalog/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("results", data)
        self.assertGreaterEqual(len(data["results"]), 1)

    def test_api_customers_list_ok(self):
        self.client.login(username="apiuser", password="testpass123")
        response = self.client.get("/api/customers/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("results", data)
        self.assertGreaterEqual(len(data["results"]), 1)
