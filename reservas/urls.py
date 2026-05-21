from django.urls import path
from .views import (
    LandingView,
    LoginView,
    RegisterView,
    LogoutView,
    DashboardView,
    CatalogoView,
    DetalleAlojamientoView,
    CrearReservaView,
    CancelarReservaView,
    RenovarReservaView,
    PublicarAlojamientoView,
    editar_alojamiento,
    eliminar_alojamiento,
    eliminar_imagen_alojamiento,
)

urlpatterns = [
    path('',                          LandingView.as_view(),              name='landing'),
    path('login/',                    LoginView.as_view(),                name='login'),
    path('registro/',                 RegisterView.as_view(),             name='register'),
    path('logout/',                   LogoutView.as_view(),               name='logout'),
    path('dashboard/',                DashboardView.as_view(),            name='dashboard'),
    path('explorar/',                 CatalogoView.as_view(),             name='catalogo'),
    path('alojamiento/<int:pk>/',     DetalleAlojamientoView.as_view(),   name='detalle_alojamiento'),
    path('reservas/crear/',           CrearReservaView.as_view(),         name='crear_reserva'),
    path('reservas/<int:pk>/cancelar/', CancelarReservaView.as_view(),    name='cancelar_reserva'),
    path('reservas/<int:pk>/renovar/', RenovarReservaView.as_view(),      name='renovar_reserva'),
    path('alojamientos/publicar/',    PublicarAlojamientoView.as_view(),  name='publicar_alojamiento'),
    path('alojamientos/<int:pk>/editar/',   editar_alojamiento,           name='editar_alojamiento'),
    path('alojamientos/<int:pk>/eliminar/', eliminar_alojamiento,         name='eliminar_alojamiento'),
    path('alojamientos/imagenes/<int:pk>/eliminar/', eliminar_imagen_alojamiento, name='eliminar_imagen'),
]
