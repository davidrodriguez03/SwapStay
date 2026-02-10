from django.views.generic import FormView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.contrib import messages

from .forms import ReservaForm
from .services import ReservaService


class CrearReservaView(FormView):
    template_name = 'reservas/crear_reserva.html'
    form_class = ReservaForm
    success_url = reverse_lazy('admin:index') 
    
    def form_valid(self, form):
        service = ReservaService()
        reserva = service.crear_reserva(
            estudiante=form.cleaned_data['estudiante'],
            alojamiento=form.cleaned_data['alojamiento'],
            fecha_inicio=form.cleaned_data['fecha_inicio'],
            fecha_fin=form.cleaned_data['fecha_fin']
        )
        messages.success(self.request, f'Reserva #{reserva.id} creada!')
        return super().form_valid(form)
