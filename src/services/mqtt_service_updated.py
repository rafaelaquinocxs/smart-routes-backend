import json
import threading
import time
from datetime import datetime
from typing import Optional

import paho.mqtt.client as mqtt
from flask_socketio import SocketIO

from src.models.container import Container
from src.models.sensor_data import SensorData, Gateway
from src.models.config import Alert
from src.models.user import db
from src.services.config_service import ConfigService


class MQTTService:
    """Serviço para gerenciar conexão MQTT e processamento de dados dos sensores Cabrex"""
    
    def __init__(self, socketio: SocketIO, app=None):
        self.socketio = socketio
        self.app = app
        self.client: Optional[mqtt.Client] = None
        self.is_connected = False
        self.is_running = False
        self.thread: Optional[threading.Thread] = None
        
        # Configurações MQTT Cabrex
        self.broker_host = "localhost"  # Configurar conforme necessário
        self.broker_port = 1883
        self.topic_prefix = "cabrex/"
        
        # Mapeamento de tipos de sensores
        self.sensor_types = {
            "003D00454741501320313431": "ULTRASSOM_TAMPA_PRETA",
            "004500235847501820393531": "ULTRASSOM_TAMPA_CINZA", 
            "004400255847501820393531": "INFRARED"
        }
        
        # Estatísticas
        self.stats = {
            'messages_received': 0,
            'messages_processed': 0,
            'messages_failed': 0,
            'last_message_time': None,
            'connected_since': None
        }
    
    def start(self):
        """Inicia o serviço MQTT em thread separada"""
        if not self.is_running:
            self.is_running = True
            self.thread = threading.Thread(target=self._run, daemon=True)
            self.thread.start()
            print("🚀 Serviço MQTT Cabrex iniciado")
    
    def stop(self):
        """Para o serviço MQTT"""
        self.is_running = False
        if self.client and self.is_connected:
            self.client.disconnect()
        if self.thread:
            self.thread.join(timeout=5)
        print("🛑 Serviço MQTT parado")
    
    def _run(self):
        """Loop principal do serviço MQTT"""
        while self.is_running:
            try:
                if not self.is_connected:
                    self._connect()
                time.sleep(1)
            except Exception as e:
                print(f"❌ Erro no loop MQTT: {e}")
                time.sleep(5)
    
    def _connect(self):
        """Conecta ao broker MQTT"""
        try:
            self.client = mqtt.Client()
            self.client.on_connect = self._on_connect
            self.client.on_message = self._on_message
            self.client.on_disconnect = self._on_disconnect
            
            print(f"🔌 Conectando ao broker MQTT {self.broker_host}:{self.broker_port}")
            self.client.connect(self.broker_host, self.broker_port, 60)
            self.client.loop_start()
            
        except Exception as e:
            print(f"❌ Erro ao conectar MQTT: {e}")
            time.sleep(10)
    
    def _on_connect(self, client, userdata, flags, rc):
        """Callback de conexão MQTT"""
        if rc == 0:
            self.is_connected = True
            self.stats['connected_since'] = datetime.utcnow()
            
            # Subscrever aos tópicos Cabrex
            topic_pattern = f"{self.topic_prefix}+/data/+"
            client.subscribe(topic_pattern)
            
            print(f"✅ Conectado ao MQTT! Subscrito a: {topic_pattern}")
            
            # Notificar frontend via WebSocket
            self.socketio.emit('mqtt_status', {
                'connected': True,
                'message': 'Conectado ao broker MQTT Cabrex'
            })
        else:
            print(f"❌ Falha na conexão MQTT: {rc}")
            self.is_connected = False
    
    def _on_disconnect(self, client, userdata, rc):
        """Callback de desconexão MQTT"""
        self.is_connected = False
        print(f"🔌 Desconectado do MQTT (código: {rc})")
        
        # Notificar frontend
        self.socketio.emit('mqtt_status', {
            'connected': False,
            'message': 'Desconectado do broker MQTT'
        })
    
    def _on_message(self, client, userdata, msg):
        """Processa mensagens MQTT recebidas"""
        try:
            self.stats['messages_received'] += 1
            self.stats['last_message_time'] = datetime.utcnow()
            
            # Decodificar tópico: cabrex/CABR-A09D5843CA48/data/003D00454741501320313431
            topic_parts = msg.topic.split('/')
            if len(topic_parts) != 4 or topic_parts[0] != 'cabrex':
                print(f"⚠️ Tópico inválido: {msg.topic}")
                return
            
            gateway_id = topic_parts[1]  # CABR-A09D5843CA48
            sensor_uid = topic_parts[3]  # 003D00454741501320313431
            
            # Decodificar payload JSON
            try:
                payload = json.loads(msg.payload.decode('utf-8'))
            except json.JSONDecodeError as e:
                print(f"❌ Erro ao decodificar JSON: {e}")
                self.stats['messages_failed'] += 1
                return
            
            # Validar estrutura da mensagem
            required_fields = ['uid', 'nSeq', 'rssi', 'battery_pct', 'dist', 'timestamp']
            if not all(field in payload for field in required_fields):
                print(f"❌ Campos obrigatórios ausentes: {payload}")
                self.stats['messages_failed'] += 1
                return
            
            # Processar dados com contexto da aplicação Flask
            if self.app:
                with self.app.app_context():
                    self._process_sensor_data(gateway_id, sensor_uid, payload)
            
            self.stats['messages_processed'] += 1
            
        except Exception as e:
            print(f"❌ Erro ao processar mensagem MQTT: {e}")
            self.stats['messages_failed'] += 1
    
    def _process_sensor_data(self, gateway_id: str, sensor_uid: str, payload: dict):
        """Processa dados do sensor e salva no banco"""
        try:
            # Atualizar/criar gateway
            gateway = Gateway.query.get(gateway_id)
            if not gateway:
                gateway = Gateway(
                    id=gateway_id,
                    name=f"Gateway {gateway_id}",
                    location="Localização não definida"
                )
                db.session.add(gateway)
            
            gateway.update_last_seen()
            
            # Verificar/criar container
            container = Container.query.filter_by(uid=sensor_uid).first()
            if not container:
                sensor_type = self.sensor_types.get(sensor_uid, "DESCONHECIDO")
                container = Container(
                    uid=sensor_uid,
                    name=f"Container {sensor_type}",
                    type=sensor_type,
                    latitude=-23.5505,  # Coordenadas padrão (São Paulo)
                    longitude=-46.6333,
                    capacity=100.0,
                    status='active'
                )
                db.session.add(container)
            
            # Calcular nível de preenchimento baseado na distância
            # Distâncias maiores = container mais vazio
            # Assumindo altura do container de 100cm
            container_height = 100  # cm
            distance = payload['dist']
            
            if distance >= container_height:
                fill_level = 0.0  # Vazio
            else:
                fill_level = ((container_height - distance) / container_height) * 100
                fill_level = max(0.0, min(100.0, fill_level))  # Limitar entre 0-100%
            
            # Criar registro de dados do sensor
            sensor_data = SensorData(
                container_uid=sensor_uid,
                gateway_id=gateway_id,
                nseq=payload['nSeq'],
                rssi=payload['rssi'],
                battery_pct=payload['battery_pct'],
                distance=payload['dist'],
                fill_level=fill_level,
                timestamp=datetime.fromtimestamp(payload['timestamp'])
            )
            
            db.session.add(sensor_data)
            
            # Atualizar status do container
            container.fill_level = fill_level
            container.last_updated = datetime.utcnow()
            
            # Determinar status baseado no nível
            if fill_level >= 90:
                container.status = 'full'
            elif fill_level >= 75:
                container.status = 'almost_full'
            elif fill_level >= 25:
                container.status = 'half_full'
            else:
                container.status = 'empty'
            
            db.session.commit()
            
            # Emitir dados em tempo real via WebSocket
            self.socketio.emit('sensor_data', {
                'container_uid': sensor_uid,
                'gateway_id': gateway_id,
                'fill_level': fill_level,
                'battery_pct': payload['battery_pct'],
                'rssi': payload['rssi'],
                'timestamp': payload['timestamp'],
                'sensor_type': self.sensor_types.get(sensor_uid, "DESCONHECIDO")
            })
            
            # Verificar alertas
            self._check_alerts(container, sensor_data)
            
            print(f"✅ Dados processados: {sensor_uid} - {fill_level:.1f}% cheio")
            
        except Exception as e:
            print(f"❌ Erro ao processar dados do sensor: {e}")
            db.session.rollback()
    
    def _check_alerts(self, container: Container, sensor_data: SensorData):
        """Verifica e gera alertas baseados nos dados"""
        try:
            # Alerta de container cheio
            if container.fill_level >= 90:
                alert = Alert(
                    type='container_full',
                    title='Container Cheio',
                    message=f'Container {container.name} está {container.fill_level:.1f}% cheio',
                    container_uid=container.uid,
                    severity='high',
                    data={'fill_level': container.fill_level}
                )
                db.session.add(alert)
                
                # Emitir alerta via WebSocket
                self.socketio.emit('alert', alert.to_dict())
            
            # Alerta de bateria baixa
            if sensor_data.battery_pct <= 20:
                alert = Alert(
                    type='low_battery',
                    title='Bateria Baixa',
                    message=f'Sensor {container.name} com bateria em {sensor_data.battery_pct}%',
                    container_uid=container.uid,
                    severity='medium',
                    data={'battery_pct': sensor_data.battery_pct}
                )
                db.session.add(alert)
                
                # Emitir alerta via WebSocket
                self.socketio.emit('alert', alert.to_dict())
            
            # Alerta de sinal fraco
            if sensor_data.rssi <= -80:
                alert = Alert(
                    type='weak_signal',
                    title='Sinal Fraco',
                    message=f'Sensor {container.name} com sinal fraco (RSSI: {sensor_data.rssi})',
                    container_uid=container.uid,
                    severity='low',
                    data={'rssi': sensor_data.rssi}
                )
                db.session.add(alert)
                
                # Emitir alerta via WebSocket
                self.socketio.emit('alert', alert.to_dict())
            
        except Exception as e:
            print(f"❌ Erro ao verificar alertas: {e}")
    
    def get_stats(self):
        """Retorna estatísticas do serviço MQTT"""
        return {
            **self.stats,
            'is_connected': self.is_connected,
            'is_running': self.is_running,
            'broker_host': self.broker_host,
            'broker_port': self.broker_port
        }
    
    def publish_test_message(self, gateway_id: str = "CABR-A09D5843CA48"):
        """Publica mensagem de teste para simular sensor"""
        if not self.is_connected:
            return False
        
        test_sensors = [
            "003D00454741501320313431",  # ULTRASSOM TAMPA PRETA
            "004500235847501820393531",  # ULTRASSOM TAMPA CINZA
            "004400255847501820393531"   # INFRARED
        ]
        
        for sensor_uid in test_sensors:
            topic = f"{self.topic_prefix}{gateway_id}/data/{sensor_uid}"
            payload = {
                "uid": sensor_uid,
                "nSeq": int(time.time()) % 10000,
                "rssi": -50 - (hash(sensor_uid) % 30),  # -50 a -80
                "battery_pct": 70 + (hash(sensor_uid) % 30),  # 70-100%
                "dist": 20 + (hash(sensor_uid) % 60),  # 20-80cm
                "timestamp": int(time.time())
            }
            
            self.client.publish(topic, json.dumps(payload))
            print(f"📤 Mensagem de teste enviada: {topic}")
        
        return True
