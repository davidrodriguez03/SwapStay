import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime

import requests
from flask import Flask, jsonify, request

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CACHE_TTL_SEGUNDOS = 3600  # 1 hora

_cache = {'tasas': None, 'actualizado_at': None}


# ── Adapter Pattern ───────────────────────────────────────────────────────────

class MonedaAdapter(ABC):
    @abstractmethod
    def obtener_tasas(self) -> dict:
        """Retorna un dict moneda → tasa relativa a USD."""
        pass


class ExchangeRateAPIAdapter(MonedaAdapter):
    BASE_URL = 'https://open.er-api.com/v6/latest/USD'

    def obtener_tasas(self) -> dict:
        response = requests.get(self.BASE_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data.get('result') != 'success':
            raise ValueError(f'API retornó resultado inesperado: {data.get("result")}')
        logger.info('[ExchangeRateAPI] Tasas obtenidas exitosamente')
        return data['rates']


class FallbackAdapter(MonedaAdapter):
    """Tasas estáticas aproximadas para cuando la API no está disponible."""
    TASAS = {
        'COP': 4100.0,
        'EUR': 0.92,
        'GBP': 0.79,
        'MXN': 17.15,
        'BRL': 5.05,
        'ARS': 870.0,
        'PEN': 3.72,
        'CLP': 940.0,
    }

    def obtener_tasas(self) -> dict:
        logger.warning('[Moneda] Usando tasas estáticas de fallback')
        return self.TASAS


def _refrescar_cache() -> dict:
    """Intenta actualizar la caché desde la API; usa fallback si falla."""
    try:
        tasas = ExchangeRateAPIAdapter().obtener_tasas()
    except Exception as exc:
        logger.error(f'[Moneda] Error al obtener tasas desde API: {exc} — usando fallback')
        tasas = FallbackAdapter().obtener_tasas()

    _cache['tasas'] = tasas
    _cache['actualizado_at'] = time.time()
    return tasas


def get_tasas() -> dict:
    ahora = time.time()
    if (
        _cache['tasas'] is not None
        and _cache['actualizado_at'] is not None
        and (ahora - _cache['actualizado_at']) < CACHE_TTL_SEGUNDOS
    ):
        return _cache['tasas']
    return _refrescar_cache()


def error_response(status_code: int, code: str, message: str, details=None):
    payload = {'error': {'code': code, 'message': message}}
    if details:
        payload['error']['details'] = details
    return jsonify(payload), status_code


def _ts_iso():
    if _cache['actualizado_at']:
        return datetime.fromtimestamp(_cache['actualizado_at']).isoformat()
    return None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get('/health')
def health():
    edad = round(time.time() - _cache['actualizado_at']) if _cache['actualizado_at'] else None
    return jsonify({
        'status': 'ok',
        'service': 'flask-moneda',
        'cache_edad_segundos': edad,
        'cache_ttl_segundos': CACHE_TTL_SEGUNDOS,
    }), 200


@app.get('/api/v2/moneda/tasas')
def obtener_tasas_endpoint():
    tasas = get_tasas()
    monedas_latam = {
        k: tasas[k]
        for k in ('COP', 'EUR', 'GBP', 'MXN', 'BRL', 'ARS', 'PEN', 'CLP')
        if k in tasas
    }
    return jsonify({
        'base': 'USD',
        'tasas': monedas_latam,
        'actualizado_at': _ts_iso(),
    }), 200


@app.get('/api/v2/moneda/cotizar')
def cotizar():
    try:
        monto = float(request.args.get('monto', 0))
    except (ValueError, TypeError):
        return error_response(400, 'INVALID_MONTO', 'El parámetro monto debe ser numérico')

    if monto <= 0:
        return error_response(400, 'INVALID_MONTO', 'El monto debe ser mayor a 0')

    moneda_origen = request.args.get('moneda_origen', 'COP').upper().strip()
    moneda_destino = request.args.get('moneda_destino', 'USD').upper().strip()

    tasas = get_tasas()

    for moneda in (moneda_origen, moneda_destino):
        if moneda != 'USD' and moneda not in tasas:
            return error_response(
                400, 'MONEDA_NO_SOPORTADA',
                f'Moneda no soportada: {moneda}',
                {'monedas_disponibles': list(tasas.keys())},
            )

    # Conversión triangular a través de USD como base
    tasa_origen = tasas[moneda_origen] if moneda_origen != 'USD' else 1.0
    tasa_destino = tasas[moneda_destino] if moneda_destino != 'USD' else 1.0

    monto_usd = monto / tasa_origen
    monto_destino = monto_usd * tasa_destino

    return jsonify({
        'monto_origen': monto,
        'moneda_origen': moneda_origen,
        'monto_destino': round(monto_destino, 2),
        'moneda_destino': moneda_destino,
        'tasa_cambio': round(tasa_destino / tasa_origen, 6),
        'actualizado_at': _ts_iso(),
    }), 200


@app.post('/api/v2/moneda/actualizar')
def forzar_actualizacion():
    """Disparado por Celery Beat cada hora para mantener tasas frescas."""
    _cache['actualizado_at'] = None  # Invalida caché

    try:
        tasas = ExchangeRateAPIAdapter().obtener_tasas()
        _cache['tasas'] = tasas
        _cache['actualizado_at'] = time.time()
        tasa_cop = tasas.get('COP')
        logger.info(f'[Moneda] Actualización forzada exitosa — COP/USD: {tasa_cop}')
        return jsonify({
            'status': 'success',
            'tasa_usd_cop': tasa_cop,
            'total_monedas': len(tasas),
            'actualizado_at': _ts_iso(),
        }), 200
    except Exception as exc:
        logger.error(f'[Moneda] Error en actualización forzada: {exc}')
        return error_response(503, 'API_ERROR', f'No se pudo actualizar tasas: {exc}')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5005)
