# CONTEXT.md — SwapStay Entrega 2
## Arquitectura de Software 2026-I — Migración a Microservicios

**Equipo:** David Rodriguez Espinosa · Luis Alfonso Agudelo Ramirez · Julián Lara Aristizabal

---

## 🚦 ESTADO DE IMPLEMENTACIÓN (2026-05-19)

| Fase | Descripción | Estado |
|------|-------------|--------|
| **Fase 1** | Frontend Bootstrap 5 + Alpine.js (corrección E1) | ✅ COMPLETADO |
| **Fase 2** | Celery + Redis (tareas asíncronas) | ✅ COMPLETADO |
| **Fase 3** | 5 microservicios Flask adicionales | ✅ COMPLETADO |
| **Fase 4** | Despliegue AWS (EC2 + scripts + settings prod) | ✅ COMPLETADO |
| **Fase 5** | i18n ES/EN (locale, middleware, selector navbar) | ✅ COMPLETADO |
| **Fase 6** | Adapter Pattern en Django (`reservas/domain/adapters/`) | ✅ COMPLETADO |

---

## 📊 RÚBRICA

| Criterio | Peso | Estado |
|----------|------|--------|
| Correcciones E1 (frontend) | 10% | ✅ |
| Arquitectura (diagramas) | 10% | ⏳ manual |
| Servicios (proveer + consumir aliado + Adapter tercero) | 30% | ✅ |
| Infraestructura (AWS + Docker + Nginx) | 30% | ✅ |
| Resiliencia/UX (i18n + async + UX) | 20% | ✅ |

⚠️ Sin 100% correcciones E1 → Nota 0.0

### Servicios — detalle
| Sub-criterio | Implementación | Endpoint |
|---|---|---|
| Proveer servicio | `EstadisticasSistemaAPIView` | `GET /api/v1/sistema/estadisticas/` |
| Consumir aliado | `EquipoAliadoService` en `services.py` | usado internamente con fallback graceful |
| Adapter Pattern (tercero) | `reservas/domain/adapters/` (3 ABCs × 2-3 implementaciones) | vía `EstadisticasSistemaAPIView` (COP→USD) |

---

## 📂 ESTRUCTURA DEL PROYECTO

