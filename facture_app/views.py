from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
from django.http import HttpResponse, Http404
from django.db import transaction
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.utils.translation import gettext_lazy as _
from django.template.loader import get_template
from .models import Customer, Invoice, Article, PharmacyProduct
from .utils import pagination, get_invoice
from .forms import CustomerForm, InvoiceForm, PharmacyProductForm
from celery import shared_task
import pdfkit
import datetime
from django.utils import timezone

class SuperuserRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_active and self.request.user.is_superuser

class HomeView(SuperuserRequiredMixin, View):
    template_name = 'home.html'

    def get(self, request, *args, **kwargs):
        invoices = Invoice.objects.select_related('customer', 'save_by').order_by('-invoice_date_time')
        items = pagination(request, invoices)
        context = {'invoices': items}
        return render(request, self.template_name, context)

class AddCustomerView(SuperuserRequiredMixin, View):
    template_name = 'add_customer.html'

    def get(self, request, *args, **kwargs):
        form = CustomerForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request, *args, **kwargs):
        form = CustomerForm(request.POST)
        if form.is_valid():
            customer = form.save(commit=False)
            customer.save_by = request.user
            customer.save()
            messages.success(request, _("Client enregistré avec succès."))
            return redirect('invoicing:invoices-list')
        messages.error(request, _("Données invalides fournies."))
        return render(request, self.template_name, {'form': form})

class AddInvoiceView(SuperuserRequiredMixin, View):
    template_name = 'add_invoice.html'

    def get(self, request, *args, **kwargs):
        form = InvoiceForm()
        products = PharmacyProduct.objects.all()
        customers = Customer.objects.all()
        return render(request, self.template_name, {'form': form, 'products': products, 'customers': customers})

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        form = InvoiceForm(request.POST)
        products = request.POST.getlist('product')
        quantities = request.POST.getlist('qty')
        if form.is_valid():
            # Vérifier le stock pour chaque produit
            for i in range(len(products)):
                try:
                    product = PharmacyProduct.objects.get(id=products[i])
                    qty = float(quantities[i])
                    if qty > product.stock_quantity:
                        messages.error(request, _("Quantité demandée (%s) dépasse le stock disponible (%s) pour %s.") % (qty, product.stock_quantity, product.name))
                        return render(request, self.template_name, {'form': form, 'products': PharmacyProduct.objects.all(), 'customers': Customer.objects.all()})
                except PharmacyProduct.DoesNotExist:
                    messages.error(request, _("Produit non trouvé."))
                    return render(request, self.template_name, {'form': form, 'products': PharmacyProduct.objects.all(), 'customers': Customer.objects.all()})

            if len(products) == len(quantities):
                invoice = form.save(commit=False)
                invoice.save_by = request.user
                invoice.save()
                for i in range(len(products)):
                    article = Article(
                        invoice=invoice,
                        product_id=products[i],
                        quantity=float(quantities[i])
                    )
                    article.full_clean()
                    article.save()
                messages.success(request, _("Facture créée avec succès."))
                return redirect('invoicing:invoices-list')
            messages.error(request, _("Données de produit incohérentes."))
        else:
            messages.error(request, _("Données invalides fournies."))
        return render(request, self.template_name, {'form': form, 'products': PharmacyProduct.objects.all(), 'customers': Customer.objects.all()})

class AddPharmacyProductView(SuperuserRequiredMixin, View):
    template_name = 'add_product.html'

    def get(self, request, *args, **kwargs):
        form = PharmacyProductForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request, *args, **kwargs):
        form = PharmacyProductForm(request.POST)
        if form.is_valid():
            product = form.save(commit=False)
            product.created_by = request.user
            product.save()
            messages.success(request, _("Produit enregistré avec succès."))
            return redirect('invoicing:invoices-list')
        messages.error(request, _("Données invalides fournies."))
        return render(request, self.template_name, {'form': form})

class InvoiceVisualizationView(SuperuserRequiredMixin, View):
    template_name = 'invoice.html'

    def get(self, request, *args, **kwargs):
        context = get_invoice(kwargs.get('pk'))
        if not context:
            messages.error(request, _("Facture non trouvée."))
            return redirect('invoicing:invoices-list')
        return render(request, self.template_name, context)

class ModifyInvoiceView(SuperuserRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            invoice = Invoice.objects.get(id=request.POST.get('id_modified'))
            invoice.paid = request.POST.get('modified') == 'True'
            invoice.last_updated_date = timezone.now()
            invoice.save()
            messages.success(request, _("Facture mise à jour avec succès."))
        except Invoice.DoesNotExist:
            messages.error(request, _("Facture non trouvée."))
        return redirect('invoicing:invoices-list')

class DeleteInvoiceView(SuperuserRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            invoice = Invoice.objects.get(pk=request.POST.get('id_supprimer'))
            invoice.delete()
            messages.success(request, _("Facture supprimée avec succès."))
        except Invoice.DoesNotExist:
            messages.error(request, _("Facture non trouvée."))
        return redirect('invoicing:invoices-list')

@shared_task
def generate_invoice_pdf_task(pk):
    """Tâche Celery pour générer un PDF de facture de manière asynchrone."""
    context = get_invoice(pk)
    if not context:
        return None
    context['date'] = datetime.datetime.today()
    template = get_template('invoice.html')
    html = template.render(context)
    options = {
        'page-size': 'Letter',
        'encoding': 'UTF-8',
        'enable-local-file-access': ''
    }
    pdf = pdfkit.from_string(html, False, options)
    return pdf

def get_invoice_pdf(request, *args, **kwargs):
    """Déclenche la génération asynchrone de PDF et retourne le résultat."""
    pk = kwargs.get('pk')
    result = generate_invoice_pdf_task.delay(pk)
    pdf = result.get(timeout=30)  # Attendre jusqu'à 30 secondes
    if not pdf:
        raise Http404(_("Facture non trouvée ou génération de PDF échouée"))
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="facture_{pk}.pdf"'
    return response