from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
from django.http import HttpResponse, Http404
from django.db import transaction
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.utils.translation import gettext_lazy as _
from django.template.loader import render_to_string
from .models import Customer, Invoice, Article, PharmacyProduct
from .utils import pagination, get_invoice
from .forms import CustomerForm, InvoiceForm, PharmacyProductForm
from celery import shared_task
import datetime
from django.utils import timezone
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
import logging
import subprocess
import os
import time
from django.conf import settings

logger = logging.getLogger(__name__)

class SuperuserRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_active and self.request.user.is_superuser

class HomeView(SuperuserRequiredMixin, View):
    template_name = 'facture_app/home.html'  # Ajouté le chemin explicite

    def get(self, request, *args, **kwargs):
        invoices = Invoice.objects.select_related('customer', 'save_by').order_by('-invoice_date_time')
        items = pagination(request, invoices)
        context = {'invoices': items}
        return render(request, self.template_name, context)

class AddAdminView(SuperuserRequiredMixin, View):
    template_name = 'facture_app/admin_add_user.html'  # Correct

    def get(self, request, *args, **kwargs):
        form = UserCreationForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request, *args, **kwargs):
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_staff = True
            user.is_superuser = True
            user.save()
            messages.success(request, _("Administrateur créé avec succès."))
            return redirect('invoicing:invoices-list')
        messages.error(request, _("Données invalides fournies."))
        return render(request, self.template_name, {'form': form})

class AddCustomerView(SuperuserRequiredMixin, View):
    template_name = 'facture_app/add_customer.html'  # Ajouté le chemin explicite

    def get(self, request, *args, **kwargs):
        form = CustomerForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request, *args, **kwargs):
        form = CustomerForm(request.POST)
        if form.is_valid():
            customer = form.save(commit=False)
            customer.save_by = request.user
            customer.save()
            messages.success(request, _("Client enregistré avec succès."))
            return redirect('invoicing:invoices-list')
        else:
            print("Formulaire invalide. Erreurs :", form.errors)
            messages.error(request, _("Données invalides fournies."))
        return render(request, self.template_name, {'form': form})

class AddInvoiceView(SuperuserRequiredMixin, View):
    template_name = 'facture_app/add_invoice.html'  # Ajouté le chemin explicite

    def get(self, request, *args, **kwargs):
        form = InvoiceForm()
        products = PharmacyProduct.objects.all()
        customers = Customer.objects.all()
        print(f"Nombre de clients disponibles : {customers.count()}")
        print(f"Clients dans le formulaire : {list(form.fields['customer'].queryset)}")
        return render(request, self.template_name, {'form': form, 'products': products, 'customers': customers})

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        form = InvoiceForm(request.POST)
        products = request.POST.getlist('product')
        quantities = request.POST.getlist('qty')
        if form.is_valid():
            for i in range(len(products)):
                try:
                    product = PharmacyProduct.objects.get(id=products[i])
                    qty = float(quantities[i])
                    if qty > product.stock_quantity:
                        messages.error(request, _("Quantité demandée (%s) dépasse le stock disponible (%s) pour %s.") % (qty, product.stock_quantity, product.name))
                        return render(request, self.template_name, {'form': form, 'products': PharmacyProduct.objects.all(), 'customers': Customer.objects.all()})
                except PharmacyProduct.DoesNotExist:
                    messages.error(request, _("Produit non trouvé."))
                    return render(request, self.template_name, {'form': form, 'products': PharmacyProduct.objects.all(), 'customers': Customer.objects.all()})

            if len(products) == len(quantities):
                invoice = form.save(commit=False)
                invoice.save_by = request.user
                invoice.save()
                for i in range(len(products)):
                    article = Article(
                        invoice=invoice,
                        product_id=products[i],
                        quantity=float(quantities[i])
                    )
                    article.full_clean()
                    article.save()
                messages.success(request, _("Facture créée avec succès."))
                return redirect('invoicing:invoices-list')
            messages.error(request, _("Données de produit incohérentes."))
        else:
            messages.error(request, _("Données invalides fournies."))
        return render(request, self.template_name, {'form': form, 'products': PharmacyProduct.objects.all(), 'customers': Customer.objects.all()})

class AddPharmacyProductView(SuperuserRequiredMixin, View):
    template_name = 'facture_app/add_product.html'  # Ajouté le chemin explicite

    def get(self, request, *args, **kwargs):
        form = PharmacyProductForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request, *args, **kwargs):
        form = PharmacyProductForm(request.POST)
        if form.is_valid():
            product = form.save(commit=False)
            product.created_by = request.user
            product.save()
            messages.success(request, _("Produit enregistré avec succès."))
            return redirect('invoicing:invoices-list')
        messages.error(request, _("Données invalides fournies."))
        return render(request, self.template_name, {'form': form})

class InvoiceVisualizationView(SuperuserRequiredMixin, View):
    template_name = 'facture_app/invoice.html'  # Ajouté le chemin explicite

    def get(self, request, *args, **kwargs):
        context = get_invoice(kwargs.get('pk'))
        if not context:
            messages.error(request, _("Facture non trouvée."))
            return redirect('invoicing:invoices-list')
        return render(request, self.template_name, context)

