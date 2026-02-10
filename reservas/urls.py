from django.urls import path
from .views import CrearReservaView

urlpatterns = [
    path('crear/', CrearReservaView.as_view(), name='crear'),
]