import os
from celery import Celery
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'your_project.settings')
app = Celery('your_project')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Configure celery beat schedule
app.conf.beat_schedule = {
    'check-listing-expiration': {
        'task': 'auctions.tasks.check_listing_expiration',
        'schedule': 60.0,
    },
}