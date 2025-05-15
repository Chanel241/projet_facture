from django.shortcuts import render, redirect
from django.views import View
from django.contrib.messages import get_messages
from django.contrib import messages
from django.http import HttpResponse, Http404
from django.db import transaction
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.utils.translation import gettext_lazy as _
from django.template.loader import render_to_string
from .models import Customer, Invoice, Article, PharmacyProduct
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from .utils import pagination, get_invoice
from .forms import CustomerForm, InvoiceForm, PharmacyProductForm
from celery import shared_task
import datetime
from django.utils import timezone
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
import logging
import subprocess
import os
import time
from django.conf import settings
from django.utils import translation
from django.views.decorators.csrf import csrf_protect
from django.utils.decorators import method_decorator

logger = logging.getLogger(__name__)

class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        is_staff = self.request.user.is_active and self.request.user.is_staff
        logger.info(f"StaffRequiredMixin: user={self.request.user.username or 'Anonymous'}, is_staff={is_staff}")
        return is_staff

class HomeView(LoginRequiredMixin, View):  # Changé de StaffRequiredMixin à LoginRequiredMixin
    template_name = 'facture_app/home.html'

    def get(self, request, *args, **kwargs):
        logger.info(f"HomeView: Langue active={translation.get_language()}, Utilisateur={request.user.username or 'Anonymous'}")
        invoices = Invoice.objects.select_related('customer', 'save_by').order_by('-invoice_date_time')
        items = pagination(request, invoices)
        context = {'invoices': items}
        return render(request, self.template_name, context)

class LoginView(LoginView):  # Non utilisé, mais conservé pour compatibilité
    template_name = 'facture_app/login.html'
    form_class = AuthenticationForm

    def form_invalid(self, form):
        logger.error(f"LoginView: Échec de la connexion pour {form.data.get('username')}: {form.errors}")
        messages.error(self.request, _("Nom d'utilisateur ou mot de passe incorrect."))
        return super().form_invalid(form)

class AdminLoginView(LoginView):
    template_name = 'facture_app/admin_login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        url = reverse_lazy('invoicing:invoices-list')  # Redirige tous les utilisateurs vers /fr/
        logger.info(f"AdminLoginView: Redirection de {self.request.user.username} vers {url}")
        return url

@method_decorator(csrf_protect, name='dispatch')
class AddAdminView(StaffRequiredMixin, View):
    template_name = 'facture_app/admin_add_user.html'

    def get(self, request, *args, **kwargs):
        logger.info(f"AddAdminView GET: Langue={request.session.get('django_language')}, Utilisateur={request.user.username}")
        form1 = UserCreationForm(prefix="form1")
        form2 = UserCreationForm(prefix="form2")
        return render(request, self.template_name, {'form1': form1, 'form2': form2})

    def post(self, request, *args, **kwargs):
        logger.info(f"AddAdminView POST: Langue={translation.get_language()}, Données={request.POST}")
        submitted_form_id = request.POST.get('form_id')
        saved = False

        if submitted_form_id == 'form1':
            form1 = UserCreationForm(request.POST, prefix="form1")
            form2 = UserCreationForm(prefix="form2")
            if form1.is_valid():
                user = form1.save(commit=False)
                user.is_staff = False
                user.is_active = request.POST.get('form1-auth_mode') == 'active'
                user.save()
                saved = True
                logger.info(f"Utilisateur standard {user.username} créé, is_staff={user.is_staff}, is_active={user.is_active}")
                messages.success(request, _("Utilisateur standard créé avec succès."))
            else:
                logger.error(f"Erreurs form1: {form1.errors}")
                messages.error(request, _("Erreur formulaire utilisateur standard: %s") % form1.errors.as_text())
        elif submitted_form_id == 'form2':
            form1 = UserCreationForm(prefix="form1")
            form2 = UserCreationForm(request.POST, prefix="form2")
            if form2.is_valid():
                user = form2.save(commit=False)
                user.is_staff = True
                user.is_superuser = True
                user.is_active = request.POST.get('form2-auth_mode') == 'active'
                user.save()
                saved = True
                logger.info(f"Administrateur {user.username} créé, is_staff={user.is_staff}, is_superuser={user.is_superuser}, is_active={user.is_active}")
                messages.success(request, _("Administrateur créé avec succès."))
            else:
                logger.error(f"Erreurs form2: {form2.errors}")
                messages.error(request, _("Erreur formulaire administrateur: %s") % form2.errors.as_text())
        else:
            form1 = UserCreationForm(prefix="form1")
            form2 = UserCreationForm(prefix="form2")
            logger.error("Aucun form_id valide soumis")
            messages.error(request, _("Aucun formulaire valide soumis."))

        if saved:
            return redirect('invoicing:invoices-list')
        return render(request, self.template_name, {'form1': form1, 'form2': form2})
    
