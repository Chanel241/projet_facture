from django import forms
from .models import Customer, Invoice, PharmacyProduct
from django.utils.translation import gettext_lazy as _

class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ['name', 'email', 'phone', 'address', 'sex', 'city']
        labels = {
            'name': _("Nom"),
            'email': _("Email"),
            'phone': _("Téléphone"),
            'address': _("Adresse"),
            'sex': _("Sexe"),
            'city': _("Ville"),
        }

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if Customer.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError(_("Cet email est déjà utilisé."))
        return email

class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = ['customer', 'invoice_type', 'comments']
        labels = {
            'customer': _("Client"),
            'invoice_type': _("Type de facture"),
            'comments': _("Commentaires"),
        }

class PharmacyProductForm(forms.ModelForm):
    class Meta:
        model = PharmacyProduct
        fields = ['name', 'description', 'price', 'stock_quantity']
        labels = {
            'name': _("Nom"),
            'description': _("Description"),
            'price': _("Prix"),
            'stock_quantity': _("Quantité en stock"),
        }

    def clean_price(self):
        price = self.cleaned_data['price']
        if price < 0:
            raise forms.ValidationError(_("Le prix ne peut pas être négatif."))
        return price

    def clean_stock_quantity(self):
        stock = self.cleaned_data['stock_quantity']
        if stock < 0:
            raise forms.ValidationError(_("La quantité en stock ne peut pas être négative."))
        return stock