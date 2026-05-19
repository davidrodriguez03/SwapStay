import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('swapstay')

app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()

app.conf.beat_schedule = {
    'actualizar-tasas-cambio-cada-hora': {
        'task': 'reservas.tasks.actualizar_tasas_cambio',
        'schedule': crontab(minute=0),
    },
    'generar-reporte-diario': {
        'task': 'reservas.tasks.generar_reporte_mensual',
        'schedule': crontab(hour=8, minute=0),
    },
}
