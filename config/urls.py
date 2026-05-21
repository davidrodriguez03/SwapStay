from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static

from reservas.api_public import (
    alojamientos_disponibles,
    verificar_disponibilidad,
    crear_reserva_externa,
    consultar_reserva,
)

urlpatterns = [
    path('i18n/', include('django.conf.urls.i18n')),
    path('admin/', admin.site.urls),

    # API pública — integración externa (sin autenticación)
    path('api/v1/alojamientos/disponibles/',               alojamientos_disponibles,   name='pub-alojamientos-disponibles'),
    path('api/v1/alojamientos/verificar-disponibilidad/',  verificar_disponibilidad,   name='pub-verificar-disponibilidad'),
    path('api/v1/reservas/crear/',                         crear_reserva_externa,      name='pub-crear-reserva'),
    path('api/v1/reservas/<str:codigo>/',                  consultar_reserva,          name='pub-consultar-reserva'),

    # API interna DRF + frontend
    path('api/v1/', include('reservas.api_urls')),
    path('api/',    include('reservas.api_urls')),
    path('',        include('reservas.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
