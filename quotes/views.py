from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db import models, transaction
from django.db.models import Count, DecimalField, Q, Sum, Value
from django.db.models.functions import Coalesce, ExtractMonth, ExtractYear
import csv
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.staticfiles import finders
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_POST
from django.views.generic import DetailView, ListView, TemplateView
import json
from decimal import Decimal
from pathlib import Path

from dateutil.relativedelta import relativedelta

import logging
from django.db.models.signals import post_delete, post_save

from catalog.models import CameraModel

logger = logging.getLogger(__name__)
from customers.models import Customer
from quotes.forms import QuoteForm, QuoteItemFormSet
from quotes.models import Quote, QuoteItem
from quotes.signals import quote_item_deleted, quote_item_saved


def _get_quote_for_user(request, pk):
    """Obtiene la cotización por pk; 404 si no existe o el usuario no tiene acceso."""
    qs = Quote.objects.all()
    if not request.user.is_superuser:
        qs = qs.filter(sales_user=request.user)
    return get_object_or_404(qs, pk=pk)


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = Quote.objects.all()
        if not self.request.user.is_superuser:
            queryset = queryset.filter(sales_user=self.request.user)

        accepted_queryset = queryset.filter(status=Quote.STATUS_ACCEPTED)
        customer_queryset = Customer.objects.filter(quotes__in=queryset).distinct()

        totals = queryset.aggregate(
            total_amount=Coalesce(
                Sum("total"),
                Value(0),
                output_field=DecimalField(max_digits=14, decimal_places=2),
            ),
            accepted_count=Count("id", filter=models.Q(status=Quote.STATUS_ACCEPTED)),
            sent_count=Count("id", filter=models.Q(status=Quote.STATUS_SENT)),
            draft_count=Count("id", filter=models.Q(status=Quote.STATUS_DRAFT)),
            rejected_count=Count("id", filter=models.Q(status=Quote.STATUS_REJECTED)),
            expired_count=Count("id", filter=models.Q(status=Quote.STATUS_EXPIRED)),
            total_quotes=Count("id"),
        )
        accepted_total = accepted_queryset.aggregate(
            total=Coalesce(
                Sum("total"),
                Value(0),
                output_field=DecimalField(max_digits=14, decimal_places=2),
            ),
        )["total"]

        conversion_rate = 0
        if totals["total_quotes"]:
            conversion_rate = round((totals["accepted_count"] / totals["total_quotes"]) * 100, 2)

        top_customer = (
            accepted_queryset.values("customer__name")
            .annotate(total=Sum("total"))
            .order_by("-total")
            .first()
        )
        top_seller = (
            accepted_queryset.values("sales_user__username")
            .annotate(total=Sum("total"))
            .order_by("-total")
            .first()
        )
        top_models = list(
            QuoteItem.objects.filter(quote__in=accepted_queryset)
            .values("camera_model__model_code", "camera_model__name")
            .annotate(total_qty=Coalesce(Sum("quantity"), Value(0)))
            .order_by("-total_qty")[:6]
        )
        max_model_qty = max((model["total_qty"] for model in top_models), default=0) or 1
        for model in top_models:
            model["pct"] = round((float(model["total_qty"]) / float(max_model_qty)) * 100)

        current_date = timezone.localdate()
        month_labels = [
            "Enero",
            "Febrero",
            "Marzo",
            "Abril",
            "Mayo",
            "Junio",
            "Julio",
            "Agosto",
            "Septiembre",
            "Octubre",
            "Noviembre",
            "Diciembre",
        ]
        start_six_months = current_date - relativedelta(months=5)
        monthly_totals = (
            queryset.filter(
                issue_date__gte=start_six_months.replace(day=1),
                issue_date__lte=current_date,
            )
            .annotate(year=ExtractYear("issue_date"), month=ExtractMonth("issue_date"))
            .values("year", "month")
            .annotate(
                total=Coalesce(
                    Sum("total"),
                    Value(0),
                    output_field=DecimalField(max_digits=14, decimal_places=2),
                )
            )
            .order_by("year", "month")
        )
        monthly_map = {(row["year"], row["month"]): row["total"] for row in monthly_totals}
        last_months = []
        for offset in range(5, -1, -1):
            d = current_date - relativedelta(months=offset)
            last_months.append(
                {
                    "label": month_labels[d.month - 1][:3],
                    "total": monthly_map.get((d.year, d.month), 0),
                }
            )
        max_total = max((item["total"] for item in last_months), default=0) or 1
        for item in last_months:
            item["pct"] = round((float(item["total"]) / float(max_total)) * 100)

        # Comparativa año anterior (aceptadas vs aceptadas)
        prev_year = current_date.year - 1
        prev_year_accepted = queryset.filter(
            status=Quote.STATUS_ACCEPTED, issue_date__year=prev_year
        ).aggregate(
            total=Coalesce(Sum("total"), Value(0), output_field=DecimalField(max_digits=14, decimal_places=2))
        )["total"]
        year_vs_prev = None
        if prev_year_accepted and float(prev_year_accepted) > 0 and accepted_total:
            diff_pct = round(((float(accepted_total) - float(prev_year_accepted)) / float(prev_year_accepted)) * 100, 1)
            year_vs_prev = {"prev_total": prev_year_accepted, "diff_pct": diff_pct}

        customer_count = customer_queryset.count()
        active_customer_rate = 0
        if Customer.objects.exists():
            active_customer_rate = round((customer_count / Customer.objects.count()) * 100)

        # Datos para Chart.js
        chart_status_labels = ["Borrador", "Enviadas", "Aceptadas", "Rechazadas", "Expiradas"]
        chart_status_data = [
            totals["draft_count"],
            totals["sent_count"],
            totals["accepted_count"],
            totals["rejected_count"],
            totals["expired_count"],
        ]
        chart_models_labels = [m.get("camera_model__model_code") or m.get("camera_model__name") or "-" for m in top_models]
        chart_models_data = [float(m["total_qty"]) for m in top_models]
        chart_months_labels = [m["label"] for m in last_months]
        chart_months_data = [float(m["total"]) for m in last_months]

        context.update(
            {
                "customer_count": customer_count,
                "model_count": CameraModel.objects.count(),
                "quote_count": totals["total_quotes"],
                "total_amount": totals["total_amount"],
                "accepted_total": accepted_total,
                "accepted_count": totals["accepted_count"],
                "sent_count": totals["sent_count"],
                "draft_count": totals["draft_count"],
                "rejected_count": totals["rejected_count"],
                "expired_count": totals["expired_count"],
                "conversion_rate": conversion_rate,
                "top_customer": top_customer,
                "top_seller": top_seller,
                "top_models": top_models,
                "last_months": last_months,
                "year_vs_prev": year_vs_prev,
                "active_customer_rate": active_customer_rate,
                "today_label": current_date.strftime("%d/%m/%Y"),
                "chart_status_labels": chart_status_labels,
                "chart_status_data": chart_status_data,
                "chart_models_labels": chart_models_labels,
                "chart_models_data": chart_models_data,
                "chart_months_labels": chart_months_labels,
                "chart_months_data": chart_months_data,
            }
        )
        return context


class QuoteListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Quote
    template_name = "quotes/quote_list.html"
    permission_required = "quotes.view_quote"
    paginate_by = 10

    def get_queryset(self):
        return _get_quote_list_queryset(self.request)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_superuser:
            context["customers"] = Customer.objects.values_list("id", "name").order_by("name")
            context["sales_users"] = get_user_model().objects.values_list("id", "username").order_by("username")
        else:
            context["customers"] = (
                Customer.objects.filter(quotes__sales_user=self.request.user)
                .distinct()
                .values_list("id", "name")
                .order_by("name")
            )
            context["sales_users"] = (
                get_user_model()
                .objects.filter(id=self.request.user.id)
                .values_list("id", "username")
            )
        context["status_choices"] = Quote.STATUS_CHOICES
        q = self.request.GET.copy()
        if "page" in q:
            q.pop("page")
        context["filter_query_string"] = q.urlencode()
        q_no_order = q.copy()
        q_no_order.pop("order_by", None)
        context["filter_query_string_no_order"] = q_no_order.urlencode()
        order_by = self.request.GET.get("order_by", "-issue_date")
        context["current_order_by"] = order_by
        from datetime import timedelta
        today = timezone.localdate()
        context["today_iso"] = today.isoformat()
        context["allowed_order"] = {
            "issue_date", "-issue_date", "quote_number", "-quote_number",
            "total", "-total", "valid_until", "-valid_until",
            "customer__name", "-customer__name", "sales_user__username", "-sales_user__username",
            "currency", "-currency",
        }
        return context


class QuoteDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Quote
    template_name = "quotes/quote_detail.html"
    permission_required = "quotes.view_quote"

    def get_queryset(self):
        queryset = (
            super()
            .get_queryset()
            .select_related("customer", "contact", "sales_user")
            .prefetch_related("items__camera_model")
        )
        if not self.request.user.is_superuser:
            queryset = queryset.filter(sales_user=self.request.user)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        quote = self.object
        context["is_expired"] = (
            quote.status == Quote.STATUS_EXPIRED
            or (quote.valid_until and quote.valid_until < timezone.localdate())
        )
        return context


def _count_valid_items(formset):
    count = 0
    for form in formset:
        if not form.cleaned_data:
            continue
        if form.cleaned_data.get("DELETE"):
            continue
        count += 1
    return count


def _validate_item_currencies(formset, quote_currency):
    if not quote_currency:
        return False
    has_errors = False
    for form in formset:
        if not getattr(form, "cleaned_data", None):
            continue
        if form.cleaned_data.get("DELETE"):
            continue
        camera_model = form.cleaned_data.get("camera_model")
        if camera_model and camera_model.currency and camera_model.currency != quote_currency:
            form.add_error(
                "camera_model",
                (
                    f"La moneda del modelo ({camera_model.currency}) no coincide con "
                    f"la moneda de la cotización ({quote_currency})."
                ),
            )
            has_errors = True
    return has_errors


def _build_file_uri(path_value):
    if not path_value:
        return ""
    return Path(path_value).resolve().as_uri()


def _apply_common_quote_filters(queryset, request, date_from=None, date_to=None):
    """Aplica filtros comunes: usuario, fechas, customer_id, sales_user_id.
    date_from/date_to opcionales: si no se pasan, se leen de request.GET."""
    if not request.user.is_superuser:
        queryset = queryset.filter(sales_user=request.user)
    if date_from is None:
        date_from = parse_date(request.GET.get("date_from") or "")
    if date_to is None:
        date_to = parse_date(request.GET.get("date_to") or "")
    if date_from:
        queryset = queryset.filter(issue_date__gte=date_from)
    if date_to:
        queryset = queryset.filter(issue_date__lte=date_to)
    for param, filter_key in [("customer", "customer_id"), ("sales_user", "sales_user_id")]:
        val = request.GET.get(param)
        if val:
            try:
                queryset = queryset.filter(**{filter_key: int(val)})
            except (TypeError, ValueError):
                pass
    return queryset


def _get_quote_list_queryset(request):
    """Queryset filtrado para lista y export CSV (misma lógica)."""
    queryset = Quote.objects.select_related("customer", "sales_user")
    queryset = _apply_common_quote_filters(queryset, request)
    status = request.GET.get("status")
    search = (request.GET.get("q") or "").strip()
    if search:
        queryset = queryset.filter(
            Q(quote_number__icontains=search) | Q(customer__name__icontains=search)
        )
    if status:
        queryset = queryset.filter(status=status)
    expiring_days = request.GET.get("expiring_days")
    if expiring_days:
        try:
            days = int(expiring_days)
            if days > 0:
                from datetime import timedelta
                today = timezone.localdate()
                limit = today + timedelta(days=days)
                queryset = queryset.filter(
                    status__in=[Quote.STATUS_DRAFT, Quote.STATUS_SENT],
                    valid_until__gte=today,
                    valid_until__lte=limit,
                )
        except (TypeError, ValueError):
            pass
    order_by = request.GET.get("order_by", "-issue_date")
    allowed = {
        "issue_date", "-issue_date", "quote_number", "-quote_number",
        "total", "-total", "valid_until", "-valid_until",
        "customer__name", "-customer__name", "sales_user__username", "-sales_user__username",
        "currency", "-currency",
    }
    if order_by in allowed:
        queryset = queryset.order_by(order_by)
    else:
        queryset = queryset.order_by("-issue_date")
    return queryset


def _validate_quote_action(quote, require_items=True):
    if quote.status == Quote.STATUS_EXPIRED:
        return "La cotización está expirada."
    if quote.valid_until and quote.valid_until < timezone.localdate():
        return "La cotización está expirada."
    if require_items and not quote.items.exists():
        return "Agrega al menos un item antes de continuar."
    return ""


