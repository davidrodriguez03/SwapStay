import os
import logging

from flask import Flask, jsonify, request

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'db'),
    'port': int(os.environ.get('DB_PORT', 5432)),
    'dbname': os.environ.get('DB_NAME', 'swapstay'),
    'user': os.environ.get('DB_USER', 'swapstay'),
    'password': os.environ.get('DB_PASSWORD', 'swapstay'),
}


def get_connection():
    import psycopg2
    return psycopg2.connect(**DB_CONFIG)


def error_response(status_code: int, code: str, message: str, details=None):
    payload = {'error': {'code': code, 'message': message}}
    if details:
        payload['error']['details'] = details
    return jsonify(payload), status_code


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get('/health')
def health():
    try:
        conn = get_connection()
        conn.close()
        db_status = 'connected'
    except Exception as exc:
        db_status = f'unavailable: {exc}'
    return jsonify({'status': 'ok', 'service': 'flask-disponibilidad', 'db': db_status}), 200


@app.get('/api/v2/disponibilidad/<int:alojamiento_id>')
def verificar_disponibilidad(alojamiento_id: int):
    fecha_inicio = request.args.get('fecha_inicio')
    fecha_fin = request.args.get('fecha_fin')

    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute(
            'SELECT id, nombre, ciudad, disponible, precio_mensual '
            'FROM reservas_alojamiento WHERE id = %s',
            (alojamiento_id,),
        )
        row = cur.fetchone()

        if not row:
            cur.close()
            conn.close()
            return error_response(404, 'NOT_FOUND', f'Alojamiento {alojamiento_id} no encontrado')

        _, nombre, ciudad, disponible_flag, precio_mensual = row

        conflicto_fechas = False
        if fecha_inicio and fecha_fin:
            cur.execute(
                '''
                SELECT COUNT(*) FROM reservas_reserva
                WHERE alojamiento_id = %s
                  AND estado = 'CONFIRMADA'
                  AND fecha_inicio < %s::date
                  AND fecha_fin    > %s::date
                ''',
                (alojamiento_id, fecha_fin, fecha_inicio),
            )
            conflicto_fechas = cur.fetchone()[0] > 0

        cur.close()
        conn.close()

        disponible = bool(disponible_flag) and not conflicto_fechas

        motivo = None
        if conflicto_fechas:
            motivo = 'conflicto_fechas'
        elif not disponible_flag:
            motivo = 'no_disponible'

        return jsonify({
            'alojamiento_id': alojamiento_id,
            'nombre': nombre,
            'ciudad': ciudad,
            'disponible': disponible,
            'precio_mensual': float(precio_mensual),
            'motivo': motivo,
            'fechas_consultadas': {
                'fecha_inicio': fecha_inicio,
                'fecha_fin': fecha_fin,
            } if fecha_inicio and fecha_fin else None,
        }), 200

    except Exception as exc:
        logger.error(f'[Disponibilidad] DB error: {exc}')
        return error_response(503, 'DB_ERROR', 'No se pudo consultar disponibilidad', str(exc))


@app.get('/api/v2/disponibilidad/')
def listar_disponibles():
    ciudad = request.args.get('ciudad', '').strip()
    tipo = request.args.get('tipo', '').strip().lower()
    precio_max = request.args.get('precio_max', '').strip()

    try:
        conn = get_connection()
        cur = conn.cursor()

        query = '''
            SELECT
                a.id, a.nombre, a.ciudad, a.precio_mensual,
                CASE
                    WHEN c.alojamiento_ptr_id IS NOT NULL  THEN 'Casa'
                    WHEN ap.alojamiento_ptr_id IS NOT NULL THEN 'Apartamento'
                    ELSE 'Alojamiento'
                END AS tipo
            FROM reservas_alojamiento a
            LEFT JOIN reservas_casa        c  ON c.alojamiento_ptr_id  = a.id
            LEFT JOIN reservas_apartamento ap ON ap.alojamiento_ptr_id = a.id
            WHERE a.disponible = TRUE
        '''
        params = []

        if ciudad:
            query += ' AND LOWER(a.ciudad) LIKE LOWER(%s)'
            params.append(f'%{ciudad}%')

        if precio_max:
            try:
                query += ' AND a.precio_mensual <= %s'
                params.append(float(precio_max))
            except ValueError:
                pass

        if tipo == 'casa':
            query += ' AND c.alojamiento_ptr_id IS NOT NULL'
        elif tipo == 'apartamento':
            query += ' AND ap.alojamiento_ptr_id IS NOT NULL'

        query += ' ORDER BY a.precio_mensual ASC LIMIT 50'

        cur.execute(query, params)
        rows = cur.fetchall()
        cur.close()
        conn.close()

        alojamientos = [
            {
                'id': r[0],
                'nombre': r[1],
                'ciudad': r[2],
                'precio_mensual': float(r[3]),
                'tipo': r[4],
            }
            for r in rows
        ]

        return jsonify({'total': len(alojamientos), 'alojamientos': alojamientos}), 200

    except Exception as exc:
        logger.error(f'[Disponibilidad] DB error en listado: {exc}')
        return error_response(503, 'DB_ERROR', 'No se pudo listar alojamientos', str(exc))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5003)
