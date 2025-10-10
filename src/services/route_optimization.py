import requests
import json
from typing import List, Dict, Tuple
from src.models.container import Container
from src.models.sensor_data import SensorData
from src.models.user import db
from datetime import datetime, timedelta

class RouteOptimizationService:
    """Serviço para otimização de rotas de coleta"""
    
    def __init__(self):
        # Em produção, usar chave real do Google Maps
        self.google_maps_api_key = "YOUR_GOOGLE_MAPS_API_KEY"
        self.base_url = "https://maps.googleapis.com/maps/api"
    
    def get_containers_needing_collection(self, fill_threshold: float = 75.0) -> List[Container]:
        """
        Busca containers que precisam de coleta (>75% cheios)
        
        Args:
            fill_threshold (float): Percentual mínimo para coleta
            
        Returns:
            List[Container]: Lista de containers que precisam de coleta
        """
        try:
            # Buscar containers ativos com dados recentes
            recent_time = datetime.utcnow() - timedelta(hours=24)
            
            # Query para buscar containers com nível de enchimento > threshold
            containers_query = db.session.query(Container).join(
                SensorData, Container.uid == SensorData.container_uid
            ).filter(
                Container.is_active == True,
                SensorData.timestamp >= recent_time,
                SensorData.fill_level >= fill_threshold
            ).distinct()
            
            containers = containers_query.all()
            
            # Adicionar dados do sensor mais recente para cada container
            for container in containers:
                latest_data = SensorData.query.filter_by(
                    container_uid=container.uid
                ).order_by(SensorData.timestamp.desc()).first()
                
                if latest_data:
                    container.latest_fill_level = latest_data.fill_level
                    container.latest_battery = latest_data.battery_pct
                    container.latest_timestamp = latest_data.timestamp
                else:
                    container.latest_fill_level = 0
                    container.latest_battery = 0
                    container.latest_timestamp = None
            
            return containers
            
        except Exception as e:
            print(f"Erro ao buscar containers para coleta: {e}")
            return []
    
    def calculate_distance_matrix(self, locations: List[Tuple[float, float]]) -> List[List[float]]:
        """
        Calcula matriz de distâncias entre localizações usando Google Maps
        
        Args:
            locations: Lista de tuplas (latitude, longitude)
            
        Returns:
            List[List[float]]: Matriz de distâncias em metros
        """
        try:
            # Para demonstração, usar distância euclidiana simples
            # Em produção, usar Google Maps Distance Matrix API
            
            n = len(locations)
            matrix = [[0.0 for _ in range(n)] for _ in range(n)]
            
            for i in range(n):
                for j in range(n):
                    if i != j:
                        lat1, lon1 = locations[i]
                        lat2, lon2 = locations[j]
                        
                        # Distância euclidiana aproximada em metros
                        # 1 grau ≈ 111km
                        lat_diff = (lat2 - lat1) * 111000
                        lon_diff = (lon2 - lon1) * 111000 * 0.8  # Ajuste para latitude de SP
                        distance = (lat_diff**2 + lon_diff**2)**0.5
                        
                        matrix[i][j] = distance
            
            return matrix
            
        except Exception as e:
            print(f"Erro ao calcular matriz de distâncias: {e}")
            return []
    
    def solve_tsp_greedy(self, distance_matrix: List[List[float]], start_index: int = 0) -> List[int]:
        """
        Resolve o problema do caixeiro viajante usando algoritmo guloso
        
        Args:
            distance_matrix: Matriz de distâncias
            start_index: Índice do ponto de partida
            
        Returns:
            List[int]: Ordem otimizada de visitação
        """
        try:
            n = len(distance_matrix)
            if n <= 1:
                return list(range(n))
            
            visited = [False] * n
            route = [start_index]
            visited[start_index] = True
            current = start_index
            
            for _ in range(n - 1):
                nearest_distance = float('inf')
                nearest_index = -1
                
                for j in range(n):
                    if not visited[j] and distance_matrix[current][j] < nearest_distance:
                        nearest_distance = distance_matrix[current][j]
                        nearest_index = j
                
                if nearest_index != -1:
                    route.append(nearest_index)
                    visited[nearest_index] = True
                    current = nearest_index
            
            return route
            
        except Exception as e:
            print(f"Erro ao resolver TSP: {e}")
            return list(range(len(distance_matrix)))
    
    def optimize_collection_route(self, depot_location: Tuple[float, float] = None) -> Dict:
        """
        Otimiza rota de coleta para containers que precisam ser coletados
        
        Args:
            depot_location: Localização do depósito (lat, lon)
            
        Returns:
            Dict: Rota otimizada com containers e informações
        """
        try:
            # Buscar containers que precisam de coleta
            containers = self.get_containers_needing_collection()
            
            if not containers:
                return {
                    'success': False,
                    'message': 'Nenhum container precisa de coleta no momento',
                    'containers': [],
                    'route': [],
                    'total_distance': 0,
                    'estimated_time': 0
                }
            
            # Usar localização padrão se não fornecida (Centro de SP)
            if depot_location is None:
                depot_location = (-23.5505, -46.6333)
            
            # Preparar localizações (depósito + containers)
            locations = [depot_location]
            for container in containers:
                if container.latitude and container.longitude:
                    locations.append((container.latitude, container.longitude))
            
            # Calcular matriz de distâncias
            distance_matrix = self.calculate_distance_matrix(locations)
            
            if not distance_matrix:
                return {
                    'success': False,
                    'message': 'Erro ao calcular distâncias',
                    'containers': [],
                    'route': [],
                    'total_distance': 0,
                    'estimated_time': 0
                }
            
            # Resolver TSP (começando do depósito)
            optimal_route = self.solve_tsp_greedy(distance_matrix, 0)
            
            # Calcular distância total
            total_distance = 0
            for i in range(len(optimal_route) - 1):
                current = optimal_route[i]
                next_point = optimal_route[i + 1]
                total_distance += distance_matrix[current][next_point]
            
            # Voltar ao depósito
            if len(optimal_route) > 1:
                total_distance += distance_matrix[optimal_route[-1]][0]
            
            # Preparar resposta
            route_containers = []
            for i, route_index in enumerate(optimal_route):
                if route_index == 0:  # Depósito
                    route_containers.append({
                        'type': 'depot',
                        'name': 'Depósito',
                        'latitude': depot_location[0],
                        'longitude': depot_location[1],
                        'order': i + 1
                    })
                else:  # Container
                    container = containers[route_index - 1]  # -1 porque depósito é índice 0
                    route_containers.append({
                        'type': 'container',
                        'id': container.id,
                        'uid': container.uid,
                        'name': container.name,
                        'latitude': container.latitude,
                        'longitude': container.longitude,
                        'fill_level': getattr(container, 'latest_fill_level', 0),
                        'battery_level': getattr(container, 'latest_battery', 0),
                        'container_type': container.container_type,
                        'order': i + 1
                    })
            
            # Adicionar retorno ao depósito
            route_containers.append({
                'type': 'depot',
                'name': 'Retorno ao Depósito',
                'latitude': depot_location[0],
                'longitude': depot_location[1],
                'order': len(route_containers) + 1
            })
            
            # Estimar tempo (assumindo 30 km/h + 10 min por container)
            estimated_time_hours = (total_distance / 1000) / 30  # Tempo de viagem
            estimated_time_hours += len(containers) * (10 / 60)  # Tempo de coleta
            
            return {
                'success': True,
                'message': f'Rota otimizada para {len(containers)} containers',
                'containers_count': len(containers),
                'route': route_containers,
                'total_distance': round(total_distance / 1000, 2),  # km
                'estimated_time': round(estimated_time_hours * 60),  # minutos
                'depot_location': depot_location,
                'created_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            print(f"Erro ao otimizar rota: {e}")
            return {
                'success': False,
                'message': f'Erro ao otimizar rota: {str(e)}',
                'containers': [],
                'route': [],
                'total_distance': 0,
                'estimated_time': 0
            }

