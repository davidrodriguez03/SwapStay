import logging
import os
from abc import ABC, abstractmethod

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class CurrencyAdapter(ABC):
    @abstractmethod
    def cotizar(self, monto: float, moneda_origen: str = 'COP', moneda_destino: str = 'USD') -> dict:
        """Convierte `monto` de `moneda_origen` a `moneda_destino`.
        Retorna dict con claves: monto_original, moneda_origen, moneda_destino, tasa, resultado.
        """


class MicroserviceMonedaAdapter(CurrencyAdapter):
    """Delega la conversión al microservicio Flask de moneda (μS 5, puerto 5005)."""

    def cotizar(self, monto: float, moneda_origen: str = 'COP', moneda_destino: str = 'USD') -> dict:
        url = f"{settings.MONEDA_SERVICE_URL}/api/v2/moneda/cotizar"
        resp = requests.get(
            url,
            params={'monto': monto, 'moneda_origen': moneda_origen, 'moneda_destino': moneda_destino},
            timeout=5,
        )
        resp.raise_for_status()
        return resp.json()


class OpenERAPIAdapter(CurrencyAdapter):
    """Consulta open.er-api.com directamente (sin API key, rate-limited a 1500 req/mes)."""

    _BASE = 'https://open.er-api.com/v6/latest'

    def cotizar(self, monto: float, moneda_origen: str = 'COP', moneda_destino: str = 'USD') -> dict:
        resp = requests.get(f'{self._BASE}/{moneda_origen}', timeout=8)
        resp.raise_for_status()
        data = resp.json()
        tasa = data['rates'][moneda_destino]
        return {
            'monto_original': monto,
            'moneda_origen': moneda_origen,
            'moneda_destino': moneda_destino,
            'tasa': tasa,
            'resultado': round(monto * tasa, 2),
            'fuente': 'open.er-api.com',
        }


class MockAdapter(CurrencyAdapter):
    """Tasas estáticas para pruebas unitarias o cuando los servicios externos no están disponibles."""

    _RATES_TO_COP = {'COP': 1.0, 'USD': 4200.0, 'EUR': 4550.0, 'GBP': 5300.0}

    def cotizar(self, monto: float, moneda_origen: str = 'COP', moneda_destino: str = 'USD') -> dict:
        cop_origen = self._RATES_TO_COP.get(moneda_origen, 1.0)
        cop_destino = self._RATES_TO_COP.get(moneda_destino, 1.0)
        tasa = cop_destino / cop_origen if cop_origen else 1.0
        # Invert: rates are COP per 1 foreign unit, so 1 COP → USD = 1/4200
        tasa_directa = (1.0 / cop_origen) * cop_destino if moneda_origen != 'COP' else 1.0 / cop_destino
        if moneda_origen == 'COP':
            tasa_directa = 1.0 / cop_destino
        elif moneda_destino == 'COP':
            tasa_directa = cop_origen
        else:
            tasa_directa = cop_origen / cop_destino
        return {
            'monto_original': monto,
            'moneda_origen': moneda_origen,
            'moneda_destino': moneda_destino,
            'tasa': round(tasa_directa, 8),
            'resultado': round(monto * tasa_directa, 2),
            'fuente': 'mock',
        }


def get_currency_adapter() -> CurrencyAdapter:
    """Devuelve el adaptador más adecuado según el entorno.

    - ENV_TYPE=test → MockAdapter (sin red)
    - Default → MicroserviceMonedaAdapter (con fallback externo en el llamador)
    """
    if os.environ.get('ENV_TYPE') == 'test':
        return MockAdapter()
    return MicroserviceMonedaAdapter()
