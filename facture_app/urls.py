from django.urls import path
from . import views
from django.contrib.auth.views import LogoutView

app_name = 'invoicing'

urlpatterns = [
    # Tableau de bord et liste des factures
    path('', views.HomeView.as_view(), name='invoices-list'),
    # Créer un admin
    path('add-admin/', views.AddAdminView.as_view(), name='admin_add_user'),  # Changé de 'create-admin' à 'admin_add_user'
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
    path('logout/', LogoutView.as_view(next_page='invoicing:invoices-list'), name='logout'),
]