```
SwapStay/
├── config/
│   ├── settings.py        ✅ STATIC_ROOT, DEBUG env-based, django_celery_beat,
│   │                         LocaleMiddleware, LANGUAGES, LOCALE_PATHS,
│   │                         URLs de 6 microservicios
│   ├── urls.py            ✅ i18n/ + /api/v1/ + /api/ + frontend
│   ├── celery.py          ✅ beat_schedule: tasas cada hora + reporte diario 8am
│   └── __init__.py        ✅ exporta celery_app
│
├── reservas/
│   ├── domain/
│   │   ├── builders.py          ✅ Builder Pattern (ReservaBuilder)
│   │   └── adapters/            ✅ Adapter Pattern (Fase 6)
│   │       ├── __init__.py
│   │       ├── currency_adapter.py    ABC CurrencyAdapter
│   │       │                          → MicroserviceMonedaAdapter (μS 5)
│   │       │                          → OpenERAPIAdapter (open.er-api.com, sin key)
│   │       │                          → MockAdapter (estático, sin red)
│   │       ├── email_adapter.py       ABC EmailAdapter
│   │       │                          → MicroserviceNotificacionesAdapter (μS 2)
│   │       │                          → MockEmailAdapter (log)
│   │       └── geolocation_adapter.py ABC GeoAdapter
│   │                                  → MicroserviceGeoAdapter (μS 6)
│   │                                  → PreSeedGeoAdapter (15 ciudades CO, sin red)
│   ├── infra/
│   │   └── factories.py         ✅ Factory Pattern (ConsoleNotificador / EmailNotificador)
│   ├── models.py                ✅ Estudiante, Arrendador, Alojamiento, Casa, Apartamento, Reserva
│   ├── services.py              ✅ ReservaService + EquipoAliadoService
│   ├── tasks.py                 ✅ 4 tareas Celery
│   ├── api_views.py             ✅ CrearReserva, ListarReservas, DetalleReserva,
│   │                               ListarAlojamientosDisponibles, EstadisticasSistema
│   ├── api_urls.py              ✅ /reservas/, /alojamientos/disponibles/,
│   │                               /sistema/estadisticas/
│   ├── views.py                 ✅ 8 vistas frontend (CBV)
│   ├── urls.py                  ✅ 8 rutas frontend
│   ├── serializers.py           ✅
│   └── forms.py                 ✅ ReservaForm
│
├── templates/                   ✅ Bootstrap 5.3 + Alpine.js 3 + Font Awesome 6
│   ├── base.html                ✅ {% load i18n %} + selector idioma 🇨🇴/🇺🇸
│   ├── landing.html             ✅ Hero + stats BD + "Cómo funciona" + destacados
│   ├── dashboard.html           ✅ Stats + conversor COP→USD (fetch open.er-api.com)
│   ├── auth/login.html          ✅
│   ├── auth/register.html       ✅
│   ├── alojamientos/catalogo.html    ✅ Filtros sidebar + grid cards
│   ├── alojamientos/detalle.html     ✅ Calculadora estadía + COP→USD sidebar
│   └── reservas/crear.html           ✅ Wizard 3 pasos Alpine.js
│
├── static/
│   ├── css/custom.css           ✅ Variables CSS, animaciones, mobile-first
│   └── js/main.js               ✅ IntersectionObserver, auto-dismiss, date min=today
│
├── flask_service/                    ✅ μS 1 — Cotizaciones   :5000
├── flask_service_notificaciones/     ✅ μS 2 — Notificaciones :5002
│   └── app.py  → ConsoleAdapter (dev) / SendGridAdapter (prod)
├── flask_service_disponibilidad/     ✅ μS 3 — Disponibilidad :5003
│   └── app.py  → psycopg2 read-only PostgreSQL
├── flask_service_validaciones/       ✅ μS 4 — Validaciones   :5004
│   └── app.py  → reglas de negocio puras (sin deps externas)
├── flask_service_moneda/             ✅ μS 5 — Moneda         :5005
│   └── app.py  → ExchangeRateAPIAdapter / FallbackAdapter estático
├── flask_service_geolocalizacion/    ✅ μS 6 — Geolocalización :5006
│   └── app.py  → NominatimAdapter / PreSeedAdapter (15 ciudades CO)
│
├── nginx/nginx.conf             ✅ 7 upstreams + routing /api/v2/* + static/ + fallback /
├── locale/
│   ├── es/LC_MESSAGES/django.po ✅ ~40 cadenas ES
│   └── en/LC_MESSAGES/django.po ✅ ~40 cadenas EN
│
├── scripts/
│   ├── setup_ec2.sh             ✅ Ubuntu 24.04 — Docker, UFW, clone repo
│   └── deploy.sh                ✅ pull + build + migrate + up + status
│
├── Dockerfile                   ✅ python:3.12-slim (Django + Celery)
├── docker-compose.yml           ✅ 11 servicios: db, redis, django, celery_worker,
│                                    celery_beat, flask ×6, nginx
├── requirements-django.txt      ✅ django, drf, celery[redis], django-celery-beat,
│                                    redis, requests, psycopg2-binary, corsheaders
├── .env.example                 ✅ plantilla completa
└── .gitignore                   ✅ UTF-8, ignora __pycache__, .env, staticfiles/, *.mo
```

---

## 🔧 DETALLES DE IMPLEMENTACIÓN

### Patrones de diseño usados
| Patrón | Dónde | Propósito |
|--------|-------|-----------|
| **Builder** | `reservas/domain/builders.py` | Construir `Reserva` con validaciones encadenadas |
| **Factory** | `reservas/infra/factories.py` | Seleccionar notificador (consola / email) según ENV |
| **Adapter** | `reservas/domain/adapters/` | Abstraer μS externos + 3rd-party APIs en Django |
| **Adapter** | `flask_service_moneda/app.py` | ExchangeRateAPI ↔ FallbackAdapter en Flask |
| **Adapter** | `flask_service_notificaciones/app.py` | Console ↔ SendGrid en Flask |
| **Adapter** | `flask_service_geolocalizacion/app.py` | Nominatim ↔ PreSeed en Flask |
| **Strangler Fig** | `config/urls.py` + nginx | Migración incremental monolito → microservicios |

