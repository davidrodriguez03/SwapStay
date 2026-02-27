
##Serializers - Django Rest Framework
##Manejo de entrada/salida de datos para la API REST



from rest_framework import serializers
from .models import Estudiante, Arrendador, Alojamiento, Reserva


class EstudianteSerializer(serializers.ModelSerializer):
    ##Serializer para Estudiante (solo lectura de datos básicos)
    nombre_completo = serializers.CharField(source='user.get_full_name', read_only=True)
    
    class Meta:
        model = Estudiante
        fields = ['id', 'codigo_estudiantil', 'institucion', 'verificado', 'nombre_completo']
        read_only_fields = ['id', 'verificado']


class ArrendadorSerializer(serializers.ModelSerializer):
    ##Serializer para Arrendador
    nombre_completo = serializers.CharField(source='user.get_full_name', read_only=True)
    
    class Meta:
        model = Arrendador
        fields = ['id', 'telefono', 'nombre_completo']
        read_only_fields = ['id']


class AlojamientoSerializer(serializers.ModelSerializer):
    ##Serializer para Alojamiento
    arrendador_nombre = serializers.CharField(source='arrendador.user.get_full_name', read_only=True)
    
    class Meta:
        model = Alojamiento
        fields = [
            'id', 'nombre', 'direccion', 'ciudad', 
            'precio_mensual', 'disponible', 'arrendador', 'arrendador_nombre'
        ]
        read_only_fields = ['id', 'disponible']


class ReservaSerializer(serializers.ModelSerializer):
    ##Serializer para Reserva (salida)
    ##Solo para mostrar datos de reservas existentes
    estudiante_nombre = serializers.CharField(source='estudiante.user.get_full_name', read_only=True)
    alojamiento_nombre = serializers.CharField(source='alojamiento.nombre', read_only=True)
    
    class Meta:
        model = Reserva
        fields = [
            'id', 'estudiante', 'estudiante_nombre',
            'alojamiento', 'alojamiento_nombre',
            'fecha_inicio', 'fecha_fin', 'estado',
            'monto_total', 'fecha_creacion'
        ]
        read_only_fields = ['id', 'estado', 'monto_total', 'fecha_creacion']


class CrearReservaSerializer(serializers.Serializer):
    ##Serializer para CREAR reserva (entrada)
    
    ##IMPORTANTE: Este serializer NO tiene lógica de negocio Solo valida que los datos de entrada tengan el formato correcto La lógica de negocio está en ReservaService
    
    estudiante_id = serializers.IntegerField(
        help_text="ID del estudiante que hace la reserva"
    )
    alojamiento_id = serializers.IntegerField(
        help_text="ID del alojamiento a reservar"
    )
    fecha_inicio = serializers.DateField(
        help_text="Fecha de inicio de la reserva (YYYY-MM-DD)"
    )
    fecha_fin = serializers.DateField(
        help_text="Fecha de fin de la reserva (YYYY-MM-DD)"
    )
    
    def validate(self, data):
    ##Validación básica de formato de datos
    ##NO incluye lógica de negocio (eso está en el Service)
      
        if data['fecha_inicio'] >= data['fecha_fin']:
            raise serializers.ValidationError(
                "La fecha de fin debe ser posterior a la fecha de inicio"
            )
        return data


class ReservaDetalleSerializer(serializers.ModelSerializer):
    ##Serializer detallado para ver una reserva específica
    estudiante = EstudianteSerializer(read_only=True)
    alojamiento = AlojamientoSerializer(read_only=True)
    
    class Meta:
        model = Reserva
        fields = '__all__'