"""
API pública de SwapStay — endpoints para integración con equipos aliados.
No requieren autenticación. Versión: /api/v1/
"""
import logging
from datetime import date, datetime

from django.contrib.auth.models import User
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from .models import Alojamiento, Reserva, Estudiante
from .serializers import AlojamientoSerializer, ReservaSerializer
from .domain.adapters.currency_adapter import get_currency_adapter, OpenERAPIAdapter, MockAdapter

logger = logging.getLogger(__name__)


# ── helpers ───────────────────────────────────────────────────────────────────

def _cop_a_usd(monto_cop: float) -> float | None:
    """Convierte COP a USD usando la cadena de adaptadores con fallback."""
    for adapter in (get_currency_adapter(), OpenERAPIAdapter(), MockAdapter()):
        try:
            resultado = adapter.cotizar(monto_cop, 'COP', 'USD')
            return resultado.get('resultado')
        except Exception as exc:
            logger.warning('[api_public] %s falló: %s', adapter.__class__.__name__, exc)
    return None


def _generar_codigo(reserva) -> str:
    """Genera código de confirmación RSV-YYYYMMDD-### a partir de fecha_creacion + id."""
    return f"RSV-{reserva.fecha_creacion.strftime('%Y%m%d')}-{reserva.id:03d}"


def _id_desde_codigo(codigo: str):
    """Extrae el ID de reserva desde un código RSV-YYYYMMDD-###. Retorna None si es inválido."""
    try:
        partes = codigo.upper().split('-')
        if len(partes) != 3 or partes[0] != 'RSV':
            return None
        return int(partes[2])
    except (ValueError, IndexError):
        return None


# ── 1. GET /api/v1/alojamientos/disponibles/ ─────────────────────────────────

@api_view(['GET'])
def alojamientos_disponibles(request):
    """Lista alojamientos disponibles con filtros opcionales.

    Query params:
      - ciudad (str): filtro parcial por ciudad
      - precio_max (number): precio mensual máximo en COP
      - capacidad_min (int): ignorado — el modelo no tiene campo capacidad
    """
    qs = Alojamiento.objects.filter(disponible=True)

    ciudad = request.query_params.get('ciudad', '').strip()
    if ciudad:
        qs = qs.filter(ciudad__icontains=ciudad)

    precio_max = request.query_params.get('precio_max')
    if precio_max:
        try:
            qs = qs.filter(precio_mensual__lte=float(precio_max))
        except ValueError:
            return Response(
                {'error': 'precio_max debe ser un número'},
                status=status.HTTP_400_BAD_REQUEST,
            )

    serializer = AlojamientoSerializer(qs, many=True)
    return Response({
        'total': qs.count(),
        'alojamientos': serializer.data,
    })


# ── 2. POST /api/v1/alojamientos/verificar-disponibilidad/ ───────────────────

