import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'facture.settings')
import django
django.setup()
from django.template.loader import get_template
from facture_app.utils import get_invoice
import datetime

context = get_invoice(1)
if context:
    context['date'] = datetime.datetime.today()
    template = get_template('facture_app/invoice_pdf.html')
    html = template.render(context)
    with open('rendered_invoice.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("HTML généré dans rendered_invoice.html")
else:
    print("Erreur : Impossible de récupérer la facture ID=1")