class AddCustomerView(LoginRequiredMixin, View):
    template_name = 'facture_app/add_customer.html'

    def get(self, request, *args, **kwargs):
        form = CustomerForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request, *args, **kwargs):
        form = CustomerForm(request.POST)
        if form.is_valid():
            customer = form.save(commit=False)
            customer.save_by = request.user
            customer.save()
            logger.info(f"Client {customer.name} créé par {request.user.username}")
            messages.success(request, _("Client enregistré avec succès."))
            return redirect('invoicing:invoices-list')
        else:
            logger.error(f"Erreurs formulaire client: {form.errors}")
            messages.error(request, _("Données invalides: %s") % form.errors.as_text())
        return render(request, self.template_name, {'form': form})

class AddInvoiceView(LoginRequiredMixin, View):
    template_name = 'facture_app/add_invoice.html'

    def get(self, request, *args, **kwargs):
        form = InvoiceForm()
        products = PharmacyProduct.objects.all()
        customers = Customer.objects.all()
        logger.info(f"AddInvoiceView: Clients={customers.count()}, Produits={products.count()}")
        return render(request, self.template_name, {'form': form, 'products': products, 'customers': customers})

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        form = InvoiceForm(request.POST)
        products = request.POST.getlist('product')
        quantities = request.POST.getlist('qty')
        errors = []
        if form.is_valid():
            for i in range(len(products)):
                try:
                    product = PharmacyProduct.objects.get(id=products[i])
                    qty = float(quantities[i])
                    if qty > product.stock_quantity:
                        errors.append(_("Quantité demandée (%s) dépasse le stock (%s) pour %s.") % (qty, product.stock_quantity, product.name))
                except PharmacyProduct.DoesNotExist:
                    errors.append(_("Produit ID %s non trouvé.") % products[i])

            if errors:
                for error in errors:
                    messages.error(request, error)
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
                logger.info(f"Facture ID={invoice.id} créée par {request.user.username}")
                messages.success(request, _("Facture créée avec succès."))
                return redirect('invoicing:invoices-list')
            messages.error(request, _("Données produit incohérentes."))
        else:
            logger.error(f"Erreurs formulaire facture: {form.errors}")
            messages.error(request, _("Données invalides: %s") % form.errors.as_text())
        return render(request, self.template_name, {'form': form, 'products': PharmacyProduct.objects.all(), 'customers': Customer.objects.all()})

class AddPharmacyProductView(LoginRequiredMixin, View):
    template_name = 'facture_app/add_product.html'

    def get(self, request, *args, **kwargs):
        form = PharmacyProductForm(initial={'name': ''})
        return render(request, self.template_name, {'form': form})

    def post(self, request, *args, **kwargs):
        form = PharmacyProductForm(request.POST)
        if form.is_valid():
            product = form.save(commit=False)
            product.created_by = request.user
            product.save()
            logger.info(f"Produit {product.name} créé par {request.user.username}")
            messages.success(request, _("Produit enregistré avec succès."))
            return redirect('invoicing:invoices-list')
        else:
            logger.error(f"Erreurs formulaire produit: {form.errors}")
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Erreur dans {field}: {error}")
        return render(request, self.template_name, {'form': form})
    