@login_required
@permission_required("quotes.add_quote", raise_exception=True)
def quote_create(request):
    if request.method == "POST":
        form = QuoteForm(request.POST)
        formset = QuoteItemFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            quote = form.save(commit=False)
            quote.sales_user = request.user
            if _validate_item_currencies(formset, quote.currency):
                pass
            elif quote.status == Quote.STATUS_SENT and _count_valid_items(formset) == 0:
                form.add_error("status", "No puedes enviar una cotización sin items.")
            else:
                with transaction.atomic():
                    quote.save()
                    formset.instance = quote
                    post_save.disconnect(quote_item_saved, sender=QuoteItem)
                    post_delete.disconnect(quote_item_deleted, sender=QuoteItem)
                    try:
                        formset.save()
                    finally:
                        post_save.connect(quote_item_saved, sender=QuoteItem)
                        post_delete.connect(quote_item_deleted, sender=QuoteItem)
                    quote.recalculate_totals()
                logger.info("Cotización creada", extra={"quote": quote.quote_number, "user": request.user.username})
                messages.success(request, "Cotización creada.")
                return redirect("quotes:detail", pk=quote.pk)
    else:
        form = QuoteForm(initial={"status": Quote.STATUS_DRAFT})
        formset = QuoteItemFormSet()
    optional_service_fields = {
        "cableado", "cableado_monto", "instalacion", "instalacion_monto",
        "inyector_poe", "inyector_poe_monto", "poe", "poe_monto",
    }
    camera_model_prices = json.dumps({
        str(pk): str(price)
        for pk, price in CameraModel.objects.values_list("id", "base_price")
    })
    return render(
        request,
        "quotes/quote_form.html",
        {
            "form": form,
            "formset": formset,
            "is_edit": False,
            "optional_service_fields": optional_service_fields,
            "camera_model_prices": camera_model_prices,
        },
    )


@login_required
@permission_required("quotes.change_quote", raise_exception=True)
def quote_update(request, pk):
    quote = _get_quote_for_user(request, pk)
    if request.method == "POST":
        form = QuoteForm(request.POST, instance=quote)
        formset = QuoteItemFormSet(request.POST, instance=quote)
        if form.is_valid() and formset.is_valid():
            updated_quote = form.save(commit=False)
            if _validate_item_currencies(formset, updated_quote.currency):
                pass
            elif updated_quote.status == Quote.STATUS_SENT and _count_valid_items(formset) == 0:
                form.add_error("status", "No puedes enviar una cotización sin items.")
            else:
                with transaction.atomic():
                    updated_quote.save()
                    post_save.disconnect(quote_item_saved, sender=QuoteItem)
                    post_delete.disconnect(quote_item_deleted, sender=QuoteItem)
                    try:
                        formset.save()
                    finally:
                        post_save.connect(quote_item_saved, sender=QuoteItem)
                        post_delete.connect(quote_item_deleted, sender=QuoteItem)
                    updated_quote.recalculate_totals()
                logger.info("Cotización actualizada", extra={"quote": updated_quote.quote_number, "user": request.user.username})
                messages.success(request, "Cotización actualizada.")
                return redirect("quotes:detail", pk=quote.pk)
    else:
        form = QuoteForm(instance=quote)
        formset = QuoteItemFormSet(instance=quote)
    optional_service_fields = {
        "cableado", "cableado_monto", "instalacion", "instalacion_monto",
        "inyector_poe", "inyector_poe_monto", "poe", "poe_monto",
    }
    camera_model_prices = json.dumps({
        str(pk): str(price)
        for pk, price in CameraModel.objects.values_list("id", "base_price")
    })
    return render(
        request,
        "quotes/quote_form.html",
        {
            "form": form,
            "formset": formset,
            "is_edit": True,
            "quote": quote,
            "optional_service_fields": optional_service_fields,
            "camera_model_prices": camera_model_prices,
        },
    )


@login_required
@permission_required("quotes.change_quote", raise_exception=True)
@require_POST
def quote_send(request, pk):
    quote = _get_quote_for_user(request, pk)
    if quote.status != Quote.STATUS_DRAFT:
        messages.error(request, "Solo puedes enviar cotizaciones en borrador.")
        return redirect("quotes:detail", pk=pk)
    quote.recalculate_totals()
    error = _validate_quote_action(quote, require_items=True)
    if error:
        messages.error(request, error)
        return redirect("quotes:detail", pk=pk)
    quote.status = Quote.STATUS_SENT
    quote.save()
    logger.info("Cotización enviada", extra={"quote": quote.quote_number, "user": request.user.username})
    messages.success(request, "Cotización enviada.")
    return redirect("quotes:detail", pk=pk)


