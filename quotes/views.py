from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db import models, transaction
from django.db.models import Count, DecimalField, Sum, Value
from django.db.models.functions import Coalesce
from django.db.models.functions import ExtractMonth
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.staticfiles import finders
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_POST
from django.views.generic import DetailView, ListView, TemplateView
from pathlib import Path

from quotes.forms import QuoteForm, QuoteItemFormSet
from customers.models import Customer
from quotes.models import Quote, QuoteItem

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard.html"


class QuoteListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Quote
    template_name = "quotes/quote_list.html"
    permission_required = "quotes.view_quote"
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset().select_related("customer", "sales_user")
        if not self.request.user.is_superuser:
            queryset = queryset.filter(sales_user=self.request.user)
        status = self.request.GET.get("status")
        customer_id = self.request.GET.get("customer")
        sales_user_id = self.request.GET.get("sales_user")
        date_from = parse_date(self.request.GET.get("date_from") or "")
        date_to = parse_date(self.request.GET.get("date_to") or "")

        if status:
            queryset = queryset.filter(status=status)
        if customer_id:
            try:
                customer_id = int(customer_id)
                queryset = queryset.filter(customer_id=customer_id)
            except (TypeError, ValueError):
                pass
        if sales_user_id:
            try:
                sales_user_id = int(sales_user_id)
                queryset = queryset.filter(sales_user_id=sales_user_id)
            except (TypeError, ValueError):
                pass
        if date_from:
            queryset = queryset.filter(issue_date__gte=date_from)
        if date_to:
            queryset = queryset.filter(issue_date__lte=date_to)
        return queryset

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
        return context


class QuoteDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Quote
    template_name = "quotes/quote_detail.html"
    permission_required = "quotes.view_quote"

    def get_queryset(self):
        queryset = super().get_queryset().select_related("customer", "sales_user")
        if not self.request.user.is_superuser:
            queryset = queryset.filter(sales_user=self.request.user)
        return queryset


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
                    formset.save()
                    quote.recalculate_totals()
                messages.success(request, "Cotización creada.")
                return redirect("quotes:detail", pk=quote.pk)
    else:
        form = QuoteForm(initial={"status": Quote.STATUS_DRAFT})
        formset = QuoteItemFormSet()
    return render(
        request,
        "quotes/quote_form.html",
        {"form": form, "formset": formset, "is_edit": False},
    )


@login_required
@permission_required("quotes.change_quote", raise_exception=True)
def quote_update(request, pk):
    quote = get_object_or_404(Quote, pk=pk)
    if not request.user.is_superuser and quote.sales_user != request.user:
        messages.error(request, "No tienes permiso para editar esta cotización.")
        return redirect("quotes:detail", pk=pk)
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
                    formset.save()
                    updated_quote.recalculate_totals()
                messages.success(request, "Cotización actualizada.")
                return redirect("quotes:detail", pk=quote.pk)
    else:
        form = QuoteForm(instance=quote)
        formset = QuoteItemFormSet(instance=quote)
    return render(
        request,
        "quotes/quote_form.html",
        {"form": form, "formset": formset, "is_edit": True, "quote": quote},
    )


@login_required
@permission_required("quotes.change_quote", raise_exception=True)
@require_POST
def quote_send(request, pk):
    quote = get_object_or_404(Quote, pk=pk)
    if not request.user.is_superuser and quote.sales_user != request.user:
        messages.error(request, "No tienes permiso para enviar esta cotización.")
        return redirect("quotes:detail", pk=pk)
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
    messages.success(request, "Cotización enviada.")
    return redirect("quotes:detail", pk=pk)


@login_required
@permission_required("quotes.change_quote", raise_exception=True)
@require_POST
def quote_mark(request, pk, status):
    quote = get_object_or_404(Quote, pk=pk)
    if not request.user.is_superuser and quote.sales_user != request.user:
        messages.error(request, "No tienes permiso para modificar esta cotización.")
        return redirect("quotes:detail", pk=pk)
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
    messages.success(request, "Estado actualizado.")
    return redirect("quotes:detail", pk=pk)


@login_required
@permission_required("quotes.view_quote", raise_exception=True)
def quote_pdf(request, pk):
    quote = get_object_or_404(Quote, pk=pk)
    from weasyprint import HTML
    logo_path = finders.find("img/logo.png")
    header_right_path = finders.find("img/quote_header_rigth.png")
    logo_uri = _build_file_uri(logo_path)
    header_right_uri = _build_file_uri(header_right_path)
    html_string = render_to_string(
        "quotes/quote_pdf.html",
        {
            "quote": quote,
            "company_name": "Sistemas de Conteo de Personas.",
            "company_website": "www.sisconper.com",
            "company_street": "Blvd. Paseo de la República No. 13020 Int. 1307",
            "company_colony": "Col. Juriquilla, Querétaro, Qro.",
            "company_postal_code": "C.P. 76230",
            "company_phone": "(442) 245 7000",
            "company_mobile": "",
            "company_rfc": "SCP070410C43",
            "company_email": "info@sisconper.com",
            "company_logo_uri": logo_uri,
            "header_right_uri": header_right_uri,
        },
    )
    pdf_file = HTML(string=html_string, base_url=request.build_absolute_uri()).write_pdf()
    response = HttpResponse(pdf_file, content_type="application/pdf")
    filename_number = quote.quote_number
    if filename_number.startswith("COT-"):
        filename_number = filename_number.replace("COT-", "SCP-", 1)
    elif not filename_number.startswith("SCP-"):
        filename_number = f"SCP-{filename_number}"
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

    if date_from:
        queryset = queryset.filter(issue_date__gte=date_from)
    if date_to:
        queryset = queryset.filter(issue_date__lte=date_to)
    if date_from and date_to and date_from > date_to:
        messages.error(request, "La fecha desde debe ser menor o igual a la fecha hasta.")
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
                .objects.filter(quote__in=queryset)
                .distinct()
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
