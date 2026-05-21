from functools import wraps

from django.views.generic import FormView, TemplateView, ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404, render
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.db.models import Sum, Q

from .forms import (
    ReservaForm, RegistroEstudianteForm, RegistroArrendadorForm,
    PublicarAlojamientoForm, CancelarReservaForm,
)
from .services import ReservaService
from .models import Alojamiento, Casa, Apartamento, Reserva, Estudiante, Arrendador, AlojamientoImagen


# ── Decoradores ───────────────────────────────────────────────────────────────

def estudiante_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not hasattr(request.user, 'estudiante'):
            messages.error(request, 'Solo estudiantes pueden acceder a esta sección.')
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper


def arrendador_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not hasattr(request.user, 'arrendador'):
            messages.error(request, 'Solo arrendadores pueden acceder a esta sección.')
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper


# ── Landing ───────────────────────────────────────────────────────────────────

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

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['form_estudiante'] = RegistroEstudianteForm(prefix='est')
        ctx['form_arrendador'] = RegistroArrendadorForm(prefix='arr')
        return ctx

    def post(self, request):
        user_type = request.POST.get('user_type', 'estudiante')

        if user_type == 'estudiante':
            form = RegistroEstudianteForm(request.POST, prefix='est')
            if not form.is_valid():
                ctx = self.get_context_data()
                ctx['form_estudiante'] = form
                ctx['user_type_selected'] = 'estudiante'
                return self.render_to_response(ctx)

            data = form.cleaned_data
            if User.objects.filter(username=data['username']).exists():
                form.add_error('username', 'Ese nombre de usuario ya existe.')
                ctx = self.get_context_data()
                ctx['form_estudiante'] = form
                ctx['user_type_selected'] = 'estudiante'
                return self.render_to_response(ctx)

            user = User.objects.create_user(
                username=data['username'], email=data['email'],
                password=data['password1'],
                first_name=data['first_name'], last_name=data.get('last_name', ''),
            )
            Estudiante.objects.create(
                user=user,
                codigo_estudiantil=data['codigo_estudiantil'],
                institucion=data['institucion'],
                telefono=data.get('telefono', ''),
                verificado=True,
            )

        else:  # arrendador
            form = RegistroArrendadorForm(request.POST, prefix='arr')
            if not form.is_valid():
                ctx = self.get_context_data()
                ctx['form_arrendador'] = form
                ctx['user_type_selected'] = 'arrendador'
                return self.render_to_response(ctx)

            data = form.cleaned_data
            if User.objects.filter(username=data['username']).exists():
                form.add_error('username', 'Ese nombre de usuario ya existe.')
                ctx = self.get_context_data()
                ctx['form_arrendador'] = form
                ctx['user_type_selected'] = 'arrendador'
                return self.render_to_response(ctx)

            user = User.objects.create_user(
                username=data['username'], email=data['email'],
                password=data['password1'],
                first_name=data['first_name'], last_name=data.get('last_name', ''),
            )
            Arrendador.objects.create(
                user=user,
                telefono=data['telefono'],
                documento_identidad=data.get('documento_identidad', ''),
            )

        login(request, user)
        messages.success(request, f'¡Bienvenido/a, {user.first_name or user.username}!')
        return redirect('dashboard')


class LogoutView(TemplateView):
    def post(self, request):
        logout(request)
        return redirect('landing')


# ── Dashboard (router por rol) ────────────────────────────────────────────────

class DashboardView(LoginRequiredMixin, TemplateView):
    login_url = 'login'

    def get_template_names(self):
        if hasattr(self.request.user, 'arrendador'):
            return ['dashboard_arrendador.html']
        return ['dashboard_estudiante.html']

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user

        if hasattr(user, 'arrendador'):
            arrendador = user.arrendador
            alojamientos = Alojamiento.objects.filter(arrendador=arrendador).prefetch_related('imagenes')
            reservas_recibidas = Reserva.objects.filter(
                alojamiento__arrendador=arrendador
            ).select_related('estudiante__user', 'alojamiento').order_by('-fecha_creacion')
            ctx.update({
                'arrendador': arrendador,
                'alojamientos': alojamientos,
                'alojamientos_count': alojamientos.count(),
                'alojamientos_disponibles': alojamientos.filter(disponible=True).count(),
                'reservas_recibidas': reservas_recibidas,
                'reservas_count': reservas_recibidas.count(),
            })
        else:
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
                'estudiante': estudiante,
                'reservas': reservas,
                'reservas_count': reservas.count(),
                'reservas_confirmadas': reservas.filter(estado='CONFIRMADA').count(),
                'reservas_pendientes': reservas.filter(estado='PENDIENTE').count(),
                'monto_total': monto,
            })

        return ctx


