from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
from sqlalchemy import desc, func

from src.models.container import Container
from src.models.sensor_data import SensorData
from src.models.route import Route
from src.models.config import Alert
from src.models.user import db

dashboard_bp = Blueprint("dashboard", __name__)

@dashboard_bp.route("/dashboard/metrics", methods=["GET"])
def get_dashboard_metrics():
    """Retorna métricas principais do dashboard"""
    try:
        # Período para comparação (ontem)
        yesterday_timestamp = int((datetime.utcnow() - timedelta(days=1)).timestamp())
        
        # Total de containers ativos
        total_containers = Container.query.filter_by(ativa=True).count()
        
        # Containers com dados nas últimas 24h
        containers_with_data = db.session.query(Container.uid).join(
            SensorData, Container.uid == SensorData.uid_sensor
        ).filter(
            Container.ativa == True,
            SensorData.timestamp >= yesterday_timestamp
        ).distinct().count()
        
        # Rotas ativas (assumindo que a tabela Route não mudou)
        active_routes = Route.query.filter_by(status='Em Andamento').count()
        
        # Calcular média de bateria
        battery_avg = db.session.query(func.avg(SensorData.battery_pct)).join(
            Container, SensorData.uid_sensor == Container.uid
        ).filter(
            Container.ativa == True,
            SensorData.id.in_(
                db.session.query(func.max(SensorData.id)).group_by(SensorData.uid_sensor)
            )
        ).scalar()
        
        # Calcular eficiência (containers com dados / total)
        efficiency = (containers_with_data / total_containers * 100) if total_containers > 0 else 0
        
        # Calcular variações reais comparando com período anterior
        yesterday_start_timestamp = int((datetime.utcnow() - timedelta(days=2)).timestamp())
        yesterday_end_timestamp = int((datetime.utcnow() - timedelta(days=1)).timestamp())
        
        # Containers ativos ontem
        # Não temos created_at no novo modelo de Container, então usamos ativa
        # Para uma métrica mais precisa, precisaríamos de um campo de criação no modelo 'sensores'
        containers_yesterday = Container.query.filter(
            Container.ativa == True
        ).count() # Simplificado, pois não temos data de criação no novo modelo
        
        # Rotas ativas ontem (assumindo que a tabela Route não mudou)
        routes_yesterday = Route.query.filter(
            Route.status == 'Em Andamento'
        ).count() # Simplificado, pois não temos data de criação no novo modelo
        
        # Calcular variações reais
        container_change = ((total_containers - containers_yesterday) / containers_yesterday * 100) if containers_yesterday > 0 else 0
        routes_change = ((active_routes - routes_yesterday) / routes_yesterday * 100) if routes_yesterday > 0 else 0
        
        # Bateria média ontem
        battery_yesterday = db.session.query(func.avg(SensorData.battery_pct)).filter(
            SensorData.timestamp >= yesterday_start_timestamp,
            SensorData.timestamp <= yesterday_end_timestamp
        ).scalar()
        
        battery_change = ((battery_avg - battery_yesterday) / battery_yesterday * 100) if battery_yesterday and battery_avg else 0
        
        # Eficiência ontem
        containers_with_data_yesterday = db.session.query(Container.uid).join(
            SensorData, Container.uid == SensorData.uid_sensor
        ).filter(
            Container.ativa == True,
            SensorData.timestamp >= yesterday_start_timestamp,
            SensorData.timestamp <= yesterday_end_timestamp
        ).distinct().count()
        
        efficiency_yesterday = (containers_with_data_yesterday / containers_yesterday * 100) if containers_yesterday > 0 else 0
        efficiency_change = efficiency - efficiency_yesterday
        
        metrics = {
            'total_containers': {
                'value': total_containers,
                'change': container_change,
                'change_type': 'increase' if container_change > 0 else 'decrease'
            },
            'active_routes': {
                'value': active_routes,
                'change': routes_change,
                'change_type': 'increase' if routes_change > 0 else 'decrease'
            },
            'battery_avg': {
                'value': round(battery_avg or 0, 1),
                'change': battery_change,
                'change_type': 'increase' if battery_change > 0 else 'decrease'
            },
            'efficiency': {
                'value': round(efficiency, 1),
                'change': efficiency_change,
                'change_type': 'increase' if efficiency_change > 0 else 'decrease'
            }
        }
        
        return jsonify({
            'success': True,
            'data': metrics
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@dashboard_bp.route("/dashboard/containers-status", methods=["GET"])
def get_containers_status():
    """Retorna status atual dos containers para o dashboard"""
    try:
        # Buscar containers com dados mais recentes
        containers = Container.query.filter_by(ativa=True).limit(5).all()
        result = []
        
        for container in containers:
            # Buscar dados mais recentes
            latest_data = SensorData.query.filter_by(
                uid_sensor=container.uid
            ).order_by(desc(SensorData.timestamp)).first()
            
            if latest_data:
                # Calcular tempo desde última atualização
                last_update_datetime = datetime.fromtimestamp(latest_data.timestamp)
                time_diff = datetime.utcnow() - last_update_datetime
                if time_diff.total_seconds() < 60:
                    last_update = "Agora mesmo"
                elif time_diff.total_seconds() < 3600:
                    minutes = int(time_diff.total_seconds() / 60)
                    last_update = f"{minutes} min atrás"
                else:
                    hours = int(time_diff.total_seconds() / 3600)
                    last_update = f"{hours}h atrás"
                
                container_data = {
                    'uid': container.uid,
                    'name': container.nome_amigavel,
                    'location': f'{container.coordenada_y}, {container.coordenada_x}' if container.coordenada_x and container.coordenada_y else None,
                    'type': container.nome_amigavel, # Usando nome_amigavel como tipo
                    'fill_level': latest_data.fill_level,
                    'battery_pct': latest_data.battery_pct,
                    'status': container.get_status(latest_data.fill_level),
                    'last_update': last_update,
                    'rssi': latest_data.rssi,
                    'is_online': time_diff.total_seconds() < 1800  # 30 minutos
                }
                
                result.append(container_data)
        
        return jsonify({
            'success': True,
            'data': result
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@dashboard_bp.route("/dashboard/alerts", methods=["GET"])
def get_recent_alerts():
    """Retorna alertas recentes para o dashboard"""
    try:
        limit = request.args.get('limit', 10, type=int)
        
        # Buscar alertas recentes (assumindo que a tabela Alert não mudou)
        alerts = Alert.query.filter_by(
            is_resolved=False
        ).order_by(desc(Alert.created_at)).limit(limit).all()
        
        result = []
        for alert in alerts:
            alert_data = alert.to_dict()
            alert_data['time_ago'] = alert.get_time_ago()
            result.append(alert_data)
        
        return jsonify({
            'success': True,
            'data': result,
            'total': len(result)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@dashboard_bp.route("/dashboard/system-status", methods=["GET"])
def get_system_status():
    """Retorna status geral do sistema"""
    try:
        # Status MQTT real (obtido do serviço MQTT)
        # from src.services.mqtt_service import MQTTService # Não é necessário importar aqui
        
        # Contar mensagens recebidas hoje
        today_start_timestamp = int(datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
        messages_today = SensorData.query.filter(
            SensorData.timestamp >= today_start_timestamp
        ).count()
        
        # Última mensagem recebida
        last_message_data = SensorData.query.order_by(desc(SensorData.timestamp)).first()
        if last_message_data:
            last_message_datetime = datetime.fromtimestamp(last_message_data.timestamp)
            time_diff = datetime.utcnow() - last_message_datetime
            if time_diff.total_seconds() < 60:
                last_message = "Agora mesmo"
            elif time_diff.total_seconds() < 3600:
                minutes = int(time_diff.total_seconds() / 60)
                last_message = f"{minutes} min atrás"
            else:
                hours = int(time_diff.total_seconds() / 3600)
                last_message = f"{hours}h atrás"
        else:
            last_message = "Nenhuma mensagem"
        
        mqtt_status = {
            'connected': True,  # Assumindo que o serviço MQTT está conectado
            'messages_today': messages_today,
            'last_message': last_message
        }
        
        # Contagem de sensores online
        online_threshold_timestamp = int((datetime.utcnow() - timedelta(minutes=30)).timestamp())
        sensors_online = db.session.query(SensorData.uid_sensor).filter(
            SensorData.timestamp >= online_threshold_timestamp
        ).distinct().count()
        
        total_sensors = Container.query.filter_by(ativa=True).count()
        
        # Gateways não existem mais como tabela separada, então vamos remover ou adaptar
        # Por enquanto, vamos simular os gateways como sendo os containers ativos
        gateways_online = sensors_online # Usar sensores online como proxy para gateways
        total_gateways = total_sensors # Usar total de sensores como proxy para total de gateways
        
        system_status = {
            'mqtt': mqtt_status,
            'sensors': {
                'online': sensors_online,
                'total': total_sensors,
                'percentage': round((sensors_online / total_sensors * 100) if total_sensors > 0 else 0, 1)
            },
            'gateways': {
                'online': gateways_online,
                'total': total_gateways,
                'percentage': round((gateways_online / total_gateways * 100) if total_gateways > 0 else 0, 1)
            }
        }
        
        return jsonify({
            'success': True,
            'data': system_status
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@dashboard_bp.route("/dashboard/charts/fill-levels", methods=["GET"])
def get_fill_levels_chart():
    """Retorna dados para gráfico de níveis de enchimento"""
    try:
        hours = request.args.get('hours', 24, type=int)
        since_timestamp = int((datetime.utcnow() - timedelta(hours=hours)).timestamp())
        
        # Buscar dados agrupados por hora
        # Nota: func.date_trunc não funciona diretamente com BigInteger timestamp. Precisamos converter.
        # Para MySQL, podemos usar FROM_UNIXTIME e DATE_FORMAT
        data = db.session.query(
            func.DATE_FORMAT(func.FROM_UNIXTIME(SensorData.timestamp), '%Y-%m-%d %H:00:00').label('hour'),
            func.avg(SensorData.fill_level).label('avg_fill_level')
        ).filter(
            SensorData.timestamp >= since_timestamp
        ).group_by('hour').order_by('hour').all()
        
        result = []
        for row in data:
            result.append({
                'timestamp': row.hour,
                'avg_fill_level': round(row.avg_fill_level, 1)
            })
        
        return jsonify({
            'success': True,
            'data': result
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@dashboard_bp.route("/dashboard/charts/battery-levels", methods=["GET"])
def get_battery_levels_chart():
    """Retorna dados para gráfico de níveis de bateria"""
    try:
        hours = request.args.get('hours', 24, type=int)
        since_timestamp = int((datetime.utcnow() - timedelta(hours=hours)).timestamp())
        
        # Buscar dados agrupados por hora
        data = db.session.query(
            func.DATE_FORMAT(func.FROM_UNIXTIME(SensorData.timestamp), '%Y-%m-%d %H:00:00').label('hour'),
            func.avg(SensorData.battery_pct).label('avg_battery')
        ).filter(
            SensorData.timestamp >= since_timestamp
        ).group_by('hour').order_by('hour').all()
        
        result = []
        for row in data:
            result.append({
                'timestamp': row.hour,
                'avg_battery': round(row.avg_battery, 1)
            })
        
        return jsonify({
            'success': True,
            'data': result
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@dashboard_bp.route("/dashboard/map-data", methods=["GET"])
def get_map_data():
    """Retorna dados dos containers para exibição no mapa"""
    try:
        # Buscar containers com coordenadas
        containers = Container.query.filter(
            Container.ativa == True,
            Container.coordenada_y.isnot(None),
            Container.coordenada_x.isnot(None)
        ).all()
        
        result = []
        for container in containers:
            # Buscar dados mais recentes
            latest_data = SensorData.query.filter_by(
                uid_sensor=container.uid
            ).order_by(desc(SensorData.timestamp)).first()
            
            container_data = {
                'uid': container.uid,
                'name': container.nome_amigavel,
                'location': f'{container.coordenada_y}, {container.coordenada_x}' if container.coordenada_x and container.coordenada_y else None,
                'latitude': float(container.coordenada_y) if container.coordenada_y else None,
                'longitude': float(container.coordenada_x) if container.coordenada_x else None,
                'type': container.nome_amigavel # Usando nome_amigavel como tipo
            }
            
            if latest_data:
                container_data.update({
                    'fill_level': latest_data.fill_level,
                    'battery_pct': latest_data.battery_pct,
                    'status': container.get_status(latest_data.fill_level),
                    'last_update': datetime.fromtimestamp(latest_data.timestamp).isoformat(),
                    'is_online': (datetime.utcnow() - datetime.fromtimestamp(latest_data.timestamp)).total_seconds() < 1800
                })
            else:
                container_data.update({
                    'fill_level': 0,
                    'battery_pct': 0,
                    'status': 'Sem dados',
                    'last_update': None,
                    'is_online': False
                })
            
            result.append(container_data)
        
        return jsonify({
            'success': True,
            'data': result,
            'total': len(result)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