@login_required
@permission_required("quotes.change_quote", raise_exception=True)
@require_POST
def quote_mark(request, pk, status):
    quote = _get_quote_for_user(request, pk)
    if status not in [Quote.STATUS_ACCEPTED, Quote.STATUS_REJECTED]:
        return redirect("quotes:detail", pk=pk)
    if quote.status != Quote.STATUS_SENT:
        messages.error(request, "Solo puedes marcar cotizaciones enviadas.")
        return redirect("quotes:detail", pk=pk)
    quote.recalculate_totals()
    error = _validate_quote_action(quote, require_items=True)
    if error:
        messages.error(request, error)
        return redirect("quotes:detail", pk=pk)
    quote.status = status
    quote.save()
    logger.info("Cotización marcada como %s", status.lower(), extra={"quote": quote.quote_number, "status": status, "user": request.user.username})
    messages.success(request, "Estado actualizado.")
    return redirect("quotes:detail", pk=pk)


@login_required
@permission_required("quotes.add_quote", raise_exception=True)
@permission_required("quotes.view_quote", raise_exception=True)
def quote_duplicate(request, pk):
    quote = _get_quote_for_user(request, pk)
    with transaction.atomic():
        new_quote = Quote(
            quote_number="",
            customer=quote.customer,
            contact=quote.contact,
            sales_user=request.user,
            status=Quote.STATUS_DRAFT,
            currency=quote.currency,
            tax_rate=quote.tax_rate,
            special_discount_percent=quote.special_discount_percent,
            cableado=quote.cableado,
            cableado_monto=quote.cableado_monto or Decimal("0.00"),
            instalacion=quote.instalacion,
            instalacion_monto=quote.instalacion_monto or Decimal("0.00"),
            inyector_poe=quote.inyector_poe,
            inyector_poe_monto=quote.inyector_poe_monto or Decimal("0.00"),
            poe=quote.poe,
            poe_monto=quote.poe_monto or Decimal("0.00"),
            notes=quote.notes or "",
            terms=quote.terms or "",
        )
        new_quote.save()
        for item in quote.items.all():
            QuoteItem.objects.create(
                quote=new_quote,
                camera_model=item.camera_model,
                quantity=item.quantity,
                unit_price=item.unit_price,
                discount_percent=item.discount_percent,
                group_name=item.group_name or "",
                order_in_group=item.order_in_group,
                configuration_notes=item.configuration_notes or "",
            )
        new_quote.recalculate_totals()
    messages.success(request, "Cotización duplicada. Puedes editarla ahora.")
    return redirect("quotes:update", pk=new_quote.pk)


