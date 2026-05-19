from django.views.generic import FormView, TemplateView, ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy
from django.db.models import Sum, Q

from .forms import ReservaForm
from .services import ReservaService
from .models import Alojamiento, Casa, Apartamento, Reserva, Estudiante


# ── Landing ──────────────────────────────────────────────────────────────────

class LandingView(TemplateView):
    template_name = 'landing.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['alojamientos_destacados'] = _alojamientos_con_tipo(
            Alojamiento.objects.filter(disponible=True)[:6]
        )
        ctx['total_alojamientos'] = Alojamiento.objects.count()
        ctx['total_estudiantes']  = Estudiante.objects.count()
        ctx['total_ciudades']     = Alojamiento.objects.values('ciudad').distinct().count()
        return ctx


# ── Auth ──────────────────────────────────────────────────────────────────────

class LoginView(TemplateView):
    template_name = 'auth/login.html'

    def post(self, request):
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            next_url = request.GET.get('next', 'dashboard')
            return redirect(next_url)
        messages.error(request, 'Usuario o contraseña incorrectos.')
        return self.get(request)


class RegisterView(TemplateView):
    template_name = 'auth/register.html'

    def post(self, request):
        username   = request.POST.get('username')
        email      = request.POST.get('email')
        password1  = request.POST.get('password1')
        password2  = request.POST.get('password2')
        first_name = request.POST.get('first_name', '')
        last_name  = request.POST.get('last_name', '')

        if password1 != password2:
            messages.error(request, 'Las contraseñas no coinciden.')
            return self.get(request)

        if User.objects.filter(username=username).exists():
            messages.error(request, 'Ese nombre de usuario ya existe.')
            return self.get(request)

        user = User.objects.create_user(
            username=username, email=email,
            password=password1,
            first_name=first_name, last_name=last_name,
        )
        login(request, user)
        messages.success(request, f'¡Bienvenido/a, {user.first_name or username}!')
        return redirect('dashboard')


class LogoutView(TemplateView):
    def post(self, request):
        logout(request)
        return redirect('landing')


# ── Dashboard ─────────────────────────────────────────────────────────────────

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard.html'
    login_url = 'login'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user

        try:
            estudiante = user.estudiante
        except Estudiante.DoesNotExist:
            estudiante = None

        if estudiante:
            reservas = Reserva.objects.filter(
                estudiante=estudiante
            ).select_related('alojamiento').order_by('-fecha_creacion')
        else:
            reservas = Reserva.objects.none()

        monto = reservas.aggregate(total=Sum('monto_total'))['total'] or 0

        ctx.update({
            'estudiante':          estudiante,
            'reservas':            reservas,
            'reservas_count':      reservas.count(),
            'reservas_confirmadas': reservas.filter(estado='CONFIRMADA').count(),
            'reservas_pendientes': reservas.filter(estado='PENDIENTE').count(),
            'monto_total':         monto,
        })
        return ctx


# ── Catálogo ──────────────────────────────────────────────────────────────────

class CatalogoView(TemplateView):
    template_name = 'alojamientos/catalogo.html'

    def get_context_data(self, **kwargs):
        ctx  = super().get_context_data(**kwargs)
        qs   = Alojamiento.objects.select_related('arrendador__user')
        req  = self.request.GET

        if req.get('ciudad'):
            qs = qs.filter(ciudad__icontains=req['ciudad'])

        tipo = req.get('tipo', '').lower()
        if tipo == 'casa':
            qs = qs.filter(casa__isnull=False)
        elif tipo == 'apartamento':
            qs = qs.filter(apartamento__isnull=False)

        if req.get('precio_max'):
            try:
                qs = qs.filter(precio_mensual__lte=float(req['precio_max']))
            except ValueError:
                pass

        if req.get('disponible') != '0':
            qs = qs.filter(disponible=True)

        orden = req.get('orden', '')
        if orden == 'precio_asc':
            qs = qs.order_by('precio_mensual')
        elif orden == 'precio_desc':
            qs = qs.order_by('-precio_mensual')

        ctx['alojamientos'] = _alojamientos_con_tipo(qs)
        return ctx


# ── Detalle alojamiento ───────────────────────────────────────────────────────

class DetalleAlojamientoView(TemplateView):
    template_name = 'alojamientos/detalle.html'

    def get_context_data(self, **kwargs):
        ctx  = super().get_context_data(**kwargs)
        aloj = get_object_or_404(Alojamiento, pk=kwargs['pk'])

        try:
            aloj = aloj.casa
            tipo = 'Casa'
        except Casa.DoesNotExist:
            pass
        else:
            ctx['alojamiento'] = aloj
            ctx['tipo'] = tipo
            return ctx

        try:
            aloj = aloj.apartamento
            tipo = 'Apartamento'
        except Apartamento.DoesNotExist:
            tipo = 'Alojamiento'

        ctx['alojamiento'] = aloj
        ctx['tipo'] = tipo
        return ctx


# ── Crear reserva (wizard) ────────────────────────────────────────────────────

class CrearReservaView(LoginRequiredMixin, FormView):
    template_name = 'reservas/crear.html'
    form_class    = ReservaForm
    success_url   = reverse_lazy('dashboard')
    login_url     = 'login'

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        for field in form.fields.values():
            widget = field.widget
            existing = widget.attrs.get('class', '')
            if hasattr(widget, 'input_type') and widget.input_type == 'select':
                widget.attrs['class'] = f'{existing} form-select'.strip()
            else:
                widget.attrs['class'] = f'{existing} form-control'.strip()
        return form

    def form_valid(self, form):
        service = ReservaService()
        try:
            reserva = service.crear_reserva(
                estudiante   = form.cleaned_data['estudiante'],
                alojamiento  = form.cleaned_data['alojamiento'],
                fecha_inicio = form.cleaned_data['fecha_inicio'],
                fecha_fin    = form.cleaned_data['fecha_fin'],
            )
            messages.success(self.request, f'¡Reserva #{reserva.id} confirmada con éxito!')
        except Exception as e:
            messages.error(self.request, f'Error al crear la reserva: {e}')
            return self.form_invalid(form)
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Por favor corrige los errores del formulario.')
        return super().form_invalid(form)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _alojamientos_con_tipo(queryset):
    result = []
    for aloj in queryset:
        try:
            c = aloj.casa
            c.tipo = 'Casa'
            result.append(c)
            continue
        except Casa.DoesNotExist:
            pass
        try:
            a = aloj.apartamento
            a.tipo = 'Apartamento'
            result.append(a)
            continue
        except Apartamento.DoesNotExist:
            pass
        aloj.tipo = 'Alojamiento'
        result.append(aloj)
    return result
