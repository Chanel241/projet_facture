import time
from celery import shared_task
from django.core.files.base import ContentFile
from django.template.loader import render_to_string
from django.conf import settings
import os
import weasyprint
from django.utils import timezone
from .models import Invoice
from .utils import get_invoice
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def generate_invoice_pdf_task(self, pk):
    logger.info(f"Début génération PDF pour facture ID={pk}")
    try:
        context = get_invoice(pk)
        if not context:
            logger.error(f"Facture ID={pk} non trouvée")
            return None
        context['date'] = timezone.now().strftime('%d %B %Y %H:%M')
        context['is_pdf'] = True
        if not context.get('obj') or not context.get('obj').customer:
            logger.error(f"Données invalides pour facture ID={pk}")
            return None

        html = render_to_string('facture_app/invoice_base.html', context)

        temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp')
        os.makedirs(temp_dir, exist_ok=True)
        timestamp = int(time.time())
        pdf_file_path = os.path.join(temp_dir, f'invoice_{pk}_{timestamp}.pdf')

        weasyprint.HTML(string=html, base_url=settings.STATIC_ROOT).write_pdf(pdf_file_path)
        logger.info(f"PDF généré pour facture ID={pk} à {pdf_file_path}")

        with open(pdf_file_path, 'rb') as f:
            pdf_content = f.read()

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
        raise self.retry(exc=e, countdown=60)