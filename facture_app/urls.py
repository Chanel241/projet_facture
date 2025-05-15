from django.urls import path, include
from . import views
from django.shortcuts import redirect

app_name = 'invoicing'

def custom_logout(request):
    from django.contrib.auth import logout
    logout(request)
    return redirect('invoicing:admin_login')

urlpatterns = [
    path('i18n/', include('django.conf.urls.i18n')),
    path('', views.HomeView.as_view(), name='invoices-list'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('admin-login/', views.AdminLoginView.as_view(), name='admin_login'),
    path('add-admin/', views.AddAdminView.as_view(), name='admin_add_user'),
    path('add-customer/', views.AddCustomerView.as_view(), name='create-customer'),
    path('add-invoice/', views.AddInvoiceView.as_view(), name='create-invoice'),
    path('add-product/', views.AddPharmacyProductView.as_view(), name='add-product'),  # Changé de 'create-product' à 'add-product'
    path('product-list/', views.ProductListView.as_view(), name='product-list'),
    path('modify-product/<int:pk>/', views.ModifyPharmacyProductView.as_view(), name='modify-product'),
    path('delete-product/', views.DeletePharmacyProductView.as_view(), name='delete-product'),
    path('view-invoice/<int:pk>/', views.InvoiceVisualizationView.as_view(), name='view-invoice'),
    path('invoice-pdf/<int:pk>/', views.get_invoice_pdf, name='generate-invoice-pdf'),
    path('modify-invoice/<int:pk>/', views.ModifyInvoiceView.as_view(), name='modify-invoice'),
    path('delete-invoice/', views.DeleteInvoiceView.as_view(), name='delete-invoice'),
    path('logout/', custom_logout, name='logout'),
]