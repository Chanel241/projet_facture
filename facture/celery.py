import os
from celery import Celery
from django.conf import settings

# Définir le module de paramètres Django pour le programme 'celery'
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'facture.settings')

# Initialiser Celery
app = Celery('facture')

# Charger les modules de tâches depuis toutes les applications Django enregistrées
app.config_from_object('django.conf:settings', namespace='CELERY')

# Découvrir automatiquement les tâches dans toutes les applications installées
app.autodiscover_tasks()

# Tâche de débogage pour le développement (exécutée uniquement si DEBUG est True)
@app.task(bind=True, ignore_result=True)
def debug_task(self):
    if settings.DEBUG:
        print(f'Request: {self.request!r}')