@login_required
@permission_required("quotes.view_quote", raise_exception=True)
def quote_pdf(request, pk):
    from django.conf import settings as django_settings

    quote = _get_quote_for_user(request, pk)

    company = getattr(django_settings, "QUOTE_PDF_COMPANY", {}) or {}
    vigencia_texto = ""
    if quote.valid_until and quote.issue_date:
        dias = (quote.valid_until - quote.issue_date).days
        vigencia_texto = f"{dias} días"
    _meses = (
        "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
    )
    issue_date_formatted = (
        f"{quote.issue_date.day} {_meses[quote.issue_date.month - 1]} {quote.issue_date.year}"
        if quote.issue_date else ""
    )

    pdf_engine = getattr(django_settings, "QUOTE_PDF_ENGINE", "reportlab")
    use_reportlab = pdf_engine == "reportlab"
    if use_reportlab:
        try:
            from quotes.pdf_reportlab import build_quote_pdf
            pdf_bytes = build_quote_pdf(quote, company, vigencia_texto, issue_date_formatted)
            response = HttpResponse(pdf_bytes, content_type="application/pdf")
        except ModuleNotFoundError:
            use_reportlab = False
    if not use_reportlab:
        try:
            from weasyprint import HTML
            logo_path = finders.find("img/logo.png")
            header_right_path = finders.find(
                getattr(django_settings, "QUOTE_PDF_HEADER_IMAGE", "img/quote_header_right.png")
            )
            logo_uri = _build_file_uri(logo_path)
            header_right_uri = _build_file_uri(header_right_path)
            pdf_context = {
                "quote": quote,
                "vigencia_texto": vigencia_texto,
                "issue_date_formatted": issue_date_formatted,
                "company_name": company.get("name", "Sistemas de Conteo de Personas."),
                "company_website": company.get("website", "www.sisconper.com"),
                "company_street": company.get("street", "Blvd. Paseo de la República No. 13020 Int. 1307"),
                "company_colony": company.get("colony", "Col. Juriquilla, Querétaro, Qro."),
                "company_postal_code": company.get("postal_code", "C.P. 76230"),
                "company_phone": company.get("phone", "(442) 245 7000"),
                "company_mobile": company.get("mobile", ""),
                "company_rfc": company.get("rfc", "SCP070410C43"),
                "company_email": company.get("email", "info@sisconper.com"),
                "company_logo_uri": logo_uri,
                "header_right_uri": header_right_uri,
            }
            html_string = render_to_string("quotes/quote_pdf.html", pdf_context)
            pdf_bytes = HTML(string=html_string, base_url=request.build_absolute_uri()).write_pdf()
            response = HttpResponse(pdf_bytes, content_type="application/pdf")
        except Exception as e:
            # WeasyPrint puede lanzar OSError, ValueError u otras excepciones de dependencias.
            # Capturamos todas para mostrar mensaje amigable; el traceback se registra en logs.
            logger.exception("Error generando PDF con WeasyPrint: %s", e)
            messages.error(
                request,
                "No se pudo generar el PDF. Por favor, intente de nuevo o contacte al administrador.",
            )
            return redirect("quotes:detail", pk=pk)

    filename_number = quote.quote_number
    if filename_number.startswith("COT-"):
        filename_number = filename_number.replace("COT-", "SCP-", 1)
    elif not filename_number.startswith("SCP-"):
        filename_number = f"SCP-{filename_number}"
    if request.GET.get("preview"):
        response["Content-Disposition"] = f'inline; filename="{filename_number}.pdf"'
    else:
        response["Content-Disposition"] = f'attachment; filename="{filename_number}.pdf"'
    return response


@login_required
@permission_required("quotes.view_quote", raise_exception=True)
def report_view(request):
    current_year = timezone.localdate().year
    queryset = Quote.objects.all()
    if not request.user.is_superuser:
        queryset = queryset.filter(sales_user=request.user)
    date_from = parse_date(request.GET.get("date_from") or "")
    date_to = parse_date(request.GET.get("date_to") or "")
    sales_user_id = request.GET.get("sales_user")
    customer_id = request.GET.get("customer")

    if date_from and date_to and date_from > date_to:
        messages.error(request, "La fecha desde debe ser menor o igual a la fecha hasta.")
        date_from = None
        date_to = None
    if date_from:
        queryset = queryset.filter(issue_date__gte=date_from)
    if date_to:
        queryset = queryset.filter(issue_date__lte=date_to)
    if sales_user_id:
        try:
            sales_user_id = int(sales_user_id)
            queryset = queryset.filter(sales_user_id=sales_user_id)
        except (TypeError, ValueError):
            pass
    if customer_id:
        try:
            customer_id = int(customer_id)
            queryset = queryset.filter(customer_id=customer_id)
        except (TypeError, ValueError):
            pass
    if not date_from and not date_to:
        queryset = queryset.filter(issue_date__year=current_year)

    monthly_counts = (
        queryset.annotate(month=ExtractMonth("issue_date"))
        .values("month", "status")
        .annotate(total=Count("id"))
        .order_by("month")
    )
    status_counts = (
        queryset.values("status")
        .annotate(total=Count("id"))
        .order_by("status")
    )
    accepted_queryset = queryset.filter(status=Quote.STATUS_ACCEPTED)
    top_models = (
        QuoteItem.objects.filter(quote__in=accepted_queryset)
        .values("camera_model__model_code", "camera_model__name")
        .annotate(total_qty=Sum("quantity"))
        .order_by("-total_qty")[:5]
    )
    totals = queryset.aggregate(
        total_quotes=Count("id"),
        total_amount=Coalesce(
            Sum("total"),
            Value(0),
            output_field=DecimalField(max_digits=14, decimal_places=2),
        ),
        accepted_count=Count("id", filter=models.Q(status=Quote.STATUS_ACCEPTED)),
    )
    conversion_rate = 0
    if totals["total_quotes"]:
        conversion_rate = round((totals["accepted_count"] / totals["total_quotes"]) * 100, 2)

    month_labels = [
        "Enero",
        "Febrero",
        "Marzo",
        "Abril",
        "Mayo",
        "Junio",
        "Julio",
        "Agosto",
        "Septiembre",
        "Octubre",
        "Noviembre",
        "Diciembre",
    ]
    status_keys = [status for status, _ in Quote.STATUS_CHOICES]
    series = {status: [0] * 12 for status in status_keys}
    for row in monthly_counts:
        month_index = (row["month"] or 0) - 1
        if 0 <= month_index < 12:
            series[row["status"]][month_index] = row["total"]

    status_labels = [label for _, label in Quote.STATUS_CHOICES]
    status_label_map = {key: label for key, label in Quote.STATUS_CHOICES}
    month_label_map = {month: month_labels[month - 1] for month in range(1, 13)}
    monthly_rows = []
    for row in monthly_counts:
        month_value = row["month"]
        monthly_rows.append(
            {
                "month": month_value,
                "month_label": month_label_map.get(month_value, month_value),
                "status": row["status"],
                "status_label": status_label_map.get(row["status"], row["status"]),
                "total": row["total"],
            }
        )
    status_totals = []
    status_map = {row["status"]: row["total"] for row in status_counts}
    for status_key in status_keys:
        status_totals.append(status_map.get(status_key, 0))

    return render(
        request,
        "quotes/report.html",
        {
            "monthly_counts": monthly_counts,
            "monthly_rows": monthly_rows,
            "status_counts": status_counts,
            "top_models": top_models,
            "year": current_year,
            "totals": totals,
            "conversion_rate": conversion_rate,
            "customers": (
                Customer.objects.filter(quotes__in=queryset)
                .distinct()
                .values_list("id", "name")
                .order_by("name")
            ),
            "sales_users": (
                get_user_model()
                .objects.filter(pk__in=queryset.values_list("sales_user_id", flat=True).distinct())
                .values_list("id", "username")
                .order_by("username")
            ),
            "month_labels": month_labels,
            "status_labels": status_labels,
            "status_keys": status_keys,
            "series": series,
            "status_totals": status_totals,
        },
    )


