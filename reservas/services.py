from django.db import transaction
from django.core.exceptions import ValidationError

from .domain.builders import ReservaBuilder
from .infra.factories import NotificadorFactory


class ReservaService:
    def __init__(self):
        # Crear el notificador usando la Factory
        self.notificador = NotificadorFactory.crear()
    
    @transaction.atomic  # Si algo falla, se revierte todo
    def crear_reserva(self, estudiante, alojamiento, fecha_inicio, fecha_fin):
        # 1. Construir reserva con Builder (valida automáticamente)
        reserva = (ReservaBuilder()
                   .para_estudiante(estudiante)
                   .en_alojamiento(alojamiento)
                   .en_fechas(fecha_inicio, fecha_fin)
                   .build())
        
        # 2. Guardar en BD
        reserva.save()
        
        # 3. Marcar alojamiento como no disponible
        alojamiento.disponible = False
        alojamiento.save()
        
        # 4. Confirmar reserva
        reserva.estado = 'CONFIRMADA'
        reserva.save()
        
        # 5. Enviar notificación (Factory decide cuál usar)
        self.notificador.enviar_confirmacion(reserva)
        
        return reserva