class ModifyPharmacyProductView(LoginRequiredMixin, View):
    template_name = 'facture_app/add_product.html'

    def get(self, request, *args, **kwargs):
        try:
            product = PharmacyProduct.objects.get(id=kwargs.get('pk'))
            form = PharmacyProductForm(instance=product)
            logger.info(f"ModifyPharmacyProductView GET: Produit ID={product.id}, Utilisateur={request.user.username}")
            return render(request, self.template_name, {
                'form': form,
                'obj': product,
                'product_id': product.id,
            })
        except PharmacyProduct.DoesNotExist:
            logger.error(f"Produit ID={kwargs.get('pk')} non trouvé")
            messages.error(request, _("Produit non trouvé."))
            return redirect('invoicing:product-list')

    def post(self, request, *args, **kwargs):
        try:
            product = PharmacyProduct.objects.get(id=kwargs.get('pk'))
            form = PharmacyProductForm(request.POST, instance=product)
            if form.is_valid():
                form.save()
                logger.info(f"Produit ID={product.id} modifié par {request.user.username}")
                messages.success(request, _("Produit modifié avec succès."))
                return redirect('invoicing:product-list')
            else:
                logger.error(f"Erreurs formulaire produit: {form.errors}")
                messages.error(request, _("Données invalides: %s") % form.errors.as_text())
        except PharmacyProduct.DoesNotExist:
            logger.error(f"Produit ID={kwargs.get('pk')} non trouvé")
            messages.error(request, _("Produit non trouvé."))
            return redirect('invoicing:product-list')

        return render(request, self.template_name, {
            'form': form,
            'obj': product,
            'product_id': product.id,
        })

class DeletePharmacyProductView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            product_id = request.POST.get('id_supprimer')
            product = PharmacyProduct.objects.get(id=product_id)
            product.delete()
            logger.info(f"Produit ID={product_id} supprimé par {request.user.username}")
            messages.success(request, _("Produit supprimé avec succès."))
        except PharmacyProduct.DoesNotExist:
            logger.error(f"Produit ID={product_id} non trouvé")
            messages.error(request, _("Produit non trouvé."))
        except Exception as e:
            logger.error(f"Erreur lors de la suppression du produit ID={product_id}: {str(e)}")
            messages.error(request, _("Une erreur s'est produite lors de la suppression du produit."))
        return redirect('invoicing:product-list')
    
class ProductListView(LoginRequiredMixin, View):
    template_name = 'facture_app/product_list.html'

    def get(self, request, *args, **kwargs):
        products = PharmacyProduct.objects.all().order_by('name')
        context = {'products': products}
        return render(request, self.template_name, context)

class InvoiceVisualizationView(LoginRequiredMixin, View):
    template_name = 'facture_app/invoice.html'

    def get(self, request, *args, **kwargs):
        context = get_invoice(kwargs.get('pk'))
        if not context:
            logger.error(f"Facture ID={kwargs.get('pk')} non trouvée")
            messages.error(request, _("Facture non trouvée."))
            return redirect('invoicing:invoices-list')
        return render(request, self.template_name, context)
    
