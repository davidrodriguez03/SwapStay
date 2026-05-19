import logging
import os
from abc import ABC, abstractmethod

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

# Pre-seed de 15 ciudades colombianas (lat/lon WGS84)
_CIUDADES_CO = {
    'bogota':         {'lat': 4.7110,  'lon': -74.0721, 'ciudad': 'Bogotá',        'pais': 'Colombia'},
    'bogotá':         {'lat': 4.7110,  'lon': -74.0721, 'ciudad': 'Bogotá',        'pais': 'Colombia'},
    'medellin':       {'lat': 6.2442,  'lon': -75.5812, 'ciudad': 'Medellín',      'pais': 'Colombia'},
    'medellín':       {'lat': 6.2442,  'lon': -75.5812, 'ciudad': 'Medellín',      'pais': 'Colombia'},
    'cali':           {'lat': 3.4516,  'lon': -76.5320, 'ciudad': 'Cali',          'pais': 'Colombia'},
    'barranquilla':   {'lat': 10.9685, 'lon': -74.7813, 'ciudad': 'Barranquilla',  'pais': 'Colombia'},
    'cartagena':      {'lat': 10.3910, 'lon': -75.4794, 'ciudad': 'Cartagena',     'pais': 'Colombia'},
    'bucaramanga':    {'lat': 7.1193,  'lon': -73.1227, 'ciudad': 'Bucaramanga',   'pais': 'Colombia'},
    'pereira':        {'lat': 4.8143,  'lon': -75.6946, 'ciudad': 'Pereira',       'pais': 'Colombia'},
    'manizales':      {'lat': 5.0703,  'lon': -75.5138, 'ciudad': 'Manizales',     'pais': 'Colombia'},
    'santa marta':    {'lat': 11.2408, 'lon': -74.1990, 'ciudad': 'Santa Marta',   'pais': 'Colombia'},
    'cucuta':         {'lat': 7.8939,  'lon': -72.5078, 'ciudad': 'Cúcuta',        'pais': 'Colombia'},
    'cúcuta':         {'lat': 7.8939,  'lon': -72.5078, 'ciudad': 'Cúcuta',        'pais': 'Colombia'},
    'ibague':         {'lat': 4.4389,  'lon': -75.2322, 'ciudad': 'Ibagué',        'pais': 'Colombia'},
    'ibagué':         {'lat': 4.4389,  'lon': -75.2322, 'ciudad': 'Ibagué',        'pais': 'Colombia'},
    'villavicencio':  {'lat': 4.1420,  'lon': -73.6266, 'ciudad': 'Villavicencio', 'pais': 'Colombia'},
    'pasto':          {'lat': 1.2136,  'lon': -77.2811, 'ciudad': 'Pasto',         'pais': 'Colombia'},
    'monteria':       {'lat': 8.7575,  'lon': -75.8813, 'ciudad': 'Montería',      'pais': 'Colombia'},
    'montería':       {'lat': 8.7575,  'lon': -75.8813, 'ciudad': 'Montería',      'pais': 'Colombia'},
    'armenia':        {'lat': 4.5339,  'lon': -75.6816, 'ciudad': 'Armenia',       'pais': 'Colombia'},
}


class GeoAdapter(ABC):
    @abstractmethod
    def geocodificar(self, ciudad: str, pais: str = 'Colombia') -> dict:
        """Retorna dict con claves: encontrado (bool), lat, lon, ciudad, pais."""


class MicroserviceGeoAdapter(GeoAdapter):
    """Delega la geocodificación al microservicio Flask de geolocalización (μS 6, puerto 5006)."""

    def geocodificar(self, ciudad: str, pais: str = 'Colombia') -> dict:
        url = f"{settings.GEOLOCALIZACION_SERVICE_URL}/api/v2/geolocalizacion/geocodificar"
        resp = requests.get(url, params={'ciudad': ciudad, 'pais': pais}, timeout=8)
        resp.raise_for_status()
        return resp.json()


class PreSeedGeoAdapter(GeoAdapter):
    """Resuelve coordenadas desde un diccionario estático de 15 ciudades colombianas.
    No requiere red. Usado como fallback o en ENV_TYPE=test.
    """

    def geocodificar(self, ciudad: str, pais: str = 'Colombia') -> dict:
        key = ciudad.lower().strip()
        data = _CIUDADES_CO.get(key)
        if data:
            return {'encontrado': True, **data}
        return {'encontrado': False, 'ciudad': ciudad, 'pais': pais, 'lat': None, 'lon': None}

    def listar_ciudades(self) -> list:
        vistas = set()
        ciudades = []
        for data in _CIUDADES_CO.values():
            if data['ciudad'] not in vistas:
                vistas.add(data['ciudad'])
                ciudades.append(data)
        return sorted(ciudades, key=lambda c: c['ciudad'])


def get_geo_adapter() -> GeoAdapter:
    """Devuelve el adaptador de geolocalización según el entorno.

    - ENV_TYPE=test → PreSeedGeoAdapter (sin red)
    - Default → MicroserviceGeoAdapter
    """
    if os.environ.get('ENV_TYPE') == 'test':
        return PreSeedGeoAdapter()
    return MicroserviceGeoAdapter()
