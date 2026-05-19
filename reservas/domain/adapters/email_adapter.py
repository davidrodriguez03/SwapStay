import logging
import os
from abc import ABC, abstractmethod

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class EmailAdapter(ABC):
    @abstractmethod
    def enviar(self, destinatario: str, tipo: str, datos: dict) -> dict:
        """Envía una notificación por email.

        Args:
            destinatario: dirección de correo del receptor.
            tipo: clave de plantilla (ej. 'confirmacion_reserva').
            datos: variables de contexto para rellenar la plantilla.
        Retorna dict con al menos {'enviado': bool}.
        """


class MicroserviceNotificacionesAdapter(EmailAdapter):
    """Delega el envío al microservicio Flask de notificaciones (μS 2, puerto 5002)."""

    def enviar(self, destinatario: str, tipo: str, datos: dict) -> dict:
        url = f"{settings.NOTIFICACIONES_SERVICE_URL}/api/v2/notificaciones/email"
        payload = {'destinatario': destinatario, 'tipo': tipo, 'datos': datos}
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        return resp.json()


class MockEmailAdapter(EmailAdapter):
    """Simula el envío escribiendo en el log (sin red, para pruebas y dev sin Docker)."""

    def enviar(self, destinatario: str, tipo: str, datos: dict) -> dict:
        logger.info('[MockEmailAdapter] Email simulado → %s | tipo=%s | datos=%s', destinatario, tipo, datos)
        return {
            'enviado': True,
            'destinatario': destinatario,
            'tipo': tipo,
            'adapter': 'mock',
        }


def get_email_adapter() -> EmailAdapter:
    """Devuelve el adaptador de email según el entorno.

    - ENV_TYPE=test → MockEmailAdapter
    - Default → MicroserviceNotificacionesAdapter
    """
    if os.environ.get('ENV_TYPE') == 'test':
        return MockEmailAdapter()
    return MicroserviceNotificacionesAdapter()
