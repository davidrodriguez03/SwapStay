import logging
from datetime import date

from django.db.models import Sum
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.core.exceptions import ValidationError

from .serializers import (
    CrearReservaSerializer,
    ReservaSerializer,
    ReservaDetalleSerializer,
    AlojamientoSerializer,
)
from .services import ReservaService
from .models import Estudiante, Alojamiento, Reserva
from .domain.adapters.currency_adapter import (
    get_currency_adapter,
    OpenERAPIAdapter,
    MockAdapter,
)

logger = logging.getLogger(__name__)

##API para crear una reserva
class CrearReservaAPIView(APIView):
    
    def post(self, request):

        # 1. Validar formato de datos de entrada
        serializer = CrearReservaSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'error': 'Datos inválidos', 'detalles': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 2. Obtener datos validados
        data = serializer.validated_data
        
        try:
            # 3. Obtener entidades (validar que existan)
            try:
                estudiante = Estudiante.objects.get(id=data['estudiante_id'])
            except Estudiante.DoesNotExist:
                return Response(
                    {'error': 'Estudiante no encontrado'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            try:
                alojamiento = Alojamiento.objects.get(id=data['alojamiento_id'])
            except Alojamiento.DoesNotExist:
                return Response(
                    {'error': 'Alojamiento no encontrado'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # 4. DELEGAR al Service Layer (aquí está la lógica de negocio)
            service = ReservaService()
            reserva = service.crear_reserva(
                estudiante=estudiante,
                alojamiento=alojamiento,
                fecha_inicio=data['fecha_inicio'],
                fecha_fin=data['fecha_fin']
            )
            
            # 5. Serializar respuesta
            output_serializer = ReservaSerializer(reserva)
            
            # 6. Retornar respuesta HTTP 201 Created
            return Response(
                {
                    'mensaje': 'Reserva creada exitosamente',
                    'reserva': output_serializer.data
                },
                status=status.HTTP_201_CREATED
            )
        
        except ValidationError as e:
            # Errores de validación de negocio (del Builder)
            return Response(
                {'error': 'Error de validación', 'detalles': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        except Exception as e:
            # Errores inesperados
            return Response(
                {'error': 'Error interno del servidor', 'detalles': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

##API para listar reservas
class ListarReservasAPIView(APIView):

    def get(self, request):
        ##Listar todas las reservas
        reservas = Reserva.objects.all().order_by('-fecha_creacion')
        serializer = ReservaSerializer(reservas, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

##API para ver detalle de una reserva
class DetalleReservaAPIView(APIView):

    def get(self, request, pk):
        ##Ver detalle de una reserva específica
        try:
            reserva = Reserva.objects.get(pk=pk)
            serializer = ReservaDetalleSerializer(reserva)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Reserva.DoesNotExist:
            return Response(
                {'error': 'Reserva no encontrada'},
                status=status.HTTP_404_NOT_FOUND
            )

##API para listar alojamientos disponibles
class ListarAlojamientosDisponiblesAPIView(APIView):
    def get(self, request):
        ##Listar alojamientos disponibles
        alojamientos = Alojamiento.objects.filter(disponible=True)
        serializer = AlojamientoSerializer(alojamientos, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)



class EstadisticasSistemaAPIView(APIView):
    """GET /api/v1/sistema/estadisticas/ — métricas agregadas del sistema.

    Usa el Adapter Pattern para convertir ingresos COP→USD:
    intenta MicroserviceMonedaAdapter, luego OpenERAPIAdapter, luego MockAdapter.
    """

    def get(self, request):
        hoy = date.today()

        # ── Métricas desde la BD ──────────────────────────────────────────────
        reservas_activas = Reserva.objects.filter(estado='CONFIRMADA').count()
        alojamientos_total = Alojamiento.objects.count()
        alojamientos_disponibles = Alojamiento.objects.filter(disponible=True).count()
        estudiantes_registrados = Estudiante.objects.count()

        ocupacion_pct = round(
            (alojamientos_total - alojamientos_disponibles) / alojamientos_total * 100
            if alojamientos_total > 0 else 0.0,
            1,
        )

        ingresos_mes_cop = float(
            Reserva.objects.filter(
                estado='CONFIRMADA',
                fecha_inicio__year=hoy.year,
                fecha_inicio__month=hoy.month,
            ).aggregate(total=Sum('monto_total'))['total'] or 0
        )

        # ── Conversión COP→USD vía Adapter Pattern ────────────────────────────
        ingresos_mes_usd = None
        fuente_tasa = None
        for adapter in (get_currency_adapter(), OpenERAPIAdapter(), MockAdapter()):
            try:
                resultado = adapter.cotizar(ingresos_mes_cop, 'COP', 'USD')
                ingresos_mes_usd = resultado.get('resultado')
                fuente_tasa = resultado.get('fuente', adapter.__class__.__name__)
                break
            except Exception as exc:
                logger.warning('[EstadisticasSistema] %s falló: %s', adapter.__class__.__name__, exc)

        return Response({
            'reservas_activas': reservas_activas,
            'alojamientos_disponibles': alojamientos_disponibles,
            'alojamientos_total': alojamientos_total,
            'estudiantes_registrados': estudiantes_registrados,
            'ocupacion_pct': ocupacion_pct,
            'ingresos_mes_cop': ingresos_mes_cop,
            'ingresos_mes_usd': ingresos_mes_usd,
            'fuente_tasa': fuente_tasa,
        })