# ── Catálogo ──────────────────────────────────────────────────────────────────

class CatalogoView(TemplateView):
    template_name = 'alojamientos/catalogo.html'

    def get_context_data(self, **kwargs):
        ctx  = super().get_context_data(**kwargs)
        qs   = Alojamiento.objects.select_related('arrendador__user').prefetch_related('imagenes')
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
            try:
                aloj = aloj.apartamento
                tipo = 'Apartamento'
            except Apartamento.DoesNotExist:
                tipo = 'Alojamiento'

        es_estudiante = (
            self.request.user.is_authenticated
            and hasattr(self.request.user, 'estudiante')
        )
        ctx['alojamiento'] = aloj
        ctx['tipo'] = tipo
        ctx['es_estudiante'] = es_estudiante
        ctx['imagenes'] = aloj.imagenes.all()
        return ctx


# ── Crear reserva ─────────────────────────────────────────────────────────────

class CrearReservaView(LoginRequiredMixin, TemplateView):
    template_name = 'reservas/crear.html'
    login_url = 'login'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not hasattr(request.user, 'estudiante'):
            messages.error(request, 'Solo estudiantes pueden crear reservas.')
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        alojamiento_id = self.request.GET.get('alojamiento')
        alojamiento_preseleccionado = None
        if alojamiento_id:
            try:
                alojamiento_preseleccionado = Alojamiento.objects.get(pk=alojamiento_id, disponible=True)
            except Alojamiento.DoesNotExist:
                pass

        ctx['form'] = ReservaForm(initial={'alojamiento': alojamiento_id} if alojamiento_id else {})
        ctx['alojamiento_preseleccionado'] = alojamiento_preseleccionado
        ctx['estudiante'] = self.request.user.estudiante
        return ctx

    def post(self, request, *args, **kwargs):
        form = ReservaForm(request.POST)
        if not form.is_valid():
            ctx = self.get_context_data()
            ctx['form'] = form
            return self.render_to_response(ctx)

        service = ReservaService()
        try:
            reserva = service.crear_reserva(
                estudiante   = request.user.estudiante,
                alojamiento  = form.cleaned_data['alojamiento'],
                fecha_inicio = form.cleaned_data['fecha_inicio'],
                fecha_fin    = form.cleaned_data['fecha_fin'],
            )
            messages.success(
                request,
                f'¡Reserva #{reserva.id} confirmada! Total: ${reserva.monto_total:,.0f} COP'
            )
        except Exception as e:
            messages.error(request, f'Error al crear la reserva: {e}')
            ctx = self.get_context_data()
            ctx['form'] = form
            return self.render_to_response(ctx)
        return redirect('dashboard')


# ── Cancelar reserva ──────────────────────────────────────────────────────────

