import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

ENV_TYPE = os.environ.get('ENV_TYPE', 'development')

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get(
    'SECRET_KEY',
    'django-insecure-l!-g)#(v@-26d9t0)$nf9org=fi97pgr1ui1xqu5-cx0b-$enm',
)

DEBUG = ENV_TYPE != 'production'

ALLOWED_HOSTS = os.environ.get(
    'ALLOWED_HOSTS',
    'localhost,127.0.0.1,django,nginx'
).split(',')

CSRF_TRUSTED_ORIGINS = [
    f'http://{h}' for h in os.environ.get(
        'ALLOWED_HOSTS', 'localhost,127.0.0.1'
    ).split(',') if h and h not in ('localhost', '127.0.0.1', 'django', 'nginx')
] + ['http://localhost', 'http://127.0.0.1']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'django_celery_beat',
    'reservas',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.template.context_processors.i18n',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# ── Base de datos ─────────────────────────────────────────────────────────────

if os.environ.get('DB_ENGINE') == 'postgres':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('DB_NAME', 'swapstay'),
            'USER': os.environ.get('DB_USER', 'swapstay'),
            'PASSWORD': os.environ.get('DB_PASSWORD', 'swapstay'),
            'HOST': os.environ.get('DB_HOST', 'localhost'),
            'PORT': os.environ.get('DB_PORT', '5432'),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }


# ── Validación de contraseñas ─────────────────────────────────────────────────

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# ── Internacionalización ──────────────────────────────────────────────────────

LANGUAGE_CODE = 'es'

LANGUAGES = [
    ('es', 'Español'),
    ('en', 'English'),
]

LOCALE_PATHS = [BASE_DIR / 'locale']

TIME_ZONE = 'America/Bogota'

USE_I18N = True
USE_L10N = True
USE_TZ = True


# ── Archivos estáticos ────────────────────────────────────────────────────────

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

INSTITUCIONES_VALIDAS = [
    # Colombia
    'EAFIT', 'Universidad de Antioquia', 'UPB', 'Universidad Nacional de Colombia',
    'Universidad de los Andes', 'Universidad del Rosario', 'Pontificia Universidad Javeriana',
    'Universidad del Norte', 'ICESI', 'Universidad del Valle',
    'Universidad Industrial de Santander', 'Universidad Tecnológica de Pereira',
    'Universidad de Medellín', 'Universidad Pontificia Bolivariana', 'Universidad de La Sabana',
    # Estados Unidos
    'Harvard University', 'Stanford University', 'Massachusetts Institute of Technology',
    'California Institute of Technology', 'Princeton University', 'Yale University',
    'Columbia University', 'University of Chicago', 'University of Pennsylvania',
    'Cornell University', 'Duke University', 'Northwestern University',
    'Johns Hopkins University', 'Dartmouth College', 'Brown University',
    'Vanderbilt University', 'Rice University', 'University of California Berkeley',
    'University of California Los Angeles', 'University of Southern California',
    'Carnegie Mellon University', 'Georgetown University', 'University of Michigan',
    'New York University', 'University of Virginia',
    # Reino Unido
    'University of Oxford', 'University of Cambridge', 'Imperial College London',
    'University College London', 'London School of Economics', 'University of Edinburgh',
    'Kings College London', 'University of Manchester', 'University of Warwick',
    'University of Bristol',
    # Canadá
    'University of Toronto', 'McGill University', 'University of British Columbia',
    'University of Montreal', 'University of Alberta', 'McMaster University',
    'University of Waterloo',
    # Australia
    'Australian National University', 'University of Melbourne', 'University of Sydney',
    'University of New South Wales', 'University of Queensland', 'Monash University',
    # Europa
    'ETH Zurich', 'Technical University of Munich', 'University of Amsterdam',
    'KU Leuven', 'Sorbonne University', 'Karolinska Institute', 'Uppsala University',
    'University of Copenhagen',
    # Asia
    'National University of Singapore', 'Nanyang Technological University',
    'Tsinghua University', 'Peking University', 'University of Tokyo', 'Kyoto University',
    'Seoul National University', 'KAIST', 'Hong Kong University',
    # América Latina
    'Universidad de Buenos Aires', 'Pontificia Universidad Católica de Chile',
    'Universidad de Chile', 'Tecnológico de Monterrey',
    'Universidad Nacional Autónoma de México', 'Universidade de São Paulo',
    'Universidad de Costa Rica',
]


# ── Django REST Framework ─────────────────────────────────────────────────────

REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
    ],
}

if ENV_TYPE == 'development':
    CORS_ALLOW_ALL_ORIGINS = True
else:
    CORS_ALLOWED_ORIGINS = os.environ.get('CORS_ALLOWED_ORIGINS', '').split(',')


# ── Celery ────────────────────────────────────────────────────────────────────

CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'America/Bogota'
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 300


# ── URLs de microservicios ────────────────────────────────────────────────────

NOTIFICACIONES_SERVICE_URL = os.environ.get(
    'NOTIFICACIONES_SERVICE_URL', 'http://flask-notificaciones:5002'
)
MONEDA_SERVICE_URL = os.environ.get(
    'MONEDA_SERVICE_URL', 'http://flask-moneda:5005'
)
DISPONIBILIDAD_SERVICE_URL = os.environ.get(
    'DISPONIBILIDAD_SERVICE_URL', 'http://flask-disponibilidad:5003'
)
VALIDACIONES_SERVICE_URL = os.environ.get(
    'VALIDACIONES_SERVICE_URL', 'http://flask-validaciones:5004'
)
GEOLOCALIZACION_SERVICE_URL = os.environ.get(
    'GEOLOCALIZACION_SERVICE_URL', 'http://flask-geolocalizacion:5006'
)
