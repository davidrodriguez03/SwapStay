from django.urls import path
from .api_views import (
    CrearReservaAPIView,
    ListarReservasAPIView,
    DetalleReservaAPIView,
    ListarAlojamientosDisponiblesAPIView
)

app_name = 'reservas_api'

urlpatterns = [
    # Endpoints de Reservas
    path('reservas/', CrearReservaAPIView.as_view(), name='crear-reserva'),
    path('reservas/listar/', ListarReservasAPIView.as_view(), name='listar-reservas'),
    path('reservas/<int:pk>/', DetalleReservaAPIView.as_view(), name='detalle-reserva'),
    
    # Endpoints de Alojamientos
    path('alojamientos/disponibles/', ListarAlojamientosDisponiblesAPIView.as_view(), name='alojamientos-disponibles'),
]
