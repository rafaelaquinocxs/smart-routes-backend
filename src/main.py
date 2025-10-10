import os
import sys
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO
from dotenv import load_dotenv
from fastapi import FastAPI
from src.routes.mqtt import bp as mqtt_bp
# Carregar variáveis de ambiente
load_dotenv()

# Importar modelos
from src.models.user import db
from src.models.container import Container
from src.models.sensor_data import SensorData, Gateway
from src.models.route import Route, RouteContainer
from src.models.config import SystemConfig, Alert

# Importar blueprints
from src.routes.user import user_bp
from src.routes.containers import containers_bp
from src.routes.dashboard import dashboard_bp
from src.routes.config import config_bp
from src.routes.routes import routes_bp



app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'smart-routes-secret-key-2024')

# Configurar CORS
CORS(app, origins="*")

# Configurar SocketIO
socketio = SocketIO(app, cors_allowed_origins="*")

# Registrar blueprints
app.register_blueprint(user_bp, url_prefix='/api')
app.register_blueprint(containers_bp, url_prefix='/api')
app.register_blueprint(dashboard_bp, url_prefix='/api')
app.register_blueprint(config_bp, url_prefix='/api')
app.register_blueprint(routes_bp)

# Configurar banco de dados
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'database', 'app.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Criar tabelas
with app.app_context():
    db.create_all()
    
    # Inicializar configurações padrão
    from src.services.config_service import ConfigService
    ConfigService.initialize_default_configs()

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    static_folder_path = app.static_folder
    if static_folder_path is None:
            return "Static folder not configured", 404

    if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
        return send_from_directory(static_folder_path, path)
    else:
        index_path = os.path.join(static_folder_path, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(static_folder_path, 'index.html')
        else:
            return "index.html not found", 404


if __name__ == '__main__':
    with app.app_context():
        # Inicializar cliente MQTT em thread separada
        from src.services.mqtt_service import MQTTService
        mqtt_service = MQTTService(socketio, app)
        mqtt_service.start()
    
    # Iniciar servidor Flask com SocketIO
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
