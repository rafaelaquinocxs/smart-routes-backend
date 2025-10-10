from flask import Blueprint, request, jsonify, send_file
from src.services.route_service import RouteService
import io
import json

routes_bp = Blueprint('routes', __name__)
route_service = RouteService()

@routes_bp.route('/api/routes', methods=['GET'])
def get_routes():
    """Lista todas as rotas"""
    try:
        routes = route_service.get_all_routes()
        
        return jsonify({
            'success': True,
            'data': routes,
            'total': len(routes)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@routes_bp.route('/api/routes/<int:route_id>', methods=['GET'])
def get_route(route_id):
    """Busca uma rota específica"""
    try:
        route = route_service.get_route_by_id(route_id)
        
        if not route:
            return jsonify({
                'success': False,
                'error': 'Rota não encontrada'
            }), 404
        
        return jsonify({
            'success': True,
            'data': route
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@routes_bp.route('/api/routes/generate', methods=['POST'])
def generate_route():
    """Gera uma nova rota otimizada"""
    try:
        data = request.get_json()
        
        if not data or 'container_uids' not in data:
            return jsonify({
                'success': False,
                'error': 'Lista de containers é obrigatória'
            }), 400
        
        container_uids = data['container_uids']
        start_location = data.get('start_location')
        
        if not container_uids or not isinstance(container_uids, list):
            return jsonify({
                'success': False,
                'error': 'Lista de containers deve ser um array não vazio'
            }), 400
        
        # Gerar rota otimizada
        result = route_service.generate_optimized_route(
            container_uids=container_uids,
            start_location=start_location
        )
        
        if not result['success']:
            return jsonify(result), 400
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@routes_bp.route('/api/routes/<int:route_id>/navigation', methods=['GET'])
def get_navigation_links(route_id):
    """Obtém links de navegação para uma rota"""
    try:
        route = route_service.get_route_by_id(route_id)
        
        if not route:
            return jsonify({
                'success': False,
                'error': 'Rota não encontrada'
            }), 404
        
        # Gerar links de navegação
        navigation_links = route_service._generate_navigation_links({
            'waypoints': route['waypoints'],
            'start_location': route['waypoints'][0]['location'] if route['waypoints'] else 'São Paulo, SP'
        })
        
        return jsonify({
            'success': True,
            'data': navigation_links
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@routes_bp.route('/api/routes/<int:route_id>/gpx', methods=['GET'])
def download_gpx(route_id):
    """Download do arquivo GPX da rota"""
    try:
        route = route_service.get_route_by_id(route_id)
        
        if not route:
            return jsonify({
                'success': False,
                'error': 'Rota não encontrada'
            }), 404
        
        # Gerar conteúdo GPX
        gpx_content = route_service._generate_gpx_file(route['waypoints'])
        
        # Criar arquivo em memória
        gpx_file = io.BytesIO()
        gpx_file.write(gpx_content.encode('utf-8'))
        gpx_file.seek(0)
        
        return send_file(
            gpx_file,
            as_attachment=True,
            download_name=f'rota_{route_id}_smart_routes.gpx',
            mimetype='application/gpx+xml'
        )
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@routes_bp.route('/api/routes/<int:route_id>/status', methods=['PUT'])
def update_route_status(route_id):
    """Atualiza o status de uma rota"""
    try:
        data = request.get_json()
        
        if not data or 'status' not in data:
            return jsonify({
                'success': False,
                'error': 'Status é obrigatório'
            }), 400
        
        status = data['status']
        valid_statuses = ['planned', 'in_progress', 'completed', 'cancelled']
        
        if status not in valid_statuses:
            return jsonify({
                'success': False,
                'error': f'Status deve ser um dos seguintes: {", ".join(valid_statuses)}'
            }), 400
        
        success = route_service.update_route_status(route_id, status)
        
        if not success:
            return jsonify({
                'success': False,
                'error': 'Rota não encontrada'
            }), 404
        
        return jsonify({
            'success': True,
            'message': 'Status atualizado com sucesso'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@routes_bp.route('/api/routes/<int:route_id>', methods=['DELETE'])
def delete_route(route_id):
    """Exclui uma rota"""
    try:
        success = route_service.delete_route(route_id)
        
        if not success:
            return jsonify({
                'success': False,
                'error': 'Rota não encontrada'
            }), 404
        
        return jsonify({
            'success': True,
            'message': 'Rota excluída com sucesso'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@routes_bp.route('/api/routes/containers/available', methods=['GET'])
def get_available_containers():
    """Lista containers disponíveis para criação de rotas"""
    try:
        from src.models.container import Container
        
        # Buscar containers com nível alto ou cheio
        containers = Container.query.join(Container.latest_data).filter(
            Container.latest_data.has(fill_level__gte=70)  # 70% ou mais
        ).all()
        
        # Se não houver containers com nível alto, buscar todos
        if not containers:
            containers = Container.query.all()
        
        container_data = []
        for container in containers:
            fill_level = container.latest_data.fill_level if container.latest_data else 0
            
            container_data.append({
                'uid': container.uid,
                'name': container.name,
                'location': container.location,
                'container_type': container.container_type,
                'fill_level': fill_level,
                'priority': 'high' if fill_level >= 90 else 'medium' if fill_level >= 70 else 'low',
                'has_location': bool(container.location and container.location != "Localização não definida")
            })
        
        # Ordenar por prioridade (nível de enchimento)
        container_data.sort(key=lambda x: x['fill_level'], reverse=True)
        
        return jsonify({
            'success': True,
            'data': container_data,
            'total': len(container_data),
            'summary': {
                'high_priority': len([c for c in container_data if c['priority'] == 'high']),
                'medium_priority': len([c for c in container_data if c['priority'] == 'medium']),
                'low_priority': len([c for c in container_data if c['priority'] == 'low']),
                'with_location': len([c for c in container_data if c['has_location']])
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@routes_bp.route('/api/routes/optimize/auto', methods=['POST'])
def auto_optimize_route():
    """Gera automaticamente uma rota otimizada com containers prioritários"""
    try:
        data = request.get_json() or {}
        max_containers = data.get('max_containers', 10)
        min_fill_level = data.get('min_fill_level', 70)
        
        from src.models.container import Container
        
        # Buscar containers prioritários
        containers = Container.query.join(Container.latest_data).filter(
            Container.latest_data.has(fill_level__gte=min_fill_level),
            Container.location.isnot(None),
            Container.location != "Localização não definida"
        ).order_by(Container.latest_data.fill_level.desc()).limit(max_containers).all()
        
        if not containers:
            return jsonify({
                'success': False,
                'error': 'Nenhum container encontrado com os critérios especificados'
            }), 400
        
        container_uids = [c.uid for c in containers]
        
        # Gerar rota otimizada
        result = route_service.generate_optimized_route(container_uids)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

