from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError

from .models import Alojamiento, Estudiante, AlojamientoImagen

class ReservaForm(forms.Form):
    alojamiento = forms.ModelChoiceField(
        queryset=Alojamiento.objects.filter(disponible=True)
    )
    fecha_inicio = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    fecha_fin = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))


class RegistroEstudianteForm(forms.Form):
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150, required=False)
    username = forms.CharField(max_length=150)
    email = forms.EmailField()
    telefono = forms.CharField(max_length=20, required=False)
    codigo_estudiantil = forms.CharField(max_length=20)
    institucion = forms.ChoiceField(choices=[])
    password1 = forms.CharField(widget=forms.PasswordInput())
    password2 = forms.CharField(widget=forms.PasswordInput())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instituciones = getattr(settings, 'INSTITUCIONES_VALIDAS', [])
        self.fields['institucion'].choices = [('', '-- Selecciona tu institución --')] + [
            (i, i) for i in instituciones
        ]

    def clean_email(self):
        email = self.cleaned_data.get('email', '')
        if not (email.endswith('.edu') or email.endswith('.edu.co')):
            raise ValidationError(
                'Solo correos institucionales (.edu o .edu.co) son válidos para estudiantes.'
            )
        return email.lower()

    def clean_institucion(self):
        inst = self.cleaned_data.get('institucion', '')
        validas = getattr(settings, 'INSTITUCIONES_VALIDAS', [])
        if inst not in validas:
            raise ValidationError('Por favor selecciona una institución válida.')
        return inst

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('password1') != cleaned.get('password2'):
            self.add_error('password2', 'Las contraseñas no coinciden.')
        return cleaned


class RegistroArrendadorForm(forms.Form):
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150, required=False)
    username = forms.CharField(max_length=150)
    email = forms.EmailField()
    telefono = forms.CharField(max_length=20)
    documento_identidad = forms.CharField(max_length=20, required=False)
    password1 = forms.CharField(widget=forms.PasswordInput())
    password2 = forms.CharField(widget=forms.PasswordInput())

    def clean_email(self):
        return self.cleaned_data.get('email', '').lower()

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('password1') != cleaned.get('password2'):
            self.add_error('password2', 'Las contraseñas no coinciden.')
        return cleaned


class PublicarAlojamientoForm(forms.Form):
    TIPO_CHOICES = [('alojamiento', 'Alojamiento'), ('casa', 'Casa'), ('apartamento', 'Apartamento')]

    tipo = forms.ChoiceField(choices=TIPO_CHOICES)
    nombre = forms.CharField(max_length=200)
    direccion = forms.CharField(max_length=255)
    ciudad = forms.CharField(max_length=100)
    precio_mensual = forms.DecimalField(max_digits=10, decimal_places=2, min_value=0)
    descripcion_completa = forms.CharField(widget=forms.Textarea(attrs={'rows': 5}), required=False)
    latitud = forms.DecimalField(max_digits=9, decimal_places=6, required=False)
    longitud = forms.DecimalField(max_digits=9, decimal_places=6, required=False)

    # Casa
    numero_pisos = forms.IntegerField(required=False, min_value=1)
    tiene_patio = forms.BooleanField(required=False)
    tiene_garaje = forms.BooleanField(required=False)

    # Apartamento
    numero_piso = forms.IntegerField(required=False, min_value=1)
    tiene_ascensor = forms.BooleanField(required=False)
    tiene_porteria = forms.BooleanField(required=False)


class CancelarReservaForm(forms.Form):
    motivo = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Describe el motivo de cancelación...'}),
        min_length=10,
    )
