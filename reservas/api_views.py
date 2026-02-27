
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import ValidationError

from .serializers import (
    CrearReservaSerializer, 
    ReservaSerializer,
    ReservaDetalleSerializer,
    AlojamientoSerializer
)
from .services import ReservaService
from .models import Estudiante, Alojamiento, Reserva

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



# RESUMEN DE CÓDIGOS HTTP USADOS:

# 200 OK: Consultas exitosas (GET)
# 201 CREATED: Recurso creado exitosamente (POST)
# 400 BAD REQUEST: Datos inválidos o error de validación
# 404 NOT FOUND: Recurso no encontrado
# 409 CONFLICT: Conflicto (ej: alojamiento no disponible) - puede usarse en lugar de 400
# 500 INTERNAL SERVER ERROR: Error inesperado del servidor