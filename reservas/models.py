from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal

class Estudiante(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    codigo_estudiantil = models.CharField(max_length=20)
    institucion = models.CharField(max_length=200)
    verificado = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.user.get_full_name()}"


##Dueño del alojamiento
class Arrendador(models.Model): 
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    telefono = models.CharField(max_length=20)
    
    def __str__(self):
        return f"{self.user.get_full_name()}"


class Alojamiento(models.Model):
    arrendador = models.ForeignKey(Arrendador, on_delete=models.CASCADE)
    nombre = models.CharField(max_length=200)
    direccion = models.CharField(max_length=255)
    ciudad = models.CharField(max_length=100)
    precio_mensual = models.DecimalField(max_digits=10, decimal_places=2)
    disponible = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.nombre} - {self.ciudad}"

class Casa(Alojamiento):
    numero_pisos = models.IntegerField()
    tiene_patio = models.BooleanField()
    tiene_garaje = models.BooleanField()

    def __str__(self):
        return f"Casa: {self.nombre} - {self.ciudad}"

class Apartamento(Alojamiento):
    numero_piso = models.IntegerField() 
    tiene_ascensor = models.BooleanField(default=False)
    tiene_porteria = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Apartamento: {self.nombre} - {self.ciudad}"


class Reserva(models.Model):
    ESTADO_CHOICES = [
        ('PENDIENTE', 'Pendiente'),
        ('CONFIRMADA', 'Confirmada'),
        ('CANCELADA', 'Cancelada'),
    ]
    
    estudiante = models.ForeignKey(Estudiante, on_delete=models.CASCADE)
    alojamiento = models.ForeignKey(Alojamiento, on_delete=models.CASCADE)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='PENDIENTE')
    monto_total = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Reserva #{self.id} - {self.estudiante}"