import os
from abc import ABC, abstractmethod


# Interfaz base (todos los notificadores deben implementarla)
class NotificadorBase(ABC):  
    @abstractmethod
    def enviar_confirmacion(self, reserva):
        """Envía confirmación de reserva"""
        pass


# Implementación para DESARROLLO (imprime en consola)
class ConsoleNotificador(NotificadorBase):   
    def enviar_confirmacion(self, reserva):
        print("\n" + "="*50)
        print("CONFIRMACIÓN DE RESERVA")
        print("="*50)
        print(f"Estudiante: {reserva.estudiante}")
        print(f"Alojamiento: {reserva.alojamiento}")
        print(f"Fechas: {reserva.fecha_inicio} a {reserva.fecha_fin}")
        print(f"Monto: ${reserva.monto_total}")
        print("="*50 + "\n")


# Implementación para PRODUCCIÓN (email real - simplificado)
class EmailNotificador(NotificadorBase):
    def enviar_confirmacion(self, reserva):
        # Aquí iría la lógica real de envío
        # Por ahora solo un ejemplo
        print(f"Email enviado a {reserva.estudiante.user.email}")


# FACTORY - Decide cuál notificador usar
class NotificadorFactory:
    @staticmethod
    def crear():
        """Crea el notificador según ENV_TYPE"""
        env_type = os.environ.get('ENV_TYPE', 'development')
        
        if env_type == 'production':
            return EmailNotificador()
        else:
            return ConsoleNotificador()