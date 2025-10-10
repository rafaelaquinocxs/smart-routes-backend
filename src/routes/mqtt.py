from flask import Blueprint, request, jsonify

bp = Blueprint("mqtt", __name__)

@bp.route("/api/mqtt/ingest", methods=["POST"])
def ingest_mqtt():
    event = request.get_json(silent=True) or {}
    # Aqui você salva no banco como faz com os outros endpoints
    return jsonify({"ok": True})
