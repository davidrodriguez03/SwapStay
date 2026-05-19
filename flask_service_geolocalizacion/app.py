import logging
import time
from abc import ABC, abstractmethod

import requests
from flask import Flask, jsonify, request

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CACHE_TTL = 86400  # 24 horas — las coordenadas no cambian

_geocache: dict = {}

CIUDADES_COLOMBIA = {
    'Bogotá':        {'lat': 4.7110,  'lon': -74.0721, 'departamento': 'Cundinamarca'},
    'Medellín':      {'lat': 6.2442,  'lon': -75.5812, 'departamento': 'Antioquia'},
    'Cali':          {'lat': 3.4516,  'lon': -76.5320, 'departamento': 'Valle del Cauca'},
    'Barranquilla':  {'lat': 10.9685, 'lon': -74.7813, 'departamento': 'Atlántico'},
    'Cartagena':     {'lat': 10.3910, 'lon': -75.4794, 'departamento': 'Bolívar'},
    'Manizales':     {'lat': 5.0703,  'lon': -75.5138, 'departamento': 'Caldas'},
    'Pereira':       {'lat': 4.8133,  'lon': -75.6961, 'departamento': 'Risaralda'},
    'Bucaramanga':   {'lat': 7.1254,  'lon': -73.1198, 'departamento': 'Santander'},
    'Cúcuta':        {'lat': 7.8939,  'lon': -72.5078, 'departamento': 'Norte de Santander'},
    'Ibagué':        {'lat': 4.4389,  'lon': -75.2322, 'departamento': 'Tolima'},
    'Santa Marta':   {'lat': 11.2408, 'lon': -74.1990, 'departamento': 'Magdalena'},
    'Villavicencio': {'lat': 4.1420,  'lon': -73.6266, 'departamento': 'Meta'},
    'Pasto':         {'lat': 1.2136,  'lon': -77.2811, 'departamento': 'Nariño'},
    'Montería':      {'lat': 8.7575,  'lon': -75.8851, 'departamento': 'Córdoba'},
    'Armenia':       {'lat': 4.5339,  'lon': -75.6811, 'departamento': 'Quindío'},
}


# ── Adapter Pattern ───────────────────────────────────────────────────────────

class GeolocalizacionAdapter(ABC):
    @abstractmethod
    def geocodificar(self, ciudad: str, pais: str) -> dict:
        pass


class NominatimAdapter(GeolocalizacionAdapter):
    """Adapter para Nominatim (OpenStreetMap) — gratuito, sin API key."""
    BASE_URL = 'https://nominatim.openstreetmap.org/search'

    def geocodificar(self, ciudad: str, pais: str) -> dict:
        response = requests.get(
            self.BASE_URL,
            params={'q': f'{ciudad}, {pais}', 'format': 'json', 'limit': 1},
            headers={'User-Agent': 'SwapStay/2.0 (arquitectura-software@swapstay.edu.co)'},
            timeout=10,
        )
        response.raise_for_status()
        results = response.json()
        if not results:
            raise ValueError(f'Nominatim: sin resultados para "{ciudad}, {pais}"')
        r = results[0]
        return {
            'lat': float(r['lat']),
            'lon': float(r['lon']),
            'nombre_completo': r.get('display_name', ''),
            'fuente': 'nominatim',
        }


class PreSeedAdapter(GeolocalizacionAdapter):
    """Adapter de fallback con ciudades colombianas pre-cargadas."""

    def geocodificar(self, ciudad: str, pais: str) -> dict:
        ciudad_lower = ciudad.lower().strip()
        for nombre, datos in CIUDADES_COLOMBIA.items():
            if nombre.lower() in ciudad_lower or ciudad_lower in nombre.lower():
                return {
                    'lat': datos['lat'],
                    'lon': datos['lon'],
                    'nombre_completo': f'{nombre}, {datos["departamento"]}, Colombia',
                    'fuente': 'preseed',
                }
        raise ValueError(f'PreSeed: "{ciudad}" no encontrada en el catálogo')


def geocodificar_con_fallback(ciudad: str, pais: str) -> dict:
    cache_key = f'{ciudad.lower().strip()}:{pais.lower().strip()}'
    ahora = time.time()

    if cache_key in _geocache:
        entrada = _geocache[cache_key]
        if ahora - entrada['_ts'] < CACHE_TTL:
            return {k: v for k, v in entrada.items() if k != '_ts'}

    for adapter in (NominatimAdapter(), PreSeedAdapter()):
        try:
            resultado = adapter.geocodificar(ciudad, pais)
            _geocache[cache_key] = {**resultado, '_ts': ahora}
            logger.info(
                f'[Geo] {ciudad} geocodificado via {adapter.__class__.__name__}: '
                f'{resultado["lat"]},{resultado["lon"]}'
            )
            return resultado
        except Exception as exc:
            logger.warning(f'[Geo] {adapter.__class__.__name__} falló para "{ciudad}": {exc}')

    raise ValueError(f'No se pudo geocodificar "{ciudad}, {pais}"')


def error_response(status_code: int, code: str, message: str, details=None):
    payload = {'error': {'code': code, 'message': message}}
    if details:
        payload['error']['details'] = details
    return jsonify(payload), status_code


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get('/health')
def health():
    return jsonify({
        'status': 'ok',
        'service': 'flask-geolocalizacion',
        'ciudades_precargadas': len(CIUDADES_COLOMBIA),
        'entradas_en_cache': len(_geocache),
    }), 200


@app.get('/api/v2/geolocalizacion/geocodificar')
def geocodificar():
    ciudad = request.args.get('ciudad', '').strip()
    pais = request.args.get('pais', 'Colombia').strip()

    if not ciudad:
        return error_response(400, 'MISSING_PARAM', 'Parámetro requerido: ciudad')

    try:
        resultado = geocodificar_con_fallback(ciudad, pais)
        return jsonify({
            'ciudad': ciudad,
            'pais': pais,
            'lat': resultado['lat'],
            'lon': resultado['lon'],
            'nombre_completo': resultado['nombre_completo'],
            'fuente': resultado['fuente'],
            'mapa_url': (
                f'https://www.openstreetmap.org/'
                f'?mlat={resultado["lat"]}&mlon={resultado["lon"]}&zoom=13'
            ),
        }), 200
    except ValueError as exc:
        return error_response(404, 'NOT_FOUND', str(exc))
    except Exception as exc:
        logger.error(f'[Geo] Error inesperado para "{ciudad}": {exc}')
        return error_response(503, 'SERVICE_ERROR', 'Error interno al geocodificar')


@app.get('/api/v2/geolocalizacion/ciudades')
def listar_ciudades():
    ciudades = [
        {
            'nombre': nombre,
            'departamento': datos['departamento'],
            'lat': datos['lat'],
            'lon': datos['lon'],
            'mapa_url': (
                f'https://www.openstreetmap.org/'
                f'?mlat={datos["lat"]}&mlon={datos["lon"]}&zoom=11'
            ),
        }
        for nombre, datos in CIUDADES_COLOMBIA.items()
    ]
    return jsonify({'total': len(ciudades), 'ciudades': ciudades}), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5006)
