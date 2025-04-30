from django.contrib import admin
from .models import *

# Register your models here.

class AdminCustomer(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone', 'address', 'sex', 'city',)

class AdminInvoice(admin.ModelAdmin):
    list_display = ('customer', 'save_by', 'invoice_date_time', 'total', 'last_updated_date', 'paid', 'invoice_type',)

class AdminArticle(admin.ModelAdmin):
    list_display = ('name', 'quantity', 'unit_price', 'total',)

class AdminPharmacyProduct(admin.ModelAdmin):
    list_display = ('name', 'price', 'stock_quantity','created_at')

admin.site.register(Customer, AdminCustomer)
admin.site.register(Invoice, AdminInvoice)
admin.site.register(Article, AdminArticle)
admin.site.register(PharmacyProduct, AdminPharmacyProduct)