class CancelarReservaView(LoginRequiredMixin, TemplateView):
    template_name = 'reservas/cancelar.html'
    login_url = 'login'

    def _get_reserva_y_rol(self, request, pk):
        reserva = get_object_or_404(Reserva, pk=pk)
        es_arrendador = (
            hasattr(request.user, 'arrendador')
            and reserva.alojamiento.arrendador == request.user.arrendador
        )
        es_estudiante = (
            hasattr(request.user, 'estudiante')
            and reserva.estudiante == request.user.estudiante
        )
        return reserva, es_arrendador, es_estudiante

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        reserva, es_arrendador, es_estudiante = self._get_reserva_y_rol(
            self.request, kwargs['pk']
        )
        if not (es_arrendador or es_estudiante):
            return ctx
        ctx['reserva'] = reserva
        ctx['form'] = CancelarReservaForm()
        return ctx

    def post(self, request, *args, **kwargs):
        reserva, es_arrendador, es_estudiante = self._get_reserva_y_rol(request, kwargs['pk'])
        if not (es_arrendador or es_estudiante):
            messages.error(request, 'No tienes permiso para cancelar esta reserva.')
            return redirect('dashboard')

        if not reserva.puede_cancelarse():
            messages.error(request, 'Esta reserva no puede cancelarse (ya está activa o cancelada).')
            return redirect('dashboard')

        form = CancelarReservaForm(request.POST)
        if not form.is_valid():
            ctx = {'reserva': reserva, 'form': form}
            return self.render_to_response(ctx)

        reserva.estado = 'CANCELADA'
        reserva.motivo_cancelacion = form.cleaned_data['motivo']
        reserva.cancelada_por = 'arrendador' if es_arrendador else 'estudiante'
        reserva.save(update_fields=['estado', 'motivo_cancelacion', 'cancelada_por'])

        # Liberar el alojamiento
        aloj = reserva.alojamiento
        aloj.disponible = True
        aloj.save(update_fields=['disponible'])

        messages.success(request, f'Reserva #{reserva.id} cancelada correctamente.')
        return redirect('dashboard')


# ── Renovar reserva ───────────────────────────────────────────────────────────

class RenovarReservaView(LoginRequiredMixin, TemplateView):
    login_url = 'login'

    def post(self, request, pk, *args, **kwargs):
        reserva = get_object_or_404(
            Reserva, pk=pk, estudiante=request.user.estudiante
        )

        if not reserva.esta_por_vencer():
            messages.error(request, 'Solo puedes renovar reservas que estén por vencer (≤ 7 días).')
            return redirect('dashboard')

        duracion = (reserva.fecha_fin - reserva.fecha_inicio).days
        nueva_inicio = reserva.fecha_fin
        from datetime import timedelta
        nueva_fin = nueva_inicio + timedelta(days=duracion)

        service = ReservaService()
        try:
            nueva = service.crear_reserva(
                estudiante   = request.user.estudiante,
                alojamiento  = reserva.alojamiento,
                fecha_inicio = nueva_inicio,
                fecha_fin    = nueva_fin,
            )
            nueva.renovacion_de = reserva
            nueva.save(update_fields=['renovacion_de'])
            messages.success(request, f'Contrato renovado. Nueva reserva #{nueva.id} creada.')
        except Exception as e:
            messages.error(request, f'No se pudo renovar: {e}')

        return redirect('dashboard')


# ── Publicar alojamiento ──────────────────────────────────────────────────────

class PublicarAlojamientoView(LoginRequiredMixin, TemplateView):
    template_name = 'alojamientos/publicar.html'
    login_url = 'login'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not hasattr(request.user, 'arrendador'):
            messages.error(request, 'Solo arrendadores pueden publicar alojamientos.')
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['form'] = PublicarAlojamientoForm()
        return ctx

    def post(self, request, *args, **kwargs):
        form = PublicarAlojamientoForm(request.POST)
        if not form.is_valid():
            return self.render_to_response({'form': form})

        d = form.cleaned_data
        tipo = d['tipo']
        arrendador = request.user.arrendador

        base_kwargs = dict(
            arrendador=arrendador,
            nombre=d['nombre'],
            direccion=d['direccion'],
            ciudad=d['ciudad'],
            precio_mensual=d['precio_mensual'],
            descripcion_completa=d.get('descripcion_completa', ''),
            latitud=d.get('latitud'),
            longitud=d.get('longitud'),
            disponible=True,
        )

        if tipo == 'casa':
            alojamiento = Casa.objects.create(
                **base_kwargs,
                numero_pisos=d.get('numero_pisos') or 1,
                tiene_patio=d.get('tiene_patio', False),
                tiene_garaje=d.get('tiene_garaje', False),
            )
        elif tipo == 'apartamento':
            alojamiento = Apartamento.objects.create(
                **base_kwargs,
                numero_piso=d.get('numero_piso') or 1,
                tiene_ascensor=d.get('tiene_ascensor', False),
                tiene_porteria=d.get('tiene_porteria', False),
            )
        else:
            alojamiento = Alojamiento.objects.create(**base_kwargs)

        # Guardar imágenes subidas
        imagenes = request.FILES.getlist('imagenes')
        for i, img_file in enumerate(imagenes):
            AlojamientoImagen.objects.create(
                alojamiento=alojamiento,
                imagen=img_file,
                orden=i,
                es_principal=(i == 0),
            )

        messages.success(request, f'Alojamiento "{alojamiento.nombre}" publicado exitosamente.')
        return redirect('dashboard')


