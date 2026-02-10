from django import forms
from .models import Alojamiento
from .models import Estudiante, Alojamiento  # ajusta el import

class ReservaForm(forms.Form):
    estudiante = forms.ModelChoiceField(
        queryset=Estudiante.objects.all()
    )
    alojamiento = forms.ModelChoiceField(
        queryset=Alojamiento.objects.filter(disponible=True)
    )
    fecha_inicio = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    fecha_fin = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
