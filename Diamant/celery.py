import os
from django.conf import settings
from dotenv import load_dotenv

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Diamant.settings_prod')


app = Celery('Diamant')

load_dotenv(os.path.join(settings.BASE_DIR, ".env"))
app.config_from_object(settings, namespace='CELERY')


app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
