from datetime import date
from decimal import Decimal
from django.core.exceptions import ValidationError


class ReservaBuilder:
    ##Construye reservas paso a paso con validaciones
    
    def __init__(self):
        self._estudiante = None
        self._alojamiento = None
        self._fecha_inicio = None
        self._fecha_fin = None
    
    def para_estudiante(self, estudiante):
        if not estudiante.verificado:
            raise ValidationError("El estudiante debe estar verificado")
        self._estudiante = estudiante
        return self  # Para poder encadenar: .para_estudiante().en_alojamiento()
    
    def en_alojamiento(self, alojamiento):
        if not alojamiento.disponible:
            raise ValidationError("El alojamiento no está disponible")
        self._alojamiento = alojamiento
        return self
    
    def en_fechas(self, fecha_inicio, fecha_fin):
        # Validar que fecha_inicio sea futura
        if fecha_inicio < date.today():
            raise ValidationError("La fecha de inicio debe ser futura")
        
        # Validar que fecha_fin sea después de fecha_inicio
        if fecha_fin <= fecha_inicio:
            raise ValidationError("La fecha fin debe ser posterior al inicio")
        
        # Validar duración mínima (1 mes = 30 días)
        duracion = (fecha_fin - fecha_inicio).days
        if duracion < 30:
            raise ValidationError("La duración mínima es de 1 mes")
        
        self._fecha_inicio = fecha_inicio
        self._fecha_fin = fecha_fin
        return self
    
    def build(self):
        # Verificar que tenemos todos los datos
        if not all([self._estudiante, self._alojamiento, 
                    self._fecha_inicio, self._fecha_fin]):
            raise ValidationError("Faltan datos para crear la reserva")
        
        # Calcular monto total
        duracion_meses = (self._fecha_fin - self._fecha_inicio).days / 30
        monto_total = self._alojamiento.precio_mensual * Decimal(str(duracion_meses))
        
        # Crear la reserva (sin guardar todavía)
        from ..models import Reserva
        reserva = Reserva(
            estudiante=self._estudiante,
            alojamiento=self._alojamiento,
            fecha_inicio=self._fecha_inicio,
            fecha_fin=self._fecha_fin,
            monto_total=monto_total,
            estado='PENDIENTE'
        )
        
        return reserva