### Tareas Celery
| Tarea | Trigger | Fallback |
|-------|---------|---------|
| `enviar_confirmacion_reserva` | `.delay()` al crear reserva | consola; retry ×3 |
| `actualizar_tasas_cambio` | Beat cada hora | open.er-api.com directo |
| `generar_reporte_mensual` | Beat diario 8am | sin deps externas |
| `enviar_recordatorio_pago` | manual/beat | consola; retry ×2 |

### Microservicios Flask — Endpoints
| μS | Puerto | Endpoint clave | Patrón interno |
|----|--------|---------------|----------------|
| Cotizaciones | 5000 | `POST /api/v2/funcionalidad` | — |
| Notificaciones | 5002 | `POST /api/v2/notificaciones/email` | Adapter |
| Disponibilidad | 5003 | `GET /api/v2/disponibilidad/<id>` | — |
| Validaciones | 5004 | `POST /api/v2/validaciones/reserva` | — |
| Moneda | 5005 | `GET /api/v2/moneda/cotizar` | Adapter |
| Geolocalización | 5006 | `GET /api/v2/geolocalizacion/geocodificar` | Adapter |

Todos tienen: `/health`, Dockerfile, graceful fallback, logging.

### Nginx routing
```
/static/                  → staticfiles volume
/api/v1/                  → django:8000
/api/v2/notificaciones/   → flask-notificaciones:5002
/api/v2/disponibilidad/   → flask-disponibilidad:5003
/api/v2/validaciones/     → flask-validaciones:5004
/api/v2/moneda/           → flask-moneda:5005
/api/v2/geolocalizacion/  → flask-geolocalizacion:5006
/api/v2/cotizaciones      → flask:5000
/                         → django:8000 (frontend + admin)
```

### Django API endpoints (v1)
```
POST /api/v1/reservas/                  → crear reserva
GET  /api/v1/reservas/listar/           → listar todas
GET  /api/v1/reservas/<pk>/             → detalle
GET  /api/v1/alojamientos/disponibles/  → disponibles
GET  /api/v1/sistema/estadisticas/      → métricas + conversión COP→USD (Adapter Pattern)
```

---

## 🚀 COMANDOS ÚTILES

```bash
# Levantar todo
docker compose up -d

# Ver logs
docker compose logs -f celery_worker
docker compose logs -f django

# Migrations + superusuario
docker compose exec django python manage.py migrate
docker compose exec django python manage.py createsuperuser

# Compilar traducciones
docker compose exec django python manage.py compilemessages

# Health checks
curl http://localhost/health
curl http://localhost/api/v1/sistema/estadisticas/
curl http://localhost/api/v2/moneda/tasas
curl http://localhost/api/v2/geolocalizacion/ciudades

# Disparar tarea Celery manualmente
docker compose exec django python manage.py shell
>>> from reservas.tasks import actualizar_tasas_cambio
>>> actualizar_tasas_cambio.delay()
```

---

## ⚠️ NOTAS IMPORTANTES

- **`.gitignore` era UTF-16** → git no parseaba ninguna regla; corregido a UTF-8
- `STATIC_ROOT = BASE_DIR / 'staticfiles'` — necesario para `collectstatic` en Docker
- `DEBUG = ENV_TYPE != 'production'` — cambiar `ENV_TYPE=production` en `.env` para prod
- `django-celery-beat` requerido para `DatabaseScheduler` en `celery_beat`
- Microservicio cotizaciones escucha en puerto **5000** (no 5001)
- Todos los μS tienen fallback: si están caídos las reservas siguen funcionando
- `compilemessages` requiere `gettext` — incluido en `python:3.12-slim` via apt
- `EquipoAliadoService` consume la API del equipo aliado; si no responde retorna `[]`
