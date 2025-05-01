from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils.translation import activate
from .models import Customer, Invoice, Article, PharmacyProduct
from django.core.exceptions import ValidationError

class CustomerModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.customer = Customer.objects.create(
            name="John Doe",
            email="john@example.com",
            phone="+1234567890",
            address="123 Main St",
            sex="M",
            city="Douala",
            save_by=self.user
        )

    def test_customer_str(self):
        self.assertEqual(str(self.customer), "John Doe")

    def test_email_lowercase(self):
        customer = Customer.objects.create(
            name="Jane Doe",
            email="JANE@example.com",
            phone="+1234567891",
            address="124 Main St",
            sex="F",
            city="Yaounde",
            save_by=self.user
        )
        self.assertEqual(customer.email, "jane@example.com")

    def test_invalid_phone(self):
        with self.assertRaises(ValidationError):
            Customer.objects.create(
                name="Utilisateur invalide",
                email="invalid@example.com",
                phone="123",  # Numéro de téléphone invalide
                address="125 Main St",
                sex="M",
                city="Douala",
                save_by=self.user
            )

class InvoiceModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.customer = Customer.objects.create(
            name="John Doe",
            email="john@example.com",
            phone="+1234567890",
            address="123 Main St",
            sex="M",
            city="Douala",
            save_by=self.user
        )
        self.product = PharmacyProduct.objects.create(
            name="Paracetamol",
            price=5.00,
            stock_quantity=100,
            created_by=self.user
        )
        self.invoice = Invoice.objects.create(
            customer=self.customer,
            save_by=self.user,
            invoice_type="F",
            comments="Facture de test"
        )
        self.article = Article.objects.create(
            invoice=self.invoice,
            product=self.product,
            quantity=2.5
        )

    def test_invoice_str(self):
        self.assertIn(self.customer.name, str(self.invoice))

    def test_get_total(self):
        self.assertEqual(self.invoice.total, 12.50)

    def test_insufficient_stock(self):
        with self.assertRaises(ValueError):
            Article.objects.create(
                invoice=self.invoice,
                product=self.product,
                quantity=1000  # Plus que le stock
            )

class PharmacyProductModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.product = PharmacyProduct.objects.create(
            name="Paracetamol",
            price=5.00,
            stock_quantity=100,
            created_by=self.user
        )

    def test_product_str(self):
        self.assertEqual(str(self.product), "Paracetamol")

class HomeViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(username='admin', password='12345', email='admin@example.com')
        self.client.login(username='admin', password='12345')

    def test_home_view_get(self):
        activate('fr')  # Test en français
        response = self.client.get(reverse('invoicing:invoices-list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'home.html')

    def test_home_view_unauthenticated(self):
        self.client.logout()
        response = self.client.get(reverse('invoicing:invoices-list'))
        self.assertEqual(response.status_code, 302)

class AddCustomerViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(username='admin', password='12345', email='admin@example.com')
        self.client.login(username='admin', password='12345')

    def test_add_customer_post_valid(self):
        response = self.client.post(reverse('invoicing:create-customer'), {
            'name': 'Client Test',
            'email': 'test@example.com',
            'phone': '+1234567890',
            'address': '123 Test St',
            'sex': 'M',
            'city': 'Douala'
        })
        self.assertRedirects(response, reverse('invoicing:invoices-list'))
        self.assertTrue(Customer.objects.filter(email='test@example.com').exists())

    def test_add_customer_post_invalid(self):
        response = self.client.post(reverse('invoicing:create-customer'), {
            'name': 'Client Test',
            'email': 'invalid',  # Email invalide
            'phone': '+1234567890',
            'address': '123 Test St',
            'sex': 'M',
            'city': 'Douala'
        })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'add_customer.html')