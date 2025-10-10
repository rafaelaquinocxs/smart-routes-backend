import os
from src.models.config import SystemConfig
from src.models.user import db

class ConfigService:
    """Serviço para gerenciar configurações do sistema"""
    
    @staticmethod
    def initialize_default_configs():
        """Inicializa as configurações padrão do sistema"""
        
        default_configs = [
            # Configurações MQTT
            {
                'key': 'mqtt.broker.host',
                'value': os.getenv('MQTT_BROKER_HOST', 'localhost'),
                'description': 'Endereço do broker MQTT',
                'config_type': 'string'
            },
            {
                'key': 'mqtt.broker.port',
                'value': os.getenv('MQTT_BROKER_PORT', '1883'),
                'description': 'Porta do broker MQTT',
                'config_type': 'integer'
            },
            {
                'key': 'mqtt.username',
                'value': os.getenv('MQTT_USERNAME', 'admin'),
                'description': 'Usuário para autenticação MQTT',
                'config_type': 'string'
            },
            {
                'key': 'mqtt.password',
                'value': os.getenv('MQTT_PASSWORD', 'password'),
                'description': 'Senha para autenticação MQTT',
                'config_type': 'string',
                'is_sensitive': True
            },
            {
                'key': 'mqtt.topic.prefix',
                'value': os.getenv('MQTT_TOPIC_PREFIX', 'cabrex'),
                'description': 'Prefixo dos tópicos MQTT',
                'config_type': 'string'
            },
            {
                'key': 'mqtt.qos',
                'value': '1',
                'description': 'Quality of Service para MQTT',
                'config_type': 'integer'
            },
            
            # Configurações de Alertas
            {
                'key': 'alerts.container.full_threshold',
                'value': '90',
                'description': 'Limite para alerta de container cheio (%)',
                'config_type': 'integer'
            },
            {
                'key': 'alerts.battery.low_threshold',
                'value': '20',
                'description': 'Limite para alerta de bateria baixa (%)',
                'config_type': 'integer'
            },
            {
                'key': 'alerts.sensor.offline_timeout',
                'value': '30',
                'description': 'Timeout para considerar sensor offline (minutos)',
                'config_type': 'integer'
            },
            {
                'key': 'alerts.gateway.offline_timeout',
                'value': '5',
                'description': 'Timeout para considerar gateway offline (minutos)',
                'config_type': 'integer'
            },
            
            # Configurações do Sistema
            {
                'key': 'system.data_retention_days',
                'value': '90',
                'description': 'Dias para retenção de dados históricos',
                'config_type': 'integer'
            },
            {
                'key': 'system.auto_optimization',
                'value': 'true',
                'description': 'Otimização automática de rotas',
                'config_type': 'boolean'
            },
            {
                'key': 'system.realtime_updates',
                'value': 'true',
                'description': 'Atualizações em tempo real',
                'config_type': 'boolean'
            },
            
            # Configurações do Mapa
            {
                'key': 'map.mapbox_token',
                'value': os.getenv('MAPBOX_TOKEN', ''),
                'description': 'Token de acesso do Mapbox',
                'config_type': 'string',
                'is_sensitive': True
            },
            {
                'key': 'map.default_zoom',
                'value': '13',
                'description': 'Zoom padrão do mapa',
                'config_type': 'integer'
            },
            {
                'key': 'map.default_latitude',
                'value': '-23.5505',
                'description': 'Latitude central padrão',
                'config_type': 'float'
            },
            {
                'key': 'map.default_longitude',
                'value': '-46.6333',
                'description': 'Longitude central padrão',
                'config_type': 'float'
            },
            
            # Configurações de Email
            {
                'key': 'email.smtp_server',
                'value': os.getenv('EMAIL_SMTP_SERVER', 'smtp.gmail.com'),
                'description': 'Servidor SMTP para envio de emails',
                'config_type': 'string'
            },
            {
                'key': 'email.smtp_port',
                'value': os.getenv('EMAIL_SMTP_PORT', '587'),
                'description': 'Porta do servidor SMTP',
                'config_type': 'integer'
            },
            {
                'key': 'email.username',
                'value': os.getenv('EMAIL_USERNAME', ''),
                'description': 'Usuário para autenticação SMTP',
                'config_type': 'string'
            },
            {
                'key': 'email.password',
                'value': os.getenv('EMAIL_PASSWORD', ''),
                'description': 'Senha para autenticação SMTP',
                'config_type': 'string',
                'is_sensitive': True
            },
            {
                'key': 'email.from_address',
                'value': os.getenv('EMAIL_FROM_ADDRESS', 'alerts@smartroutes.com'),
                'description': 'Endereço de email remetente',
                'config_type': 'string'
            }
        ]
        
        for config_data in default_configs:
            existing = SystemConfig.query.filter_by(key=config_data['key']).first()
            if not existing:
                config = SystemConfig(
                    key=config_data['key'],
                    value=config_data['value'],
                    description=config_data['description'],
                    config_type=config_data['config_type'],
                    is_sensitive=config_data.get('is_sensitive', False)
                )
                db.session.add(config)
        
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"Erro ao inicializar configurações: {e}")
    
    @staticmethod
    def get_mqtt_config():
        """Retorna as configurações MQTT"""
        return {
            'host': SystemConfig.get_config('mqtt.broker.host', 'localhost'),
            'port': SystemConfig.get_config('mqtt.broker.port', 1883),
            'username': SystemConfig.get_config('mqtt.username', 'admin'),
            'password': SystemConfig.get_config('mqtt.password', 'password'),
            'topic_prefix': SystemConfig.get_config('mqtt.topic.prefix', 'cabrex'),
            'qos': SystemConfig.get_config('mqtt.qos', 1)
        }
    
    @staticmethod
    def get_alert_config():
        """Retorna as configurações de alertas"""
        return {
            'container_full_threshold': SystemConfig.get_config('alerts.container.full_threshold', 90),
            'battery_low_threshold': SystemConfig.get_config('alerts.battery.low_threshold', 20),
            'sensor_offline_timeout': SystemConfig.get_config('alerts.sensor.offline_timeout', 30),
            'gateway_offline_timeout': SystemConfig.get_config('alerts.gateway.offline_timeout', 5)
        }
    
    @staticmethod
    def get_system_config():
        """Retorna as configurações do sistema"""
        return {
            'data_retention_days': SystemConfig.get_config('system.data_retention_days', 90),
            'auto_optimization': SystemConfig.get_config('system.auto_optimization', True),
            'realtime_updates': SystemConfig.get_config('system.realtime_updates', True)
        }
    
    @staticmethod
    def get_map_config():
        """Retorna as configurações do mapa"""
        return {
            'mapbox_token': SystemConfig.get_config('map.mapbox_token', ''),
            'default_zoom': SystemConfig.get_config('map.default_zoom', 13),
            'default_latitude': SystemConfig.get_config('map.default_latitude', -23.5505),
            'default_longitude': SystemConfig.get_config('map.default_longitude', -46.6333)
        }
    
    @staticmethod
    def update_config(key, value):
        """Atualiza uma configuração"""
        config = SystemConfig.query.filter_by(key=key).first()
        if config:
            config.value = str(value)
            db.session.commit()
            return True
        return False
    
    @staticmethod
    def get_all_configs(include_sensitive=False):
        """Retorna todas as configurações"""
        configs = SystemConfig.query.all()
        return [config.to_dict(include_sensitive=include_sensitive) for config in configs]

