from datetime import date
from decimal import Decimal, InvalidOperation

from flask import Flask, jsonify, request

app = Flask(__name__)


class ValidationError(Exception):
    def __init__(self, message: str, details=None):
        super().__init__(message)
        self.details = details


def error_response(status_code: int, code: str, message: str, details=None):
    payload = {
        "error": {
            "code": code,
            "message": message,
        }
    }
    if details is not None:
        payload["error"]["details"] = details
    return jsonify(payload), status_code


@app.errorhandler(ValidationError)
def handle_validation_error(error: ValidationError):
    return error_response(400, "VALIDATION_ERROR", str(error), error.details)


@app.errorhandler(Exception)
def handle_unexpected_error(error: Exception):
    return error_response(500, "INTERNAL_SERVER_ERROR", "Unexpected error", str(error))


def parse_iso_date(raw_value, field_name: str) -> date:
    try:
        return date.fromisoformat(str(raw_value))
    except (TypeError, ValueError):
        raise ValidationError(
            "Invalid request payload",
            {field_name: "Expected ISO date format YYYY-MM-DD"},
        )


def parse_decimal(raw_value, field_name: str) -> Decimal:
    try:
        return Decimal(str(raw_value))
    except (TypeError, InvalidOperation):
        raise ValidationError(
            "Invalid request payload",
            {field_name: "Expected a numeric value"},
        )


@app.get("/health")
def health_check():
    return jsonify({"status": "ok", "service": "flask-microservice"}), 200


@app.post("/api/v2/funcionalidad")
def calcular_cotizacion_reserva():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValidationError(
            "Invalid request payload",
            {"body": "Expected JSON object"},
        )

    required_fields = ["fecha_inicio", "fecha_fin", "precio_mensual"]
    missing = [field for field in required_fields if field not in data]
    if missing:
        raise ValidationError(
            "Missing required fields",
            {"missing": missing},
        )

    fecha_inicio = parse_iso_date(data.get("fecha_inicio"), "fecha_inicio")
    fecha_fin = parse_iso_date(data.get("fecha_fin"), "fecha_fin")
    precio_mensual = parse_decimal(data.get("precio_mensual"), "precio_mensual")

    if fecha_inicio < date.today():
        raise ValidationError(
            "Business rule validation failed",
            {"fecha_inicio": "Start date must be in the future"},
        )

    if fecha_fin <= fecha_inicio:
        raise ValidationError(
            "Business rule validation failed",
            {"fecha_fin": "End date must be after start date"},
        )

    duracion_dias = (fecha_fin - fecha_inicio).days
    if duracion_dias < 30:
        raise ValidationError(
            "Business rule validation failed",
            {"duracion": "Minimum stay is 30 days"},
        )

    duracion_meses = Decimal(duracion_dias) / Decimal("30")
    monto_total = (precio_mensual * duracion_meses).quantize(Decimal("0.01"))

    return jsonify(
        {
            "resultado": {
                "duracion_dias": duracion_dias,
                "duracion_meses": str(duracion_meses),
                "monto_total": str(monto_total),
                "moneda": "COP",
            }
        }
    ), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
