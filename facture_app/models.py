from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator, MinValueValidator
from django.db import transaction
from django.utils import timezone

class Customer(models.Model):
    """
    Modèle représentant un client dans le système de facturation.
    Stocke les informations personnelles et de contact pour la facturation.
    """
    SEX_TYPES = (
        ('M', _('Homme')),
        ('F', _('Femme')),
    )
    name = models.CharField(max_length=130, verbose_name=_("Nom"))
    email = models.EmailField(unique=True, verbose_name=_("Email"))
    phone = models.CharField(
        max_length=20,
        validators=[RegexValidator(r'^\+?1?\d{9,15}$', _("Le numéro de téléphone doit être au format international (ex. : +1234567890)."))],
        verbose_name=_("Téléphone")
    )
    address = models.CharField(max_length=60, verbose_name=_("Adresse"))
    sex = models.CharField(max_length=1, choices=SEX_TYPES, verbose_name=_("Sexe"))
    city = models.CharField(max_length=30, verbose_name=_("Ville"))
    created_date = models.DateTimeField(auto_now_add=True, verbose_name=_("Date de création"))
    save_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='customers', verbose_name=_("Enregistré par"))

    class Meta:
        verbose_name = _("Client")
        verbose_name_plural = _("Clients")
        ordering = ['name']
        indexes = [models.Index(fields=['email', 'name'])]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.email = self.email.lower()
        super().save(*args, **kwargs)

class Invoice(models.Model):
    """
    Modèle représentant une facture émise à un client.
    Suit le type de facture, l'état de paiement et les articles associés.
    """
    INVOICE_TYPE = (
        ('R', _('Reçu')),
        ('P', _('Facture proforma')),
        ('F', _('Facture')),
    )
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='invoices', verbose_name=_("Client"))
    save_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='invoices', verbose_name=_("Enregistré par"))
    invoice_date_time = models.DateTimeField(auto_now_add=True, verbose_name=_("Date de la facture"))
    last_updated_date = models.DateTimeField(auto_now=True, verbose_name=_("Dernière mise à jour"))
    paid = models.BooleanField(default=False, verbose_name=_("Payé"))
    invoice_type = models.CharField(max_length=1, choices=INVOICE_TYPE, verbose_name=_("Type de facture"))
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name=_("Total"))
    comments = models.TextField(max_length=1000, null=True, blank=True, verbose_name=_("Commentaires"))

    class Meta:
        verbose_name = _("Facture")
        verbose_name_plural = _("Factures")
        indexes = [models.Index(fields=['invoice_date_time', 'customer'])]

    def __str__(self):
        return f"{self.customer.name}_{self.invoice_date_time}"

    def update_total(self):
        """Met à jour le total mis en cache en fonction des articles."""
        articles = self.articles.all()
        self.total = sum(article.get_total for article in articles)
        self.save(update_fields=['total'])

class Article(models.Model):
    """
    Modèle représentant un article (élément) dans une facture.
    Lié à un produit pharmaceutique pour le suivi des stocks.
    """
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='articles', verbose_name=_("Facture"))
    product = models.ForeignKey('PharmacyProduct', on_delete=models.PROTECT, related_name='articles', verbose_name=_("Produit"))
    quantity = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(0.01, message=_("La quantité doit être positive."))],
        verbose_name=_("Quantité")
    )

    class Meta:
        verbose_name = _("Article")
        verbose_name_plural = _("Articles")
        indexes = [models.Index(fields=['invoice', 'product'])]

    def __str__(self):
        return self.product.name

    @property
    def get_total(self):
        return self.quantity * self.product.price

    def save(self, *args, **kwargs):
        """Met à jour le stock et le total de la facture lors de l'enregistrement."""
        with transaction.atomic():
            if self.pk:  # Mise à jour d'un article existant
                old_article = Article.objects.get(pk=self.pk)
                stock_change = old_article.quantity - self.quantity
            else:  # Nouvel article
                stock_change = -self.quantity

            if self.product.stock_quantity + stock_change < 0:
                raise ValueError(_("Stock insuffisant pour le produit : %s") % self.product.name)

            self.product.stock_quantity += stock_change
            self.product.save()
            super().save(*args, **kwargs)
            self.invoice.update_total()

class PharmacyProduct(models.Model):
    """
    Modèle représentant un produit disponible en pharmacie.
    Suit les détails du produit, le stock et les métadonnées de création.
    """
    name = models.CharField(max_length=255, unique=True, verbose_name=_("Nom"))
    description = models.TextField(blank=True, null=True, verbose_name=_("Description"))
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_("Prix"))
    stock_quantity = models.IntegerField(default=0, verbose_name=_("Quantité en stock"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Créé le"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Mis à jour le"))
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_products', verbose_name=_("Créé par"))

    class Meta:
        verbose_name = _("Produit pharmaceutique")
        verbose_name_plural = _("Produits pharmaceutiques")
        ordering = ['name']
        indexes = [models.Index(fields=['name'])]

    def __str__(self):
        return self.name