import requests
import json
from datetime import datetime
from typing import List, Dict, Optional
from src.models.container import Container
from src.models.route import Route
from src.models.config import SystemConfig
from src.services.config_service import ConfigService

class RouteService:
    def __init__(self):
        self.config_service = ConfigService()
        
    def get_google_maps_api_key(self) -> Optional[str]:
        """Obtém a chave da API do Google Maps das configurações"""
        config = self.config_service.get_config()
        return config.get('google_maps_api_key')
    
    def generate_optimized_route(self, container_uids: List[str], start_location: str = None) -> Dict:
        """
        Gera uma rota otimizada para coleta dos containers especificados
        
        Args:
            container_uids: Lista de UIDs dos containers para coleta
            start_location: Localização de início (opcional, usa base padrão)
            
        Returns:
            Dict com informações da rota otimizada
        """
        try:
            # Buscar containers no banco
            containers = []
            for uid in container_uids:
                container = Container.query.filter_by(uid=uid).first()
                if container and container.location and container.location != "Localização não definida":
                    containers.append(container)
            
            if not containers:
                return {
                    'success': False,
                    'error': 'Nenhum container válido encontrado com localização definida'
                }
            
            # Configuração padrão se não houver localização de início
            if not start_location:
                config = self.config_service.get_config()
                start_location = config.get('base_location', 'São Paulo, SP, Brasil')
            
            # Preparar waypoints (localizações dos containers)
            waypoints = [container.location for container in containers]
            
            # Gerar rota otimizada usando Google Maps API
            api_key = self.get_google_maps_api_key()
            if not api_key:
                # Fallback: gerar rota simples sem otimização
                return self._generate_simple_route(containers, start_location)
            
            # Usar Google Maps Directions API com otimização
            route_data = self._call_google_directions_api(
                start_location, 
                waypoints, 
                api_key
            )
            
            if not route_data['success']:
                return route_data
            
            # Processar dados da rota
            processed_route = self._process_route_data(route_data['data'], containers)
            
            # Salvar rota no banco de dados
            route_record = self._save_route_to_database(processed_route, container_uids)
            
            # Gerar links para apps de navegação
            navigation_links = self._generate_navigation_links(processed_route)
            
            return {
                'success': True,
                'route_id': route_record.id,
                'route_data': processed_route,
                'navigation_links': navigation_links,
                'containers': [
                    {
                        'uid': c.uid,
                        'name': c.name,
                        'location': c.location,
                        'fill_level': c.latest_data.fill_level if c.latest_data else 0
                    } for c in containers
                ],
                'summary': {
                    'total_distance': processed_route.get('total_distance', 0),
                    'total_duration': processed_route.get('total_duration', 0),
                    'total_containers': len(containers),
                    'estimated_fuel_cost': self._calculate_fuel_cost(processed_route.get('total_distance', 0))
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Erro ao gerar rota: {str(e)}'
            }
    
    def _call_google_directions_api(self, origin: str, waypoints: List[str], api_key: str) -> Dict:
        """Chama a API do Google Maps Directions"""
        try:
            base_url = "https://maps.googleapis.com/maps/api/directions/json"
            
            # Preparar waypoints para otimização
            waypoints_str = "optimize:true|" + "|".join(waypoints)
            
            params = {
                'origin': origin,
                'destination': origin,  # Retorna ao ponto de origem
                'waypoints': waypoints_str,
                'key': api_key,
                'mode': 'driving',
                'units': 'metric',
                'language': 'pt-BR'
            }
            
            response = requests.get(base_url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if data['status'] != 'OK':
                return {
                    'success': False,
                    'error': f'Erro da API Google Maps: {data.get("error_message", data["status"])}'
                }
            
            return {
                'success': True,
                'data': data
            }
            
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': f'Erro na requisição para Google Maps API: {str(e)}'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Erro inesperado: {str(e)}'
            }
    
    def _generate_simple_route(self, containers: List[Container], start_location: str) -> Dict:
        """Gera uma rota simples sem otimização (fallback)"""
        waypoints = []
        total_distance = 0
        
        for i, container in enumerate(containers):
            waypoints.append({
                'location': container.location,
                'container_uid': container.uid,
                'container_name': container.name,
                'order': i + 1
            })
            # Estimativa simples de distância (5km entre pontos)
            total_distance += 5000  # metros
        
        return {
            'success': True,
            'route_data': {
                'waypoints': waypoints,
                'total_distance': total_distance,
                'total_duration': total_distance * 0.06,  # Estimativa: 60 segundos por km
                'optimized': False
            },
            'navigation_links': self._generate_navigation_links({
                'waypoints': waypoints,
                'start_location': start_location
            })
        }
    
    def _process_route_data(self, google_data: Dict, containers: List[Container]) -> Dict:
        """Processa os dados retornados pela API do Google Maps"""
        route = google_data['routes'][0]
        legs = route['legs']
        
        # Extrair waypoints otimizados
        waypoint_order = route.get('waypoint_order', list(range(len(containers))))
        
        waypoints = []
        total_distance = 0
        total_duration = 0
        
        for i, leg in enumerate(legs):
            total_distance += leg['distance']['value']
            total_duration += leg['duration']['value']
            
            if i < len(waypoint_order):
                container_index = waypoint_order[i]
                if container_index < len(containers):
                    container = containers[container_index]
                    waypoints.append({
                        'location': leg['end_address'],
                        'container_uid': container.uid,
                        'container_name': container.name,
                        'order': i + 1,
                        'distance_from_previous': leg['distance']['value'],
                        'duration_from_previous': leg['duration']['value'],
                        'coordinates': {
                            'lat': leg['end_location']['lat'],
                            'lng': leg['end_location']['lng']
                        }
                    })
        
        return {
            'waypoints': waypoints,
            'total_distance': total_distance,
            'total_duration': total_duration,
            'optimized': True,
            'polyline': route.get('overview_polyline', {}).get('points', ''),
            'bounds': route.get('bounds', {}),
            'start_location': legs[0]['start_address'] if legs else None
        }
    
    def _save_route_to_database(self, route_data: Dict, container_uids: List[str]) -> Route:
        """Salva a rota no banco de dados"""
        from src.main import db
        
        route = Route(
            name=f"Rota {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            container_uids=json.dumps(container_uids),
            waypoints=json.dumps(route_data['waypoints']),
            total_distance=route_data.get('total_distance', 0),
            total_duration=route_data.get('total_duration', 0),
            optimized=route_data.get('optimized', False),
            polyline=route_data.get('polyline', ''),
            status='planned'
        )
        
        db.session.add(route)
        db.session.commit()
        
        return route
    
    def _generate_navigation_links(self, route_data: Dict) -> Dict:
        """Gera links para abrir a rota em apps de navegação"""
        waypoints = route_data.get('waypoints', [])
        start_location = route_data.get('start_location', 'São Paulo, SP')
        
        if not waypoints:
            return {}
        
        # Preparar lista de destinos
        destinations = [start_location]  # Começar na base
        for waypoint in waypoints:
            destinations.append(waypoint['location'])
        destinations.append(start_location)  # Retornar à base
        
        # Link para Google Maps
        google_maps_url = "https://www.google.com/maps/dir/"
        google_maps_url += "/".join([dest.replace(" ", "+") for dest in destinations])
        
        # Link para Waze (apenas primeiro destino, pois Waze não suporta múltiplos waypoints)
        waze_url = f"https://waze.com/ul?q={waypoints[0]['location'].replace(' ', '%20')}"
        
        # Gerar arquivo GPX para download
        gpx_content = self._generate_gpx_file(waypoints)
        
        return {
            'google_maps': google_maps_url,
            'waze': waze_url,
            'gpx_content': gpx_content,
            'destinations': destinations
        }
    
    def _generate_gpx_file(self, waypoints: List[Dict]) -> str:
        """Gera conteúdo de arquivo GPX para navegação"""
        gpx_header = '''<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="Smart Routes">
<trk>
<name>Rota de Coleta Smart Routes</name>
<trkseg>'''
        
        gpx_points = ""
        for waypoint in waypoints:
            coords = waypoint.get('coordinates', {})
            if coords.get('lat') and coords.get('lng'):
                gpx_points += f'''
<trkpt lat="{coords['lat']}" lon="{coords['lng']}">
<name>{waypoint['container_name']}</name>
<desc>{waypoint['location']}</desc>
</trkpt>'''
        
        gpx_footer = '''
</trkseg>
</trk>
</gpx>'''
        
        return gpx_header + gpx_points + gpx_footer
    
    def _calculate_fuel_cost(self, distance_meters: int) -> float:
        """Calcula custo estimado de combustível"""
        # Configurações padrão
        fuel_consumption_per_100km = 25  # litros por 100km (caminhão)
        fuel_price_per_liter = 5.50  # R$ por litro
        
        distance_km = distance_meters / 1000
        fuel_needed = (distance_km / 100) * fuel_consumption_per_100km
        total_cost = fuel_needed * fuel_price_per_liter
        
        return round(total_cost, 2)
    
    def get_route_by_id(self, route_id: int) -> Optional[Dict]:
        """Busca uma rota pelo ID"""
        route = Route.query.get(route_id)
        if not route:
            return None
        
        return {
            'id': route.id,
            'name': route.name,
            'container_uids': json.loads(route.container_uids),
            'waypoints': json.loads(route.waypoints),
            'total_distance': route.total_distance,
            'total_duration': route.total_duration,
            'optimized': route.optimized,
            'status': route.status,
            'created_at': route.created_at.isoformat(),
            'updated_at': route.updated_at.isoformat()
        }
    
    def get_all_routes(self) -> List[Dict]:
        """Busca todas as rotas"""
        routes = Route.query.order_by(Route.created_at.desc()).all()
        
        return [
            {
                'id': route.id,
                'name': route.name,
                'container_count': len(json.loads(route.container_uids)),
                'total_distance': route.total_distance,
                'total_duration': route.total_duration,
                'optimized': route.optimized,
                'status': route.status,
                'created_at': route.created_at.isoformat(),
                'fuel_cost': self._calculate_fuel_cost(route.total_distance)
            } for route in routes
        ]
    
    def update_route_status(self, route_id: int, status: str) -> bool:
        """Atualiza o status de uma rota"""
        from src.main import db
        
        route = Route.query.get(route_id)
        if not route:
            return False
        
        route.status = status
        route.updated_at = datetime.utcnow()
        db.session.commit()
        
        return True
    
    def delete_route(self, route_id: int) -> bool:
        """Exclui uma rota"""
        from src.main import db
        
        route = Route.query.get(route_id)
        if not route:
            return False
        
        db.session.delete(route)
        db.session.commit()
        
        return True

