from flask import Blueprint, request, jsonify
from src.models.config import SystemConfig, Alert
from src.models.user import db
from src.services.config_service import ConfigService

config_bp = Blueprint('config', __name__)

@config_bp.route('/config/mqtt', methods=['GET'])
def get_mqtt_config():
    """Retorna configurações MQTT"""
    try:
        config = ConfigService.get_mqtt_config()
        
        # Ocultar senha por segurança
        config['password'] = '••••••••' if config['password'] else ''
        
        return jsonify({
            'success': True,
            'data': config
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@config_bp.route('/config/mqtt', methods=['PUT'])
def update_mqtt_config():
    """Atualiza configurações MQTT"""
    try:
        data = request.get_json()
        
        # Mapear campos para chaves de configuração
        config_mapping = {
            'host': 'mqtt.broker.host',
            'port': 'mqtt.broker.port',
            'username': 'mqtt.username',
            'password': 'mqtt.password',
            'topic_prefix': 'mqtt.topic.prefix',
            'qos': 'mqtt.qos'
        }
        
        # Atualizar configurações
        for field, config_key in config_mapping.items():
            if field in data:
                # Não atualizar senha se for o valor mascarado
                if field == 'password' and data[field] == '••••••••':
                    continue
                
                ConfigService.update_config(config_key, data[field])
        
        return jsonify({
            'success': True,
            'message': 'Configurações MQTT atualizadas com sucesso'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@config_bp.route('/config/alerts', methods=['GET'])
def get_alert_config():
    """Retorna configurações de alertas"""
    try:
        config = ConfigService.get_alert_config()
        
        return jsonify({
            'success': True,
            'data': config
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@config_bp.route('/config/alerts', methods=['PUT'])
def update_alert_config():
    """Atualiza configurações de alertas"""
    try:
        data = request.get_json()
        
        # Mapear campos para chaves de configuração
        config_mapping = {
            'container_full_threshold': 'alerts.container.full_threshold',
            'battery_low_threshold': 'alerts.battery.low_threshold',
            'sensor_offline_timeout': 'alerts.sensor.offline_timeout',
            'gateway_offline_timeout': 'alerts.gateway.offline_timeout'
        }
        
        # Atualizar configurações
        for field, config_key in config_mapping.items():
            if field in data:
                ConfigService.update_config(config_key, data[field])
        
        return jsonify({
            'success': True,
            'message': 'Configurações de alertas atualizadas com sucesso'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@config_bp.route('/config/system', methods=['GET'])
def get_system_config():
    """Retorna configurações do sistema"""
    try:
        config = ConfigService.get_system_config()
        
        return jsonify({
            'success': True,
            'data': config
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@config_bp.route('/config/system', methods=['PUT'])
def update_system_config():
    """Atualiza configurações do sistema"""
    try:
        data = request.get_json()
        
        # Mapear campos para chaves de configuração
        config_mapping = {
            'data_retention_days': 'system.data_retention_days',
            'auto_optimization': 'system.auto_optimization',
            'realtime_updates': 'system.realtime_updates'
        }
        
        # Atualizar configurações
        for field, config_key in config_mapping.items():
            if field in data:
                ConfigService.update_config(config_key, data[field])
        
        return jsonify({
            'success': True,
            'message': 'Configurações do sistema atualizadas com sucesso'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@config_bp.route('/config/map', methods=['GET'])
def get_map_config():
    """Retorna configurações do mapa"""
    try:
        config = ConfigService.get_map_config()
        
        # Ocultar token por segurança
        if config['mapbox_token']:
            config['mapbox_token'] = '••••••••••••••••••••••••••••••••'
        
        return jsonify({
            'success': True,
            'data': config
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@config_bp.route('/config/map', methods=['PUT'])
def update_map_config():
    """Atualiza configurações do mapa"""
    try:
        data = request.get_json()
        
        # Mapear campos para chaves de configuração
        config_mapping = {
            'mapbox_token': 'map.mapbox_token',
            'default_zoom': 'map.default_zoom',
            'default_latitude': 'map.default_latitude',
            'default_longitude': 'map.default_longitude'
        }
        
        # Atualizar configurações
        for field, config_key in config_mapping.items():
            if field in data:
                # Não atualizar token se for o valor mascarado
                if field == 'mapbox_token' and data[field] == '••••••••••••••••••••••••••••••••':
                    continue
                
                ConfigService.update_config(config_key, data[field])
        
        return jsonify({
            'success': True,
            'message': 'Configurações do mapa atualizadas com sucesso'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@config_bp.route('/config/all', methods=['GET'])
def get_all_configs():
    """Retorna todas as configurações"""
    try:
        include_sensitive = request.args.get('include_sensitive', 'false').lower() == 'true'
        configs = ConfigService.get_all_configs(include_sensitive=include_sensitive)
        
        return jsonify({
            'success': True,
            'data': configs,
            'total': len(configs)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@config_bp.route('/config/<key>', methods=['GET'])
def get_config_by_key(key):
    """Retorna uma configuração específica por chave"""
    try:
        config = SystemConfig.query.filter_by(key=key).first()
        if not config:
            return jsonify({
                'success': False,
                'error': 'Configuração não encontrada'
            }), 404
        
        return jsonify({
            'success': True,
            'data': config.to_dict()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@config_bp.route('/config/<key>', methods=['PUT'])
def update_config_by_key(key):
    """Atualiza uma configuração específica por chave"""
    try:
        data = request.get_json()
        
        if 'value' not in data:
            return jsonify({
                'success': False,
                'error': 'Campo value é obrigatório'
            }), 400
        
        success = ConfigService.update_config(key, data['value'])
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Configuração atualizada com sucesso'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Configuração não encontrada'
            }), 404
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@config_bp.route('/alerts', methods=['GET'])
def get_alerts():
    """Lista todos os alertas"""
    try:
        # Parâmetros de filtro
        severity = request.args.get('severity')
        is_resolved = request.args.get('resolved')
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # Query base
        query = Alert.query
        
        # Filtros
        if severity:
            query = query.filter(Alert.severity == severity)
        
        if is_resolved is not None:
            resolved_bool = is_resolved.lower() == 'true'
            query = query.filter(Alert.is_resolved == resolved_bool)
        
        # Ordenar e paginar
        alerts = query.order_by(Alert.created_at.desc()).offset(offset).limit(limit).all()
        total = query.count()
        
        result = []
        for alert in alerts:
            alert_data = alert.to_dict()
            alert_data['time_ago'] = alert.get_time_ago()
            result.append(alert_data)
        
        return jsonify({
            'success': True,
            'data': result,
            'total': total,
            'limit': limit,
            'offset': offset
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@config_bp.route('/alerts/<int:alert_id>/read', methods=['PUT'])
def mark_alert_read(alert_id):
    """Marca um alerta como lido"""
    try:
        alert = Alert.query.get(alert_id)
        if not alert:
            return jsonify({
                'success': False,
                'error': 'Alerta não encontrado'
            }), 404
        
        alert.mark_read()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Alerta marcado como lido'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@config_bp.route('/alerts/<int:alert_id>/resolve', methods=['PUT'])
def resolve_alert(alert_id):
    """Resolve um alerta"""
    try:
        alert = Alert.query.get(alert_id)
        if not alert:
            return jsonify({
                'success': False,
                'error': 'Alerta não encontrado'
            }), 404
        
        alert.resolve()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Alerta resolvido'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@config_bp.route('/alerts/stats', methods=['GET'])
def get_alerts_stats():
    """Retorna estatísticas dos alertas"""
    try:
        stats = {
            'total': Alert.query.count(),
            'unresolved': Alert.query.filter_by(is_resolved=False).count(),
            'unread': Alert.query.filter_by(is_read=False).count(),
            'by_severity': {},
            'by_type': {}
        }
        
        # Contar por severidade
        severity_counts = db.session.query(
            Alert.severity, 
            func.count(Alert.id)
        ).group_by(Alert.severity).all()
        
        for severity, count in severity_counts:
            stats['by_severity'][severity] = count
        
        # Contar por tipo
        type_counts = db.session.query(
            Alert.alert_type, 
            func.count(Alert.id)
        ).group_by(Alert.alert_type).all()
        
        for alert_type, count in type_counts:
            stats['by_type'][alert_type] = count
        
        return jsonify({
            'success': True,
            'data': stats
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

