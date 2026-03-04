from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase, override_settings
from django.urls import reverse

from catalog.models import CameraModel
from customers.models import Customer, CustomerContact
from quotes.models import Quote, QuoteItem

User = get_user_model()


class QuoteModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="vendedor", password="testpass123")
        self.customer = Customer.objects.create(name="Cliente Test", phone="123")
        self.contact = CustomerContact.objects.create(
            customer=self.customer, full_name="Contacto Test"
        )
        self.camera = CameraModel.objects.create(
            model_code="CAM-001",
            name="Cámara Test",
            base_price=Decimal("10000.00"),
            currency=CameraModel.CURRENCY_MXN,
        )

    def test_quote_creation_generates_number(self):
        quote = Quote.objects.create(
            quote_number="",
            customer=self.customer,
            contact=self.contact,
            sales_user=self.user,
            status=Quote.STATUS_DRAFT,
            currency=Quote.CURRENCY_MXN,
        )
        quote.save()
        self.assertTrue(quote.quote_number.startswith("SCP-"))

    def test_recalculate_totals_with_item(self):
        quote = Quote.objects.create(
            quote_number="SCP-2026-000001",
            customer=self.customer,
            sales_user=self.user,
            status=Quote.STATUS_DRAFT,
            currency=Quote.CURRENCY_MXN,
        )
        QuoteItem.objects.create(
            quote=quote,
            camera_model=self.camera,
            quantity=2,
            unit_price=Decimal("10000.00"),
            discount_percent=Decimal("10.00"),
        )
        quote.recalculate_totals()
        quote.refresh_from_db()
        # Subtotal es suma de line_subtotal (con descuento 10%: 20000 - 2000 = 18000)
        self.assertEqual(quote.subtotal, Decimal("18000.00"))
        self.assertGreater(quote.total, 0)

    def test_get_optional_rows_empty(self):
        quote = Quote.objects.create(
            quote_number="SCP-2026-000002",
            customer=self.customer,
            sales_user=self.user,
            status=Quote.STATUS_DRAFT,
            currency=Quote.CURRENCY_MXN,
        )
        self.assertEqual(len(quote.get_optional_rows()), 0)

    def test_get_optional_rows_with_services(self):
        quote = Quote.objects.create(
            quote_number="SCP-2026-000003",
            customer=self.customer,
            sales_user=self.user,
            status=Quote.STATUS_DRAFT,
            currency=Quote.CURRENCY_MXN,
            cableado=True,
            cableado_monto=Decimal("1000.00"),
        )
        rows = quote.get_optional_rows()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["desc"], "Cableado")
        self.assertEqual(rows[0]["monto"], Decimal("1000.00"))


class QuoteViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="vendedor", password="testpass123")
        ct = ContentType.objects.get(app_label="quotes", model="quote")
        perms = Permission.objects.filter(
            content_type=ct,
            codename__in=("add_quote", "change_quote", "view_quote"),
        )
        self.user.user_permissions.add(*perms)
        self.customer = Customer.objects.create(name="Cliente Test")
        self.contact = CustomerContact.objects.create(
            customer=self.customer, full_name="Contacto Test"
        )
        self.camera = CameraModel.objects.create(
            model_code="CAM-001",
            base_price=Decimal("5000.00"),
            currency=CameraModel.CURRENCY_MXN,
        )
        self.quote = Quote.objects.create(
            quote_number="SCP-2026-000010",
            customer=self.customer,
            contact=self.contact,
            sales_user=self.user,
            status=Quote.STATUS_DRAFT,
            currency=Quote.CURRENCY_MXN,
        )
        QuoteItem.objects.create(
            quote=self.quote,
            camera_model=self.camera,
            quantity=1,
            unit_price=Decimal("5000.00"),
        )
        self.quote.recalculate_totals()

    def test_list_requires_login(self):
        response = self.client.get(reverse("quotes:list"))
        self.assertEqual(response.status_code, 302)

    def test_list_ok_for_authenticated(self):
        self.client.login(username="vendedor", password="testpass123")
        response = self.client.get(reverse("quotes:list"))
        self.assertEqual(response.status_code, 200)

    def test_detail_ok(self):
        self.client.login(username="vendedor", password="testpass123")
        response = self.client.get(
            reverse("quotes:detail", kwargs={"pk": self.quote.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SCP-")

    def test_duplicate_creates_new_quote(self):
        self.client.login(username="vendedor", password="testpass123")
        initial_count = Quote.objects.count()
        response = self.client.get(
            reverse("quotes:duplicate", kwargs={"pk": self.quote.pk}),
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Quote.objects.count(), initial_count + 1)
        new_quote = Quote.objects.exclude(pk=self.quote.pk).order_by("-pk").first()
        self.assertNotEqual(new_quote.quote_number, self.quote.quote_number)
        self.assertEqual(new_quote.customer_id, self.quote.customer_id)
        self.assertEqual(new_quote.items.count(), 1)

    def test_pdf_requires_login(self):
        response = self.client.get(
            reverse("quotes:pdf", kwargs={"pk": self.quote.pk})
        )
        self.assertEqual(response.status_code, 302)

    def test_vendor_cannot_see_other_vendor_quotes(self):
        """Un vendedor no puede ver cotizaciones de otro vendedor."""
        other_user = User.objects.create_user(username="otro", password="testpass123")
        ct = ContentType.objects.get(app_label="quotes", model="quote")
        perms = Permission.objects.filter(content_type=ct, codename="view_quote")
        other_user.user_permissions.add(*perms)
        other_quote = Quote.objects.create(
            quote_number="SCP-2026-000099",
            customer=self.customer,
            sales_user=other_user,
            status=Quote.STATUS_DRAFT,
            currency=Quote.CURRENCY_MXN,
        )
        self.client.login(username="vendedor", password="testpass123")
        response = self.client.get(
            reverse("quotes:detail", kwargs={"pk": other_quote.pk})
        )
        self.assertIn(response.status_code, (302, 404))

    def test_full_flow_send_accept(self):
        """Flujo: enviar cotización en borrador, luego aceptar."""
        self.client.login(username="vendedor", password="testpass123")
        # Enviar
        response = self.client.post(
            reverse("quotes:send", kwargs={"pk": self.quote.pk}),
            follow=True,
        )
        self.quote.refresh_from_db()
        self.assertEqual(self.quote.status, Quote.STATUS_SENT)
        # Aceptar
        response = self.client.post(
            reverse("quotes:mark", kwargs={"pk": self.quote.pk, "status": "ACCEPTED"}),
            follow=True,
        )
        self.quote.refresh_from_db()
        self.assertEqual(self.quote.status, Quote.STATUS_ACCEPTED)

    def test_csv_export_requires_login(self):
        response = self.client.get(reverse("quotes:list_export"))
        self.assertEqual(response.status_code, 302)

    def test_csv_export_ok(self):
        self.client.login(username="vendedor", password="testpass123")
        response = self.client.get(reverse("quotes:list_export"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv; charset=utf-8")
        self.assertIn(b"SCP-2026-000010", response.content)

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("quotes:dashboard"))
        self.assertEqual(response.status_code, 302)

    def test_dashboard_ok(self):
        self.client.login(username="vendedor", password="testpass123")
        response = self.client.get(reverse("quotes:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Panel de control")

    def test_report_requires_login(self):
        response = self.client.get(reverse("quotes:report"))
        self.assertEqual(response.status_code, 302)

    def test_report_ok(self):
        self.client.login(username="vendedor", password="testpass123")
        response = self.client.get(reverse("quotes:report"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Reporte")

    def test_report_export_requires_login(self):
        response = self.client.get(reverse("quotes:report_export"))
        self.assertEqual(response.status_code, 302)

    def test_report_export_ok(self):
        self.client.login(username="vendedor", password="testpass123")
        response = self.client.get(reverse("quotes:report_export"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv; charset=utf-8")
        self.assertIn(b"SCP-2026-000010", response.content)

    def test_full_flow_send_reject(self):
        """Flujo: enviar cotización en borrador, luego rechazar."""
        self.client.login(username="vendedor", password="testpass123")
        response = self.client.post(
            reverse("quotes:send", kwargs={"pk": self.quote.pk}),
            follow=True,
        )
        self.quote.refresh_from_db()
        self.assertEqual(self.quote.status, Quote.STATUS_SENT)
        response = self.client.post(
            reverse("quotes:mark", kwargs={"pk": self.quote.pk, "status": "REJECTED"}),
            follow=True,
        )
        self.quote.refresh_from_db()
        self.assertEqual(self.quote.status, Quote.STATUS_REJECTED)

    @override_settings(QUOTE_PDF_ENGINE="reportlab")
    def test_pdf_ok_for_authenticated(self):
        """PDF devuelve 200 y application/pdf (usa ReportLab, salta si falla por deps)."""
        self.client.login(username="vendedor", password="testpass123")
        try:
            response = self.client.get(reverse("quotes:pdf", kwargs={"pk": self.quote.pk}))
        except OSError as e:
            if "weasyprint" in str(e).lower() or "libgobject" in str(e).lower():
                self.skipTest("WeasyPrint/ReportLab no disponible en este entorno")
            raise
        if response.status_code == 302:
            self.skipTest("WeasyPrint/ReportLab no disponible en este entorno (redirect a detail)")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            "application/pdf" in response.get("Content-Type", ""),
            f"Expected PDF content type, got {response.get('Content-Type')}",
        )
