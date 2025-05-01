from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .models import Invoice, Article

def pagination(request, invoices, items_per_page=5):
    """
    Pagine un queryset de factures.
    Args:
        request: L'objet de requête HTTP.
        invoices: Le queryset à paginer.
        items_per_page: Nombre d'éléments par page (par défaut : 5).
    Returns:
        Objet de page paginée.
    """
    page = request.GET.get('page', 1)
    paginator = Paginator(invoices, items_per_page)
    try:
        items_page = paginator.page(page)
    except PageNotAnInteger:
        items_page = paginator.page(1)
    except EmptyPage:
        items_page = paginator.page(paginator.num_pages)
    return items_page

def get_invoice(pk):
    """
    Récupère une facture et ses articles.
    Args:
        pk: La clé primaire de la facture.
    Returns:
        Dictionnaire avec la facture et les articles, ou None si non trouvé.
    """
    try:
        obj = Invoice.objects.select_related('customer', 'save_by').get(pk=pk)
        articles = obj.articles.select_related('product').all()
        return {'obj': obj, 'articles': articles}
    except Invoice.DoesNotExist:
        return None