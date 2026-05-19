import logging
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from flask import Flask, jsonify, request

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MIN_DIAS = 30
MAX_DIAS = 365
PRECIO_MINIMO_COP = Decimal('100000')


def error_response(status_code: int, code: str, message: str, details=None):
    payload = {'error': {'code': code, 'message': message}}
    if details:
        payload['error']['details'] = details
    return jsonify(payload), status_code


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get('/health')
def health():
    return jsonify({'status': 'ok', 'service': 'flask-validaciones'}), 200


@app.post('/api/v2/validaciones/reserva')
def validar_reserva():
    """
    Valida las reglas de negocio de una reserva antes de crearla.
    Body: { fecha_inicio, fecha_fin, precio_mensual, alojamiento_id? }
    """
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return error_response(400, 'INVALID_PAYLOAD', 'Se esperaba un objeto JSON')

    errores = []
    advertencias = []

    # ── Validar fechas ─────────────────────────────────────────────────────────
    fecha_inicio_raw = data.get('fecha_inicio')
    fecha_fin_raw = data.get('fecha_fin')

    if not fecha_inicio_raw:
        errores.append({'campo': 'fecha_inicio', 'mensaje': 'La fecha de inicio es requerida'})
    if not fecha_fin_raw:
        errores.append({'campo': 'fecha_fin', 'mensaje': 'La fecha de fin es requerida'})

    fecha_inicio = fecha_fin = None
    if fecha_inicio_raw:
        try:
            fecha_inicio = date.fromisoformat(str(fecha_inicio_raw))
        except ValueError:
            errores.append({'campo': 'fecha_inicio', 'mensaje': 'Formato inválido (esperado YYYY-MM-DD)'})

    if fecha_fin_raw:
        try:
            fecha_fin = date.fromisoformat(str(fecha_fin_raw))
        except ValueError:
            errores.append({'campo': 'fecha_fin', 'mensaje': 'Formato inválido (esperado YYYY-MM-DD)'})

    if fecha_inicio and fecha_fin:
        hoy = date.today()

        if fecha_inicio < hoy:
            errores.append({'campo': 'fecha_inicio', 'mensaje': 'La fecha de inicio debe ser en el futuro'})

        if fecha_fin <= fecha_inicio:
            errores.append({'campo': 'fecha_fin', 'mensaje': 'La fecha de fin debe ser posterior a la de inicio'})
        else:
            duracion_dias = (fecha_fin - fecha_inicio).days

            if duracion_dias < MIN_DIAS:
                errores.append({
                    'campo': 'duracion',
                    'mensaje': f'La estadía mínima es {MIN_DIAS} días (solicitado: {duracion_dias})',
                })

            if duracion_dias > MAX_DIAS:
                errores.append({
                    'campo': 'duracion',
                    'mensaje': f'La estadía máxima es {MAX_DIAS} días (solicitado: {duracion_dias})',
                })

            if MIN_DIAS <= duracion_dias <= MAX_DIAS and duracion_dias > 180:
                advertencias.append({
                    'campo': 'duracion',
                    'mensaje': 'Estadía mayor a 6 meses — verifica condiciones contractuales especiales',
                })

    # ── Validar precio ─────────────────────────────────────────────────────────
    precio_raw = data.get('precio_mensual')
    if precio_raw is None:
        errores.append({'campo': 'precio_mensual', 'mensaje': 'El precio mensual es requerido'})
    else:
        try:
            precio = Decimal(str(precio_raw))
            if precio <= 0:
                errores.append({'campo': 'precio_mensual', 'mensaje': 'El precio debe ser un valor positivo'})
            elif precio < PRECIO_MINIMO_COP:
                advertencias.append({
                    'campo': 'precio_mensual',
                    'mensaje': f'Precio inusualmente bajo (mínimo recomendado: ${PRECIO_MINIMO_COP:,.0f} COP)',
                })
        except InvalidOperation:
            errores.append({'campo': 'precio_mensual', 'mensaje': 'Valor numérico inválido'})

    # ── Resultado ──────────────────────────────────────────────────────────────
    valido = len(errores) == 0
    logger.info(
        f'[Validaciones] reserva valido={valido} '
        f'errores={len(errores)} advertencias={len(advertencias)}'
    )

    return jsonify({
        'valido': valido,
        'errores': errores,
        'advertencias': advertencias,
        'validado_at': datetime.now().isoformat(),
    }), 200 if valido else 422


@app.post('/api/v2/validaciones/estudiante')
def validar_estudiante():
    """
    Valida los datos de un estudiante antes de registrarlo.
    Body: { email, nombre, universidad? }
    """
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return error_response(400, 'INVALID_PAYLOAD', 'Se esperaba un objeto JSON')

    errores = []
    advertencias = []

    email = data.get('email', '')
    if not email or '@' not in str(email):
        errores.append({'campo': 'email', 'mensaje': 'Email inválido o ausente'})

    nombre = data.get('nombre', '')
    if not nombre or len(str(nombre).strip()) < 2:
        errores.append({'campo': 'nombre', 'mensaje': 'Nombre muy corto (mínimo 2 caracteres)'})

    if not data.get('universidad'):
        advertencias.append({
            'campo': 'universidad',
            'mensaje': 'Se recomienda especificar la universidad para mejor experiencia',
        })

    valido = len(errores) == 0
    return jsonify({
        'valido': valido,
        'errores': errores,
        'advertencias': advertencias,
        'validado_at': datetime.now().isoformat(),
    }), 200 if valido else 422


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5004)
