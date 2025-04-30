from django.db import models
from django.contrib.auth.models import User


class Customer(models.Model):
    """
    Name: Customer model definition
    """
    SEX_TYPES = (
        ('M', 'Masculin'),
        ('F', 'Feminin'),
    )
    name = models.CharField(max_length=130)

    email = models.EmailField(unique=True)

    phone = models.CharField(max_length=130)

    address = models.CharField(max_length=60)

    sex = models.CharField(max_length=1, choices=SEX_TYPES)

    city = models.CharField(max_length=30)

    created_date = models.DateTimeField(auto_now_add=True)

    save_by = models.ForeignKey(User, on_delete=models.PROTECT)

    class Meta:
        verbose_name = "Customer"
        verbose_name_plural = "Customers"
        ordering = ['name']

    def __str__(self):
        return self.name


class Invoice(models.Model):
    """
    Name: Invoices model definition
    Description:
    author: chanelbirimbi@gmail.com
    """

    INVOICE_TYPE = (
        ('R', 'REÇU'),
        ('P', 'PROFORMA FACTURE'),
        ('F', 'FACTURE')
    )

    customer = models.ForeignKey(Customer, on_delete=models.PROTECT)

    save_by = models.ForeignKey(User, on_delete=models.PROTECT)

    invoice_date_time = models.DateTimeField(auto_now_add=True)

    total = models.DecimalField(max_digits=10000, decimal_places=2)

    last_updated_date = models.DateTimeField(null=True, blank=True)

    paid = models.BooleanField(default=False)

    invoice_type = models.CharField(max_length=1, choices=INVOICE_TYPE)

    comments = models.TextField(null=True, max_length=1000, blank=True)

    class Meta:
        verbose_name = "Invoice"
        verbose_name_plural = "Invoices"

    def __str__(self):
        return f"{self.customer.name}_{self.invoice_date_time}"

    @property
    def get_total(self):
        articles = self.article_set.all()
        total = sum(article.get_total for article in articles)
        return total


class Article(models.Model):
    """
    Name: Article model definition
    Description:
    Author: chanelbirimbi@gmail.com
    """

    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE)

    name = models.CharField(max_length=32)

    quantity = models.IntegerField()

    unit_price = models.DecimalField(max_digits=1000, decimal_places=2)

    total = models.DecimalField(max_digits=1000, decimal_places=2)

    class Meta:
        verbose_name = "Article"
        verbose_name_plural = "Articles"

    def __str__(self):
        return self.name
    
    @property
    def get_total(self):
        total = self.quantity * self.unit_price
        return total


class PharmacyProduct(models.Model):
    """
    Name: Pharmacy Product model definition
    Description:
    This model represents a product available in the pharmacy.
    """
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock_quantity = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_products')

    class Meta:
        verbose_name = "Pharmacy Product"
        verbose_name_plural = "Pharmacy Products"
        ordering = ['name']

    def __str__(self):
        return self.name