class ModifyInvoiceView(LoginRequiredMixin, View):
    template_name = 'facture_app/add_invoice.html'

    def get(self, request, *args, **kwargs):
        try:
            invoice = Invoice.objects.get(id=kwargs.get('pk'))
            form = InvoiceForm(instance=invoice)
            articles = Article.objects.filter(invoice=invoice)
            products = PharmacyProduct.objects.all()
            customers = Customer.objects.all()
            logger.info(f"ModifyInvoiceView GET: Facture ID={invoice.id}, Utilisateur={request.user.username}")
            return render(request, self.template_name, {
                'form': form,
                'products': products,
                'customers': customers,
                'articles': articles,
                'obj': invoice,
                'invoice_id': invoice.id,
            })
        except Invoice.DoesNotExist:
            logger.error(f"Facture ID={kwargs.get('pk')} non trouvée")
            messages.error(request, _("Facture non trouvée."))
            return redirect('invoicing:invoices-list')

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        try:
            invoice = Invoice.objects.get(id=kwargs.get('pk'))
            form = InvoiceForm(request.POST, instance=invoice)
            products = request.POST.getlist('product')
            quantities = request.POST.getlist('qty')
            errors = []

            # Vérifier si la requête vise uniquement à modifier le statut "paid"
            if 'paid' in request.POST and not products and not quantities:
                paid_value = request.POST.get('paid') == 'True'
                if invoice.paid != paid_value:
                    invoice.paid = paid_value
                    invoice.save_by = request.user
                    invoice.last_updated_date = timezone.now()
                    invoice.save()
                    logger.info(f"Statut 'paid' de la facture ID={invoice.id} modifié par {request.user.username} à {paid_value}")
                    messages.success(request, _("Statut de paiement mis à jour avec succès."))
                return redirect('invoicing:invoices-list')

            # Sinon, traiter la modification complète de la facture
            if form.is_valid():
                for i in range(len(products)):
                    try:
                        product = PharmacyProduct.objects.get(id=products[i])
                        qty = float(quantities[i])
                        if qty > product.stock_quantity:
                            errors.append(_("Quantité demandée (%s) dépasse le stock (%s) pour %s.") % (qty, product.stock_quantity, product.name))
                    except PharmacyProduct.DoesNotExist:
                        errors.append(_("Produit ID %s non trouvé.") % products[i])

                if errors:
                    for error in errors:
                        messages.error(request, error)
                    return render(request, self.template_name, {
                        'form': form,
                        'products': PharmacyProduct.objects.all(),
                        'customers': Customer.objects.all(),
                        'articles': Article.objects.filter(invoice=invoice),
                        'obj': invoice,
                        'invoice_id': invoice.id,
                    })

                if len(products) == len(quantities):
                    invoice = form.save(commit=False)
                    invoice.save_by = request.user
                    invoice.last_updated_date = timezone.now()
                    invoice.save()

                    Article.objects.filter(invoice=invoice).delete()

                    for i in range(len(products)):
                        article = Article(
                            invoice=invoice,
                            product_id=products[i],
                            quantity=float(quantities[i])
                        )
                        article.full_clean()
                        article.save()

                    logger.info(f"Facture ID={invoice.id} modifiée par {request.user.username}")
                    messages.success(request, _("Facture modifiée avec succès."))
                    return redirect('invoicing:invoices-list')
                messages.error(request, _("Données produit incohérentes."))
            else:
                logger.error(f"Erreurs formulaire facture: {form.errors}")
                messages.error(request, _("Données invalides: %s") % form.errors.as_text())
        except Invoice.DoesNotExist:
            logger.error(f"Facture ID={kwargs.get('pk')} non trouvée")
            messages.error(request, _("Facture non trouvée."))
            return redirect('invoicing:invoices-list')

        return render(request, self.template_name, {
            'form': form,
            'products': PharmacyProduct.objects.all(),
            'customers': Customer.objects.all(),
            'articles': Article.objects.filter(invoice=invoice),
            'obj': invoice,
            'invoice_id': invoice.id,
        })
    
class DeleteInvoiceView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            invoice = Invoice.objects.get(pk=request.POST.get('id_supprimer'))
            invoice.delete()
            logger.info(f"Facture ID={request.POST.get('id_supprimer')} supprimée par {request.user.username}")
            messages.success(request, _("Facture supprimée avec succès."))
        except Invoice.DoesNotExist:
            logger.error(f"Facture ID={request.POST.get('id_supprimer')} non trouvée")
            messages.error(request, _("Facture non trouvée."))
        return redirect('invoicing:invoices-list')

