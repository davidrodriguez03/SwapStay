from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal
from datetime import date, timedelta


class Estudiante(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    codigo_estudiantil = models.CharField(max_length=20)
    institucion = models.CharField(max_length=200)
    telefono = models.CharField(max_length=20, blank=True)
    verificado = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.get_full_name()}"


class Arrendador(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    telefono = models.CharField(max_length=20)
    documento_identidad = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return f"{self.user.get_full_name()}"


class Alojamiento(models.Model):
    arrendador = models.ForeignKey(Arrendador, on_delete=models.CASCADE)
    nombre = models.CharField(max_length=200)
    direccion = models.CharField(max_length=255)
    ciudad = models.CharField(max_length=100)
    precio_mensual = models.DecimalField(max_digits=10, decimal_places=2)
    disponible = models.BooleanField(default=True)
    descripcion_completa = models.TextField(blank=True)
    latitud = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitud = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    def __str__(self):
        return f"{self.nombre} - {self.ciudad}"

    def get_imagen_principal(self):
        img = self.imagenes.filter(es_principal=True).first()
        if img is None:
            img = self.imagenes.order_by('orden').first()
        return img


class AlojamientoImagen(models.Model):
    alojamiento = models.ForeignKey(Alojamiento, on_delete=models.CASCADE, related_name='imagenes')
    imagen = models.ImageField(upload_to='alojamientos/%Y/%m/')
    orden = models.IntegerField(default=0)
    es_principal = models.BooleanField(default=False)

    class Meta:
        ordering = ['orden']

    def __str__(self):
        return f"Imagen {self.orden} — {self.alojamiento.nombre}"


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
    CANCELADA_POR_CHOICES = [
        ('estudiante', 'Estudiante'),
        ('arrendador', 'Arrendador'),
    ]

    estudiante = models.ForeignKey(Estudiante, on_delete=models.CASCADE)
    alojamiento = models.ForeignKey(Alojamiento, on_delete=models.CASCADE)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='PENDIENTE')
    monto_total = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    motivo_cancelacion = models.TextField(null=True, blank=True)
    cancelada_por = models.CharField(
        max_length=20, choices=CANCELADA_POR_CHOICES, null=True, blank=True
    )
    renovacion_de = models.ForeignKey(
        'self', null=True, blank=True, on_delete=models.SET_NULL, related_name='renovaciones'
    )

    def __str__(self):
        return f"Reserva #{self.id} - {self.estudiante}"

    def puede_cancelarse(self):
        return self.estado != 'CANCELADA' and date.today() < self.fecha_inicio

    def esta_activa(self):
        hoy = date.today()
        return self.fecha_inicio <= hoy <= self.fecha_fin

    def esta_por_vencer(self):
        return (
            self.estado == 'CONFIRMADA'
            and self.esta_activa()
            and (self.fecha_fin - date.today()) <= timedelta(days=7)
        )
