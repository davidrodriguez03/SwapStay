import os
import uuid
import logging
from abc import ABC, abstractmethod
from datetime import datetime

import requests
from flask import Flask, jsonify, request

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

FLASK_ENV = os.environ.get('FLASK_ENV', 'development')


# ── Adapter Pattern ───────────────────────────────────────────────────────────

class NotificacionAdapter(ABC):
    @abstractmethod
    def enviar_email(self, destinatario: str, asunto: str, cuerpo: str) -> dict:
        pass


class ConsoleAdapter(NotificacionAdapter):
    def enviar_email(self, destinatario: str, asunto: str, cuerpo: str) -> dict:
        message_id = str(uuid.uuid4())
        print('\n' + '=' * 60)
        print(f'EMAIL (simulado en consola) — {datetime.now().isoformat()}')
        print(f'  Para:   {destinatario}')
        print(f'  Asunto: {asunto}')
        print(f'  ID:     {message_id}')
        print('─' * 60)
        print(cuerpo)
        print('=' * 60 + '\n')
        return {'message_id': message_id, 'canal': 'console'}


class SendGridAdapter(NotificacionAdapter):
    def __init__(self):
        self.api_key = os.environ.get('SENDGRID_API_KEY', '')
        self.from_email = os.environ.get('SENDGRID_FROM_EMAIL', 'noreply@swapstay.com')

    def enviar_email(self, destinatario: str, asunto: str, cuerpo: str) -> dict:
        if not self.api_key:
            logger.warning('[SendGrid] API key no configurada — fallback a consola')
            return ConsoleAdapter().enviar_email(destinatario, asunto, cuerpo)

        try:
            response = requests.post(
                'https://api.sendgrid.com/v3/mail/send',
                headers={
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json',
                },
                json={
                    'personalizations': [{'to': [{'email': destinatario}]}],
                    'from': {'email': self.from_email},
                    'subject': asunto,
                    'content': [{'type': 'text/plain', 'value': cuerpo}],
                },
                timeout=10,
            )
            message_id = response.headers.get('X-Message-Id', str(uuid.uuid4()))
            logger.info(f'[SendGrid] Enviado → {destinatario} (status {response.status_code})')
            return {'message_id': message_id, 'canal': 'sendgrid'}
        except Exception as exc:
            logger.error(f'[SendGrid] Error: {exc} — fallback a consola')
            return ConsoleAdapter().enviar_email(destinatario, asunto, cuerpo)


def get_adapter() -> NotificacionAdapter:
    if FLASK_ENV == 'production':
        return SendGridAdapter()
    return ConsoleAdapter()


# ── Plantillas de mensajes ────────────────────────────────────────────────────

PLANTILLAS = {
    'confirmacion_reserva': {
        'asunto': 'SwapStay — Reserva #{reserva_id} confirmada',
        'cuerpo': (
            'Hola {estudiante_nombre},\n\n'
            'Tu reserva ha sido confirmada exitosamente.\n\n'
            'Alojamiento: {alojamiento_nombre} — {ciudad}\n'
            'Fechas: {fecha_inicio} → {fecha_fin}\n'
            'Monto total: ${monto_total:,.0f} COP\n\n'
            'Bienvenido a SwapStay. Que disfrutes tu estadía.\n\n'
            'El equipo de SwapStay'
        ),
    },
    'recordatorio_inicio': {
        'asunto': 'SwapStay — Tu estadía comienza en {dias_restantes} días',
        'cuerpo': (
            'Hola {estudiante_nombre},\n\n'
            'Te recordamos que tu reserva en {alojamiento_nombre} ({ciudad})\n'
            'comienza en {dias_restantes} días (fecha de inicio: {fecha_inicio}).\n\n'
            'Prepárate para tu nueva experiencia.\n\n'
            'El equipo de SwapStay'
        ),
    },
    'cancelacion_reserva': {
        'asunto': 'SwapStay — Reserva #{reserva_id} cancelada',
        'cuerpo': (
            'Hola {estudiante_nombre},\n\n'
            'Tu reserva #{reserva_id} en {alojamiento_nombre} ha sido cancelada.\n\n'
            'Si tienes preguntas, responde a este correo.\n\n'
            'El equipo de SwapStay'
        ),
    },
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def error_response(status_code: int, code: str, message: str, details=None):
    payload = {'error': {'code': code, 'message': message}}
    if details:
        payload['error']['details'] = details
    return jsonify(payload), status_code


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get('/health')
def health():
    return jsonify({
        'status': 'ok',
        'service': 'flask-notificaciones',
        'env': FLASK_ENV,
        'adapter': 'SendGridAdapter' if FLASK_ENV == 'production' else 'ConsoleAdapter',
    }), 200


@app.post('/api/v2/notificaciones/email')
def enviar_email():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return error_response(400, 'INVALID_PAYLOAD', 'Se esperaba un objeto JSON')

    for campo in ('destinatario', 'tipo', 'datos'):
        if campo not in data:
            return error_response(400, 'MISSING_FIELD', f'Campo requerido: {campo}')

    tipo = data['tipo']
    if tipo not in PLANTILLAS:
        return error_response(
            400, 'TIPO_INVALIDO',
            f'Tipo desconocido: {tipo}',
            {'tipos_validos': list(PLANTILLAS)},
        )

    plantilla = PLANTILLAS[tipo]
    datos = data.get('datos', {})

    try:
        asunto = plantilla['asunto'].format(**datos)
        cuerpo = plantilla['cuerpo'].format(**datos)
    except KeyError as exc:
        return error_response(400, 'DATOS_INCOMPLETOS', f'Falta campo en datos: {exc}')

    adapter = get_adapter()
    resultado = adapter.enviar_email(data['destinatario'], asunto, cuerpo)

    logger.info(
        f'[Notificaciones] tipo={tipo} → {data["destinatario"]} '
        f'canal={resultado["canal"]} id={resultado["message_id"]}'
    )

    return jsonify({
        'status': 'success',
        'tipo': tipo,
        'destinatario': data['destinatario'],
        'message_id': resultado['message_id'],
        'canal': resultado['canal'],
        'enviado_at': datetime.now().isoformat(),
    }), 200


@app.get('/api/v2/notificaciones/tipos')
def listar_tipos():
    return jsonify({'tipos': list(PLANTILLAS.keys())}), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002)
