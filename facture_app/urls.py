from django.urls import path, include
from . import views
from django.contrib.auth.views import LogoutView, LoginView
from django.shortcuts import redirect

app_name = 'invoicing'

# Vue personnalisée pour la déconnexion
def custom_logout(request):
    from django.contrib.auth import logout
    logout(request)
    return redirect('invoicing:admin_login')

urlpatterns = [
    # Nécessaire pour set_language
    path('i18n/', include('django.conf.urls.i18n')),
    # Tableau de bord et liste des factures
    path('', views.HomeView.as_view(), name='invoices-list'),
    # Page de connexion
    path('login/', LoginView.as_view(template_name='facture_app/login.html'), name='login'),
    # Page de connexion pour administration
    path('admin-login/', LoginView.as_view(template_name='facture_app/admin_login.html'), name='admin_login'),
    # Créer un admin
    path('add-admin/', views.AddAdminView.as_view(), name='admin_add_user'),
    # Créer un client
    path('add-customer/', views.AddCustomerView.as_view(), name='create-customer'),
    # Créer une facture
    path('add-invoice/', views.AddInvoiceView.as_view(), name='create-invoice'),
    # Créer un produit
    path('add-product/', views.AddPharmacyProductView.as_view(), name='create-product'),
    # Visualiser une facture
    path('view-invoice/<int:pk>/', views.InvoiceVisualizationView.as_view(), name='view-invoice'),
    # Générer un PDF pour une facture
    path('invoice-pdf/<int:pk>/', views.get_invoice_pdf, name='generate-invoice-pdf'),
    # Modifier une facture
    path('modify-invoice/', views.ModifyInvoiceView.as_view(), name='modify-invoice'),
    # Supprimer une facture
    path('delete-invoice/', views.DeleteInvoiceView.as_view(), name='delete-invoice'),
    # Déconnexion
    path('logout/', custom_logout, name='logout'),
]