# ── Editar alojamiento ────────────────────────────────────────────────────────

@arrendador_required
def editar_alojamiento(request, pk):
    alojamiento = get_object_or_404(Alojamiento, pk=pk)

    if alojamiento.arrendador != request.user.arrendador:
        messages.error(request, 'No tienes permiso para editar este alojamiento.')
        return redirect('dashboard')

    if request.method == 'POST':
        alojamiento.nombre = request.POST.get('nombre', alojamiento.nombre).strip()
        alojamiento.direccion = request.POST.get('direccion', alojamiento.direccion).strip()
        alojamiento.ciudad = request.POST.get('ciudad', alojamiento.ciudad).strip()
        precio = request.POST.get('precio_mensual', '').strip()
        if precio:
            alojamiento.precio_mensual = precio
        alojamiento.descripcion_completa = request.POST.get('descripcion_completa', '').strip()
        alojamiento.latitud = request.POST.get('latitud') or None
        alojamiento.longitud = request.POST.get('longitud') or None
        alojamiento.disponible = request.POST.get('disponible') == 'on'
        alojamiento.save()

        nuevas = request.FILES.getlist('imagenes')
        count = alojamiento.imagenes.count()
        for i, img_file in enumerate(nuevas):
            AlojamientoImagen.objects.create(
                alojamiento=alojamiento,
                imagen=img_file,
                orden=count + i,
                es_principal=(count == 0 and i == 0),
            )

        messages.success(request, f'Alojamiento "{alojamiento.nombre}" actualizado correctamente.')
        return redirect('dashboard')

    return render(request, 'alojamientos/editar.html', {
        'alojamiento': alojamiento,
        'imagenes': alojamiento.imagenes.all(),
    })


# ── Eliminar alojamiento ──────────────────────────────────────────────────────

@arrendador_required
def eliminar_alojamiento(request, pk):
    alojamiento = get_object_or_404(Alojamiento, pk=pk)

    if alojamiento.arrendador != request.user.arrendador:
        messages.error(request, 'No tienes permiso para eliminar este alojamiento.')
        return redirect('dashboard')

    reservas_activas = alojamiento.reserva_set.filter(
        estado__in=['CONFIRMADA', 'PENDIENTE']
    ).count()
    if reservas_activas > 0:
        messages.error(
            request,
            f'No puedes eliminar este alojamiento: tiene {reservas_activas} reserva(s) activa(s).'
        )
        return redirect('dashboard')

    if request.method == 'POST':
        nombre = alojamiento.nombre
        alojamiento.delete()
        messages.success(request, f'Alojamiento "{nombre}" eliminado correctamente.')
        return redirect('dashboard')

    return render(request, 'alojamientos/confirmar_eliminar.html', {'alojamiento': alojamiento})


# ── Eliminar imagen individual ────────────────────────────────────────────────

def eliminar_imagen_alojamiento(request, pk):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'No autenticado'}, status=401)
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    imagen = get_object_or_404(AlojamientoImagen, pk=pk)
    alojamiento = imagen.alojamiento

    if not hasattr(request.user, 'arrendador') or alojamiento.arrendador != request.user.arrendador:
        return JsonResponse({'error': 'No autorizado'}, status=403)

    era_principal = imagen.es_principal
    imagen.delete()

    if era_principal:
        primera = alojamiento.imagenes.first()
        if primera:
            primera.es_principal = True
            primera.save(update_fields=['es_principal'])

    return JsonResponse({'success': True})


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
