import os
from celery import Celery
from django.conf import settings


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'commerce.settings')
app = Celery('commerce')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()


# Configure celery beat schedule
app.conf.beat_schedule = {
    'set_inactive': {
        'task': 'auctions.tasks.set_inactive',
        'schedule': 60.0,
    },
    'check_user_fees': {
        'task': 'auctions.tasks.check_user_fees',
        'schedule': 43200.0,
    },
    'check_if_bids_funded': {
        'task': 'auctions.tasks.check_if_bids_funded',
        'schedule': 900.0,
    },
}


# TO RUN:

# start redis server
# redis-server

# Run celery worker
# celery -A commerce worker -l info

# Run celery beat
# celery -A commerce beat -l info




