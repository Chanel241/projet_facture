from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import Customer, Invoice, Article, PharmacyProduct
from django.utils import timezone

class AdminCustomer(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone', 'address', 'sex', 'city', 'created_date')
    list_filter = ('sex', 'city', 'created_date')
    search_fields = ('name', 'email', 'phone')
    list_per_page = 25
    ordering = ('name',)
    readonly_fields = ('created_date', 'save_by')
    fieldsets = (
        (None, {'fields': ('name', 'email', 'phone', 'address', 'city')}),
        (_('Informations personnelles'), {'fields': ('-apple-sex',)}),
        (_('Métadonnées'), {'fields': ('save_by', 'created_date')}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('save_by')

class AdminInvoice(admin.ModelAdmin):
    list_display = ('customer', 'save_by', 'invoice_date_time', 'total', 'paid', 'invoice_type', 'last_updated_date')
    list_filter = ('paid', 'invoice_type', 'invoice_date_time')
    search_fields = ('customer__name', 'comments')
    list_per_page = 25
    date_hierarchy = 'invoice_date_time'
    readonly_fields = ('invoice_date_time', 'last_updated_date', 'save_by')
    fieldsets = (
        (None, {'fields': ('customer', 'invoice_type', 'total', 'paid', 'comments')}),
        (_('Métadonnées'), {'fields': ('save_by', 'invoice_date_time', 'last_updated_date')}),
    )
    actions = ['mark_as_paid']

    def mark_as_paid(self, request, queryset):
        queryset.update(paid=True, last_updated_date=timezone.now())
        self.message_user(request, _("Factures sélectionnées marquées comme payées."))
    mark_as_paid.short_description = _("Marquer les factures sélectionnées comme payées")

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('customer', 'save_by').prefetch_related('articles')

class AdminArticle(admin.ModelAdmin):
    list_display = ('product', 'invoice', 'quantity', 'get_total')
    list_filter = ('invoice__invoice_type',)
    search_fields = ('product__name', 'invoice__customer__name')
    list_per_page = 25
    readonly_fields = ('get_total',)
    fieldsets = (
        (None, {'fields': ('invoice', 'product', 'quantity')}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('invoice__customer', 'product')

class AdminPharmacyProduct(admin.ModelAdmin):
    list_display = ('name', 'price', 'stock_quantity', 'created_at', 'updated_at')
    list_filter = ('created_at',)
    search_fields = ('name', 'description')
    list_per_page = 25
    readonly_fields = ('created_at', 'updated_at', 'created_by')
    fieldsets = (
        (None, {'fields': ('name', 'description', 'price', 'stock_quantity')}),
        (_('Métadonnées'), {'fields': ('created_by', 'created_at', 'updated_at')}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('created_by')

admin.site.register(Customer, AdminCustomer)
admin.site.register(Invoice, AdminInvoice)
admin.site.register(Article, AdminArticle)
admin.site.register(PharmacyProduct, AdminPharmacyProduct)

admin.site.site_title = _("Administration du système de facturation ECole-241")
admin.site.site_header = _("Administration du système de facturation Ecole-241")
admin.site.index_title = _("Tableau de bord du système de facturation Ecole-241")