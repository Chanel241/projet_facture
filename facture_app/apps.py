from django.apps import AppConfig

class FactureAppConfig(AppConfig):
    """
    Configuration pour l'application de facturation.
    Cette application gère la gestion des clients, la création de factures et le suivi des produits pharmaceutiques.
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'facture_app'
    verbose_name = 'Système de facturation Hooyia'