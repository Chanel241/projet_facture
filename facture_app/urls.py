# urls.py
from django.urls import path
from .views import Home, addCustomerView, AddInvoiceView, ModifyInvoiceView, DeleteInvoiceView

urlpatterns = [
    path('', Home.as_view(), name='home'),
    path('add-customer/', addCustomerView.as_view(), name='add_customer'),
    path('add-invoice/', AddInvoiceView.as_view(), name='add_invoice'),
    path('modify-invoice/', ModifyInvoiceView.as_view(), name='modify_invoice'),
    path('delete-invoice/', DeleteInvoiceView.as_view(), name='delete_invoice'),
]