import os
from celery import Celery
from celery.schedules import crontab
from datetime import timedelta

# Set the default Django settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.settings")

app = Celery("app")

# Load task modules from all registered Django apps
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks in Django apps
app.autodiscover_tasks()

# Celery Beat Schedule
app.conf.beat_schedule = {
    'remove-expired-premium-users': {
        'task': 'healthapp.tasks.remove_expired_premium_users',
        'schedule': timedelta(hours=1),  
    },
    'check_and_generate_coupons': {
        'task': 'healthapp.tasks.check_and_generate_coupons',
        'schedule': timedelta(seconds=10),  
    },
}
