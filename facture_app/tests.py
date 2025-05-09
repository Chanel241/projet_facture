from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils.translation import activate
from .models import Customer, Invoice, Article, PharmacyProduct
from django.core.exceptions import ValidationError