@api_view(['POST'])
def verificar_disponibilidad(request):
    """Verifica si un alojamiento está libre en las fechas solicitadas.

    Body: { alojamiento_id, fecha_inicio (YYYY-MM-DD), fecha_fin (YYYY-MM-DD) }
    """
    alojamiento_id = request.data.get('alojamiento_id')
    fecha_inicio_str = request.data.get('fecha_inicio')
    fecha_fin_str = request.data.get('fecha_fin')

    if not all([alojamiento_id, fecha_inicio_str, fecha_fin_str]):
        return Response(
            {'error': 'Se requieren: alojamiento_id, fecha_inicio, fecha_fin'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    alojamiento = get_object_or_404(Alojamiento, pk=alojamiento_id)

    try:
        fecha_inicio = date.fromisoformat(fecha_inicio_str)
        fecha_fin = date.fromisoformat(fecha_fin_str)
    except ValueError:
        return Response(
            {'error': 'Formato de fecha inválido. Use YYYY-MM-DD'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if fecha_fin <= fecha_inicio:
        return Response(
            {'error': 'fecha_fin debe ser posterior a fecha_inicio'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Verificar conflictos con reservas confirmadas existentes
    conflicto = Reserva.objects.filter(
        alojamiento=alojamiento,
        estado='CONFIRMADA',
    ).filter(
        Q(fecha_inicio__lt=fecha_fin) & Q(fecha_fin__gt=fecha_inicio)
    ).exists()

    noches = (fecha_fin - fecha_inicio).days
    duracion_meses = noches / 30
    precio_total_cop = float(alojamiento.precio_mensual) * duracion_meses
    precio_total_usd = _cop_a_usd(precio_total_cop)

    if conflicto or not alojamiento.disponible:
        return Response({
            'disponible': False,
            'mensaje': 'El alojamiento no está disponible en las fechas solicitadas',
            'alojamiento_id': alojamiento.id,
            'alojamiento_nombre': alojamiento.nombre,
        })

    return Response({
        'disponible': True,
        'mensaje': 'Alojamiento disponible para las fechas solicitadas',
        'alojamiento_id': alojamiento.id,
        'alojamiento_nombre': alojamiento.nombre,
        'ciudad': alojamiento.ciudad,
        'noches': noches,
        'precio_mensual_cop': float(alojamiento.precio_mensual),
        'precio_total_cop': round(precio_total_cop, 2),
        'precio_total_usd': precio_total_usd,
    })


# ── 3. POST /api/v1/reservas/crear/ ──────────────────────────────────────────

@api_view(['POST'])
def crear_reserva_externa(request):
    """Crea una reserva desde una integración externa.

    Body: {
      alojamiento_id, estudiante_email, estudiante_nombre,
      fecha_inicio (YYYY-MM-DD), fecha_fin (YYYY-MM-DD),
      num_huespedes (opcional), notas (opcional)
    }
    """
    data = request.data

    campos_requeridos = ['alojamiento_id', 'estudiante_email', 'estudiante_nombre',
                         'fecha_inicio', 'fecha_fin']
    faltantes = [c for c in campos_requeridos if not data.get(c)]
    if faltantes:
        return Response(
            {'error': f'Campos requeridos faltantes: {", ".join(faltantes)}'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    alojamiento = get_object_or_404(Alojamiento, pk=data['alojamiento_id'])

    try:
        fecha_inicio = date.fromisoformat(data['fecha_inicio'])
        fecha_fin = date.fromisoformat(data['fecha_fin'])
    except ValueError:
        return Response(
            {'error': 'Formato de fecha inválido. Use YYYY-MM-DD'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Obtener o crear User + Estudiante a partir del email
    email = data['estudiante_email'].strip().lower()
    nombre_completo = data['estudiante_nombre'].strip().split(' ', 1)
    first_name = nombre_completo[0]
    last_name = nombre_completo[1] if len(nombre_completo) > 1 else ''

    user, _ = User.objects.get_or_create(
        email=email,
        defaults={
            'username': email.split('@')[0][:150],
            'first_name': first_name,
            'last_name': last_name,
        },
    )
    estudiante, _ = Estudiante.objects.get_or_create(
        user=user,
        defaults={
            'codigo_estudiantil': f'EXT-{user.id:04d}',
            'institucion': 'Institución externa',
            'verificado': True,
        },
    )
    # Garantizar que el estudiante esté verificado para que el Builder lo acepte
    if not estudiante.verificado:
        estudiante.verificado = True
        estudiante.save(update_fields=['verificado'])

    # Construir la reserva usando ReservaBuilder (patrón Builder)
    from domain.builders import ReservaBuilder
    try:
        reserva = (ReservaBuilder()
                   .para_estudiante(estudiante)
                   .en_alojamiento(alojamiento)
                   .en_fechas(fecha_inicio, fecha_fin)
                   .build())
        reserva.save()

        # Confirmar y marcar alojamiento
        reserva.estado = 'CONFIRMADA'
        reserva.save(update_fields=['estado'])
        alojamiento.disponible = False
        alojamiento.save(update_fields=['disponible'])

    except Exception as exc:
        return Response(
            {'error': str(exc)},
            status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    # Disparar tarea Celery asíncrona
    try:
        from .tasks import enviar_confirmacion_reserva
        enviar_confirmacion_reserva.delay(reserva.id)
    except Exception as exc:
        logger.warning('[api_public] No se pudo encolar tarea Celery: %s', exc)

    codigo_confirmacion = _generar_codigo(reserva)
    precio_total_usd = _cop_a_usd(float(reserva.monto_total))

    return Response({
        'success': True,
        'reserva_id': reserva.id,
        'codigo_confirmacion': codigo_confirmacion,
        'precio_total_cop': float(reserva.monto_total),
        'precio_total_usd': precio_total_usd,
        'mensaje': f'Reserva creada exitosamente. Código: {codigo_confirmacion}',
    }, status=status.HTTP_201_CREATED)


# ── 4. GET /api/v1/reservas/<codigo>/ ────────────────────────────────────────

@api_view(['GET'])
def consultar_reserva(request, codigo):
    """Consulta una reserva por su código de confirmación (RSV-YYYYMMDD-###)."""
    reserva_id = _id_desde_codigo(codigo)
    if reserva_id is None:
        return Response(
            {'error': f'Código de confirmación inválido: {codigo}'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    reserva = get_object_or_404(Reserva, pk=reserva_id)

    # Verificar que el código generado coincida (previene colisiones de ID)
    if _generar_codigo(reserva) != codigo.upper():
        return Response(
            {'error': 'Código de confirmación no corresponde a ninguna reserva'},
            status=status.HTTP_404_NOT_FOUND,
        )

    serializer = ReservaSerializer(reserva)
    return Response({
        'codigo_confirmacion': codigo.upper(),
        'reserva': serializer.data,
    })