@shared_task
def generate_invoice_pdf_task(pk):
    logger.info(f"Début génération PDF pour facture ID={pk}")
    try:
        context = get_invoice(pk)
        if not context:
            logger.error(f"Facture ID={pk} non trouvée")
            return None
        context['date'] = datetime.datetime.now()
        context['is_pdf'] = True
        if not context.get('obj') or not context.get('obj').customer:
            logger.error(f"Données invalides pour facture ID={pk}")
            return None

        template = 'facture_app/invoice_template.tex'
        latex_content = render_to_string(template, context)
        logger.info(f"LaTeX généré pour facture ID={pk}: {latex_content[:500]}...")

        temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp')
        os.makedirs(temp_dir, exist_ok=True)
        timestamp = int(time.time())
        tex_file_path = os.path.join(temp_dir, f'invoice_{pk}_{timestamp}.tex')
        pdf_file_path = os.path.join(temp_dir, f'invoice_{pk}_{timestamp}.pdf')

        for file_name in os.listdir(temp_dir):
            if file_name.startswith(f'invoice_{pk}_'):
                file_path = os.path.join(temp_dir, file_name)
                try:
                    os.remove(file_path)
                    logger.info(f"Fichier temporaire supprimé: {file_path}")
                except OSError as e:
                    logger.error(f"Erreur suppression fichier {file_path}: {e}")

        with open(tex_file_path, 'w', encoding='utf-8') as f:
            f.write(latex_content)
        logger.info(f"Fichier LaTeX écrit à: {tex_file_path}")

        result = subprocess.run(
            ['latexmk', '-pdf', '-interaction=nonstopmode', '-f', tex_file_path],
            cwd=temp_dir,
            capture_output=True,
            text=True
        )
        logger.info(f"Commande latexmk pour facture ID={pk}: {result.stdout}")
        if result.returncode != 0:
            logger.error(f"Erreur latexmk pour facture ID={pk}: {result.stderr}")
            raise Exception(f"Erreur latexmk: {result.stderr}")

        if not os.path.exists(pdf_file_path):
            logger.error(f"PDF non généré pour facture ID={pk}")
            raise Exception("Échec génération PDF")

        with open(pdf_file_path, 'rb') as f:
            pdf_content = f.read()
        logger.info(f"PDF généré pour facture ID={pk}")

        for file_name in os.listdir(temp_dir):
            if file_name.startswith(f'invoice_{pk}_{timestamp}'):
                file_path = os.path.join(temp_dir, file_name)
                try:
                    os.remove(file_path)
                    logger.info(f"Fichier temporaire nettoyé: {file_path}")
                except OSError as e:
                    logger.error(f"Erreur nettoyage fichier {file_path}: {e}")

        return pdf_content
    except Exception as e:
        logger.error(f"Erreur generate_invoice_pdf_task pour facture ID={pk}: {str(e)}")
        raise

def get_invoice_pdf(request, *args, **kwargs):
    pk = kwargs.get('pk')
    logger.info(f"Envoi tâche generate_invoice_pdf_task pour facture ID={pk}, Utilisateur={request.user.username}")
    result = generate_invoice_pdf_task.delay(pk)
    logger.info(f"Tâche envoyée ID: {result.id}")
    try:
        pdf = result.get(timeout=300)
        logger.info(f"Tâche terminée pour facture ID={pk}")
        if not pdf:
            logger.error(f"Facture ID={pk} non trouvée ou génération PDF échouée")
            raise Http404(_("Facture non trouvée ou génération PDF échouée"))
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="facture_{pk}.pdf"'
        return response
    except Exception as e:
        logger.error(f"Erreur génération PDF pour facture ID={pk}: {str(e)}")
        return HttpResponse(f"Erreur génération PDF: {str(e)}", status=500)

def custom_404(request, exception):
    return render(request, 'facture_app/404.html', status=404)

def custom_500(request):
    return render(request, 'facture_app/500.html', status=500)