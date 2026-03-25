from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models.deletion import ProtectedError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView
from customers.forms import CustomerContactForm, CustomerForm
from customers.models import Customer, CustomerContact

class CustomerListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Customer
    template_name = 'customers/customer_list.html'
    permission_required = 'customers.view_customer'

class CustomerDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Customer
    template_name = 'customers/customer_detail.html'
    permission_required = 'customers.view_customer'

class CustomerCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Customer
    form_class = CustomerForm
    template_name = 'customers/customer_form.html'
    permission_required = 'customers.add_customer'

class CustomerUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Customer
    form_class = CustomerForm
    template_name = 'customers/customer_form.html'
    permission_required = 'customers.change_customer'

class CustomerDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Customer
    template_name = 'customers/customer_confirm_delete.html'
    permission_required = 'customers.delete_customer'
    success_url = reverse_lazy('customers:list')

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        try:
            return super().post(request, *args, **kwargs)
        except ProtectedError:
            messages.error(request, 'No se puede eliminar el cliente porque tiene cotizaciones. Puedes desactivarlo en su ficha.')
            return redirect('customers:detail', pk=self.object.pk)

class CustomerContactCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = CustomerContact
    form_class = CustomerContactForm
    template_name = 'customers/contact_form.html'
    permission_required = 'customers.add_customercontact'

    def get_initial(self):
        initial = super().get_initial()
        customer_id = self.request.GET.get('customer')
        if customer_id:
            initial['customer'] = get_object_or_404(Customer, pk=customer_id)
        return initial

    def get_success_url(self):
        return reverse('customers:detail', kwargs={'pk': self.object.customer_id})

class CustomerContactUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = CustomerContact
    form_class = CustomerContactForm
    template_name = 'customers/contact_form.html'
    permission_required = 'customers.change_customercontact'

    def get_success_url(self):
        return reverse('customers:detail', kwargs={'pk': self.object.customer_id})

@login_required
@permission_required('customers.view_customer', raise_exception=True)
def customer_contacts(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    contacts = list(customer.contacts.values('id', 'full_name').order_by('full_name'))
    return JsonResponse({'contacts': contacts})