def _get_report_queryset(request):
    """Queryset filtrado para reportes (misma lógica que report_view)."""
    current_year = timezone.localdate().year
    date_from = parse_date(request.GET.get("date_from") or "")
    date_to = parse_date(request.GET.get("date_to") or "")
    if date_from and date_to and date_from > date_to:
        date_from = None
        date_to = None
    queryset = Quote.objects.select_related("customer", "sales_user")
    queryset = _apply_common_quote_filters(queryset, request, date_from, date_to)
    if not date_from and not date_to:
        queryset = queryset.filter(issue_date__year=current_year)
    return queryset.order_by("-issue_date")


@login_required
@permission_required("quotes.view_quote", raise_exception=True)
def report_export(request):
    """Exporta el reporte filtrado a CSV."""
    queryset = _get_report_queryset(request)
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="reporte_cotizaciones.csv"'
    response.write("\ufeff")
    writer = csv.writer(response)
    writer.writerow(["Número", "Cliente", "Vendedor", "Estatus", "Total", "Moneda", "Vigencia", "Fecha emisión"])
    status_labels = dict(Quote.STATUS_CHOICES)
    for q in queryset[:2000]:
        writer.writerow([
            q.quote_number,
            q.customer.name,
            q.sales_user.get_full_name() or q.sales_user.username,
            status_labels.get(q.status, q.status),
            q.total,
            q.currency,
            q.valid_until,
            q.issue_date,
        ])
    return response


@login_required
@permission_required("quotes.view_quote", raise_exception=True)
def quote_list_export(request):
    """Exporta la lista de cotizaciones filtrada a CSV."""
    queryset = _get_quote_list_queryset(request)
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="cotizaciones.csv"'
    response.write("\ufeff")  # BOM para Excel UTF-8
    writer = csv.writer(response)
    writer.writerow(["Número", "Cliente", "Vendedor", "Estatus", "Total", "Moneda", "Vigencia", "Fecha emisión"])
    status_labels = dict(Quote.STATUS_CHOICES)
    for q in queryset[:1000]:  # límite razonable
        writer.writerow([
            q.quote_number,
            q.customer.name,
            q.sales_user.get_full_name() or q.sales_user.username,
            status_labels.get(q.status, q.status),
            q.total,
            q.currency,
            q.valid_until,
            q.issue_date,
        ])
    return response
