# views.py
from django.views import View
from django.shortcuts import render, redirect
from facture_app.models import Invoice, Customer
from datetime import datetime

class Home(View):
    """ Main view """
    template_name = "home.html"

    def get_context(self):
        return {'invoices': Invoice.objects.select_related('customer', 'save_by').all()}

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, self.get_context())

    def post(self, request, *args, **kwargs):
        return render(request, self.template_name, self.get_context())

class addCustomerView(View):
    """ Add new customer """
    template_name = "add_customer.html"

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name)

    def post(self, request, *args, **kwargs):
        name = request.POST.get('name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        sex = request.POST.get('sex')
        address = request.POST.get('address')
        city = request.POST.get('city')

        if name and email and phone:
            Customer.objects.create(name=name, email=email, phone=phone, sex=sex, address=address, city=city)
            return redirect('home')

        return render(request, self.template_name)

class AddInvoiceView(View):
    """ Add new invoice """
    def post(self, request, *args, **kwargs):
        customer_name = request.POST.get('customer_name')
        invoice_date = request.POST.get('invoice_date')
        total = request.POST.get('total')
        paid = request.POST.get('paid') == 'True'
        invoice_type = request.POST.get('invoice_type')

        # Recherche ou création du client
        customer, created = Customer.objects.get_or_create(name=customer_name, defaults={
            'email': '', 'phone': '', 'sex': '', 'address': '', 'city': ''
        })

        # Conversion de la date
        invoice_date = datetime.strptime(invoice_date, '%Y-%m-%dT%H:%M')

        # Création de la facture
        Invoice.objects.create(
            customer=customer,
            invoice_date_time=invoice_date,
            total=total,
            paid=paid,
            invoice_type=invoice_type,
            save_by=request.user if request.user.is_authenticated else None
        )

        return redirect('home')

class ModifyInvoiceView(View):
    """ Modify invoice """
    def post(self, request, *args, **kwargs):
        invoice_id = request.POST.get('id_modified')
        paid = request.POST.get('modified') == 'True'

        invoice = Invoice.objects.get(pk=invoice_id)
        invoice.paid = paid
        invoice.save()

        return redirect('home')

class DeleteInvoiceView(View):
    """ Delete invoice """
    def post(self, request, *args, **kwargs):
        invoice_id = request.POST.get('id_supprimer')
        Invoice.objects.filter(pk=invoice_id).delete()

        return redirect('home')