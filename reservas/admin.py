from django.contrib import admin
from .models import Estudiante, Arrendador, Alojamiento, Reserva

admin.site.register(Estudiante)
admin.site.register(Arrendador)
admin.site.register(Alojamiento)
admin.site.register(Reserva)