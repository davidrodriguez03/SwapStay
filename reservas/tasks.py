import logging
import requests
from datetime import datetime, timedelta

from celery import shared_task
from django.conf import settings
from django.db.models import Sum, Avg, Count

logger = logging.getLogger(__name__)


# ── Tarea 1: Confirmación de reserva ─────────────────────────────────────────

@shared_task(
    name='reservas.tasks.enviar_confirmacion_reserva',
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def enviar_confirmacion_reserva(self, reserva_id):
    """
    Dispara confirmación vía microservicio de notificaciones.
    Si el microservicio no está disponible, usa fallback a consola.
    """
    from .models import Reserva

    try:
        reserva = Reserva.objects.select_related(
            'estudiante__user', 'alojamiento'
        ).get(id=reserva_id)
    except Reserva.DoesNotExist:
        logger.error(f'[Celery] Reserva {reserva_id} no encontrada')
        return {'status': 'error', 'message': 'Reserva no existe'}

    payload = {
        'destinatario': reserva.estudiante.user.email,
        'tipo': 'confirmacion_reserva',
        'datos': {
            'reserva_id': reserva.id,
            'estudiante_nombre': reserva.estudiante.user.get_full_name(),
            'alojamiento_nombre': reserva.alojamiento.nombre,
            'ciudad': reserva.alojamiento.ciudad,
            'fecha_inicio': str(reserva.fecha_inicio),
            'fecha_fin': str(reserva.fecha_fin),
            'monto_total': float(reserva.monto_total),
        },
        'idioma': 'es',
    }

    try:
        url = f"{settings.NOTIFICACIONES_SERVICE_URL}/api/v2/notificaciones/email"
        response = requests.post(url, json=payload, timeout=10)

        if response.status_code == 200:
            logger.info(f'[Celery] Email enviado para reserva {reserva_id}')
            return {'status': 'success', 'reserva_id': reserva_id}

        logger.warning(
            f'[Celery] Microservicio notificaciones respondió {response.status_code}'
            f' para reserva {reserva_id} — usando fallback consola'
        )
        _fallback_consola(reserva)
        return {'status': 'fallback', 'reserva_id': reserva_id}

    except requests.exceptions.RequestException as exc:
        logger.warning(
            f'[Celery] Microservicio notificaciones no disponible'
            f' para reserva {reserva_id}: {exc} — usando fallback consola'
        )
        _fallback_consola(reserva)
        return {'status': 'fallback', 'reserva_id': reserva_id}

    except Exception as exc:
        logger.exception(f'[Celery] Error inesperado en reserva {reserva_id}: {exc}')
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            return {'status': 'error', 'message': str(exc)}


def _fallback_consola(reserva):
    print('\n' + '=' * 50)
    print('CONFIRMACIÓN DE RESERVA (fallback consola)')
    print('=' * 50)
    print(f'  Reserva:      #{reserva.id}')
    print(f'  Estudiante:   {reserva.estudiante.user.get_full_name()}')
    print(f'  Email:        {reserva.estudiante.user.email}')
    print(f'  Alojamiento:  {reserva.alojamiento.nombre} — {reserva.alojamiento.ciudad}')
    print(f'  Fechas:       {reserva.fecha_inicio} → {reserva.fecha_fin}')
    print(f'  Monto total:  ${reserva.monto_total:,.0f} COP')
    print('=' * 50 + '\n')


# ── Tarea 2: Actualizar tasas de cambio ───────────────────────────────────────

@shared_task(name='reservas.tasks.actualizar_tasas_cambio')
def actualizar_tasas_cambio():
    """
    Tarea programada (cada hora): Actualiza tasas COP/USD desde el
    microservicio de moneda. Si no está disponible, intenta la API
    pública directamente como fallback.
    """
    from django.core.cache import cache

    tasa_actualizada = None

    # Intento 1: microservicio de moneda
    try:
        url = f"{settings.MONEDA_SERVICE_URL}/api/v2/moneda/actualizar"
        response = requests.post(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            tasa_actualizada = data.get('tasa_usd_cop')
            logger.info(f'[Celery] Tasas actualizadas vía microservicio: {data}')
    except requests.exceptions.RequestException:
        logger.warning('[Celery] Microservicio moneda no disponible — intentando API pública')

    # Intento 2: API pública directa (fallback)
    if tasa_actualizada is None:
        try:
            response = requests.get(
                'https://open.er-api.com/v6/latest/USD',
                timeout=10,
            )
            if response.status_code == 200:
                data = response.json()
                tasa_actualizada = data.get('rates', {}).get('COP')
                logger.info(f'[Celery] Tasa COP/USD actualizada vía API pública: {tasa_actualizada}')
        except requests.exceptions.RequestException as exc:
            logger.error(f'[Celery] No se pudo actualizar tasa de cambio: {exc}')
            return {'status': 'error', 'message': str(exc)}

    if tasa_actualizada:
        cache.set('tasa_usd_cop', tasa_actualizada, timeout=3600)
        cache.set('tasa_actualizada_at', datetime.now().isoformat(), timeout=3600)
        return {'status': 'success', 'tasa_usd_cop': tasa_actualizada}

    return {'status': 'error', 'message': 'No se pudo obtener tasa'}


# ── Tarea 3: Reporte mensual de ocupación ─────────────────────────────────────

@shared_task(name='reservas.tasks.generar_reporte_mensual')
def generar_reporte_mensual():
    """
    Tarea programada (diaria a las 8am): Genera estadísticas de ocupación
    del mes actual y las guarda en cache para el dashboard admin.
    """
    from .models import Reserva, Alojamiento

    hoy = datetime.now()
    inicio_mes = hoy.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    inicio_mes_siguiente = (inicio_mes + timedelta(days=32)).replace(day=1)

    reservas_mes = Reserva.objects.filter(
        fecha_creacion__gte=inicio_mes,
        fecha_creacion__lt=inicio_mes_siguiente,
    )

    total_alojamientos = Alojamiento.objects.count() or 1
    confirmadas = reservas_mes.filter(estado='CONFIRMADA')

    stats = {
        'mes': hoy.strftime('%Y-%m'),
        'total_reservas': reservas_mes.count(),
        'reservas_confirmadas': confirmadas.count(),
        'reservas_canceladas': reservas_mes.filter(estado='CANCELADA').count(),
        'ingresos_cop': float(
            confirmadas.aggregate(total=Sum('monto_total'))['total'] or 0
        ),
        'promedio_monto_cop': float(
            confirmadas.aggregate(avg=Avg('monto_total'))['avg'] or 0
        ),
        'tasa_ocupacion_pct': round(
            (confirmadas.count() / total_alojamientos) * 100, 2
        ),
        'generado_at': hoy.isoformat(),
    }

    from django.core.cache import cache
    cache.set('reporte_mensual', stats, timeout=86400)

    logger.info(f'[Celery] Reporte mensual generado: {stats}')
    return stats


# ── Tarea 4: Recordatorio de pago ─────────────────────────────────────────────

@shared_task(
    name='reservas.tasks.enviar_recordatorio_pago',
    bind=True,
    max_retries=2,
    default_retry_delay=120,
)
def enviar_recordatorio_pago(self, reserva_id, dias_antes=7):
    """
    Tarea disparada manualmente o por beat: avisa al estudiante
    que su reserva comienza en `dias_antes` días.
    """
    from .models import Reserva

    try:
        reserva = Reserva.objects.select_related(
            'estudiante__user', 'alojamiento'
        ).get(id=reserva_id)
    except Reserva.DoesNotExist:
        logger.error(f'[Celery] Reserva {reserva_id} no encontrada para recordatorio')
        return {'status': 'error', 'message': 'Reserva no existe'}

    if reserva.estado != 'CONFIRMADA':
        return {'status': 'skipped', 'reason': f'Estado: {reserva.estado}'}

    payload = {
        'destinatario': reserva.estudiante.user.email,
        'tipo': 'recordatorio_inicio',
        'datos': {
            'reserva_id': reserva.id,
            'estudiante_nombre': reserva.estudiante.user.get_full_name(),
            'alojamiento_nombre': reserva.alojamiento.nombre,
            'ciudad': reserva.alojamiento.ciudad,
            'fecha_inicio': str(reserva.fecha_inicio),
            'dias_restantes': dias_antes,
        },
        'idioma': 'es',
    }

    try:
        url = f"{settings.NOTIFICACIONES_SERVICE_URL}/api/v2/notificaciones/email"
        response = requests.post(url, json=payload, timeout=10)

        if response.status_code == 200:
            logger.info(
                f'[Celery] Recordatorio enviado para reserva {reserva_id}'
                f' ({dias_antes} días antes)'
            )
            return {'status': 'success', 'reserva_id': reserva_id}

        # Fallback consola si el microservicio falla
        logger.warning(f'[Celery] Fallback consola para recordatorio reserva {reserva_id}')
        print(f'\n[RECORDATORIO] Reserva #{reserva_id} comienza en {dias_antes} días')
        print(f'  → {reserva.estudiante.user.email}: {reserva.alojamiento.nombre}')
        return {'status': 'fallback', 'reserva_id': reserva_id}

    except Exception as exc:
        logger.exception(f'[Celery] Error en recordatorio reserva {reserva_id}: {exc}')
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            return {'status': 'error', 'message': str(exc)}
