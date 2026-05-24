import logging
import os

import requests
from django.db import transaction
from django.core.exceptions import ValidationError

from domain.builders import ReservaBuilder
from infra.factories import NotificadorFactory

logger = logging.getLogger(__name__)


class ReservaService:
    def __init__(self):
        self.notificador = NotificadorFactory.crear()

    @transaction.atomic
    def crear_reserva(self, estudiante, alojamiento, fecha_inicio, fecha_fin):
        # 1. Construir con Builder (valida estudiante, alojamiento y fechas)
        reserva = (ReservaBuilder()
                   .para_estudiante(estudiante)
                   .en_alojamiento(alojamiento)
                   .en_fechas(fecha_inicio, fecha_fin)
                   .build())

        # 2. Persistir
        reserva.save()

        # 3. Marcar alojamiento como no disponible
        alojamiento.disponible = False
        alojamiento.save()

        # 4. Confirmar
        reserva.estado = 'CONFIRMADA'
        reserva.save()

        # 5. Notificación sincrónica local (consola en dev, email en prod)
        self.notificador.enviar_confirmacion(reserva)

        # 6. Notificación asíncrona vía Celery (no bloquea la respuesta HTTP)
        self._disparar_confirmacion_asincrona(reserva.id)

        return reserva

    @staticmethod
    def _disparar_confirmacion_asincrona(reserva_id):
        try:
            from .tasks import enviar_confirmacion_reserva
            enviar_confirmacion_reserva.delay(reserva_id)
            logger.info(f'[Service] Tarea Celery encolada para reserva {reserva_id}')
        except Exception as exc:
            # Si Celery/Redis no están disponibles (dev sin Docker), no falla
            logger.warning(
                f'[Service] No se pudo encolar tarea Celery para reserva {reserva_id}: {exc}'
            )


class AuroraEstudioService:
    """Consume la API de Aurora Estudio con cache en memoria para servicios."""

    BASE_URL = 'http://aurora-studio.ddns.net'
    TIMEOUT = 5

    _cache_servicios: list | None = None
    _cache_fecha: str | None = None

    @classmethod
    def obtener_servicios(cls) -> list:
        if cls._cache_servicios is not None:
            return cls._cache_servicios
        try:
            resp = requests.get(f'{cls.BASE_URL}/api/v1/servicios/', timeout=cls.TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            cls._cache_servicios = data if isinstance(data, list) else []
            from datetime import datetime
            cls._cache_fecha = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        except Exception as exc:
            logger.warning('[AuroraEstudioService] obtener_servicios falló: %s', exc)
            cls._cache_servicios = []
            from datetime import datetime
            cls._cache_fecha = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        return cls._cache_servicios

    @classmethod
    def obtener_disponibilidad(cls, fecha: str) -> dict:
        try:
            resp = requests.get(
                f'{cls.BASE_URL}/api/v1/disponibilidad/',
                params={'fecha': fecha, 'duracion_horas': '1.00'},
                timeout=cls.TIMEOUT,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            logger.warning('[AuroraEstudioService] obtener_disponibilidad falló: %s', exc)
            return {}

    @classmethod
    def info_cache(cls) -> dict:
        return {
            'total_servicios': len(cls._cache_servicios) if cls._cache_servicios is not None else 0,
            'tiene_datos': cls._cache_servicios is not None,
            'fecha_obtencion': cls._cache_fecha,
        }

    @classmethod
    def invalidar_cache(cls) -> None:
        cls._cache_servicios = None
        cls._cache_fecha = None


class EquipoAliadoService:
    """Consume la API del equipo aliado con fallback graceful.

    Si el servicio aliado no está disponible, los métodos retornan listas vacías
    sin propagar excepciones, de modo que el flujo principal nunca se interrumpe.
    """

    BASE_URL = os.environ.get('EQUIPO_ALIADO_URL', 'http://equipo-aliado:8000')
    TIMEOUT = 5

    @classmethod
    def obtener_alojamientos(cls) -> list:
        """Retorna los alojamientos publicados por el equipo aliado."""
        try:
            resp = requests.get(
                f'{cls.BASE_URL}/api/alojamientos/',
                timeout=cls.TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
            return data if isinstance(data, list) else data.get('results', [])
        except Exception as exc:
            logger.warning('[EquipoAliadoService] obtener_alojamientos falló: %s', exc)
            return []

    @classmethod
    def obtener_estudiantes(cls) -> list:
        """Retorna el listado de estudiantes registrados en el sistema aliado."""
        try:
            resp = requests.get(
                f'{cls.BASE_URL}/api/estudiantes/',
                timeout=cls.TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
            return data if isinstance(data, list) else data.get('results', [])
        except Exception as exc:
            logger.warning('[EquipoAliadoService] obtener_estudiantes falló: %s', exc)
            return []

    @classmethod
    def health_check(cls) -> dict:
        """Verifica si el servicio aliado está activo."""
        try:
            resp = requests.get(f'{cls.BASE_URL}/health', timeout=3)
            return {'disponible': resp.ok, 'status_code': resp.status_code}
        except Exception as exc:
            logger.warning('[EquipoAliadoService] health_check falló: %s', exc)
            return {'disponible': False, 'error': str(exc)}