class ModifyInvoiceView(SuperuserRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            invoice = Invoice.objects.get(id=request.POST.get('id_modified'))
            invoice.paid = request.POST.get('modified') == 'True'
            invoice.last_updated_date = timezone.now()
            invoice.save()
            messages.success(request, _("Facture mise à jour avec succès."))
        except Invoice.DoesNotExist:
            messages.error(request, _("Facture non trouvée."))
        return redirect('invoicing:invoices-list')

class DeleteInvoiceView(SuperuserRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            invoice = Invoice.objects.get(pk=request.POST.get('id_supprimer'))
            invoice.delete()
            messages.success(request, _("Facture supprimée avec succès."))
        except Invoice.DoesNotExist:
            messages.error(request, _("Facture non trouvée."))
        return redirect('invoicing:invoices-list')

@shared_task
def generate_invoice_pdf_task(pk):
    """Tâche Celery pour générer un PDF de facture de manière asynchrone avec LaTeX."""
    logger.info(f"Début de la génération du PDF pour la facture ID={pk}")
    try:
        # Récupérer les données de la facture
        context = get_invoice(pk)
        if not context:
            logger.error(f"Facture ID={pk} non trouvée")
            return None
        context['date'] = datetime.datetime.now()  # Ajouter la date actuelle pour vérifier la dynamique
        context['is_pdf'] = True
        if not context.get('obj') or not context.get('obj').customer:
            logger.error(f"Données invalides pour la facture ID={pk}: client ou facture manquant")
            return None

        # Loguer les données pour vérifier qu'elles changent
        logger.info(f"Contexte utilisé pour la facture ID={pk}: {context}")

        # Rendre le modèle LaTeX
        template = 'facture_app/invoice_template.tex'
        latex_content = render_to_string(template, context)
        logger.info(f"LaTeX généré pour la facture ID={pk}: {latex_content[:500]}...")  # Loguer un extrait

        # Créer un répertoire temporaire pour les fichiers
        temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp')
        os.makedirs(temp_dir, exist_ok=True)
        timestamp = int(time.time())  # Ajouter un timestamp pour éviter les conflits
        tex_file_path = os.path.join(temp_dir, f'invoice_{pk}_{timestamp}.tex')
        pdf_file_path = os.path.join(temp_dir, f'invoice_{pk}_{timestamp}.pdf')

        # Nettoyer les fichiers temporaires existants pour cette facture
        for file_name in os.listdir(temp_dir):
            if file_name.startswith(f'invoice_{pk}_'):
                file_path = os.path.join(temp_dir, file_name)
                os.remove(file_path)
                logger.info(f"Fichier temporaire supprimé : {file_path}")

        # Écrire le fichier LaTeX temporaire
        with open(tex_file_path, 'w', encoding='utf-8') as f:
            f.write(latex_content)
        logger.info(f"Fichier LaTeX écrit à : {tex_file_path}")

        # Générer le PDF avec latexmk
        result = subprocess.run(
            ['latexmk', '-pdf', '-interaction=nonstopmode', '-f', tex_file_path],
            cwd=temp_dir,
            capture_output=True,
            text=True
        )
        logger.info(f"Commande latexmk exécutée pour la facture ID={pk}: {result.stdout}")
        if result.returncode != 0:
            logger.error(f"Erreur lors de l'exécution de latexmk pour la facture ID={pk}: {result.stderr}")
            raise Exception(f"Erreur latexmk : {result.stderr}")

        # Vérifier si le PDF a été généré
        if not os.path.exists(pdf_file_path):
            logger.error(f"PDF non généré pour la facture ID={pk}")
            raise Exception("Échec de la génération du PDF")

        # Lire le PDF et le retourner
        with open(pdf_file_path, 'rb') as f:
            pdf_content = f.read()
        logger.info(f"PDF généré avec succès pour la facture ID={pk}")
        return pdf_content
    except Exception as e:
        logger.error(f"Erreur dans generate_invoice_pdf_task pour la facture ID={pk}: {str(e)}")
        raise

def get_invoice_pdf(request, *args, **kwargs):
    """Déclenche la génération asynchrone de PDF et retourne le résultat."""
    pk = kwargs.get('pk')
    logger.info(f"Envoi de la tâche generate_invoice_pdf_task pour la facture ID={pk}")
    result = generate_invoice_pdf_task.delay(pk)
    logger.info(f"Tâche envoyée avec ID : {result.id}")
    try:
        pdf = result.get(timeout=150)
        logger.info(f"Tâche terminée avec succès pour la facture ID={pk}")
        if not pdf:
            logger.error(f"Facture ID={pk} non trouvée ou génération de PDF échouée")
            raise Http404(_("Facture non trouvée ou génération de PDF échouée"))
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="facture_{pk}.pdf"'
        return response
    except Exception as e:
        logger.error(f"Erreur lors de la génération du PDF pour la facture ID={pk}: {str(e)}")
        return HttpResponse(f"Erreur lors de la génération du PDF : {str(e)}", status=500)

def custom_404(request, exception):
    return render(request, 'facture_app/404.html', status=404)

def custom_500(request):
    return render(request, 'facture_app/500.html', status=500)