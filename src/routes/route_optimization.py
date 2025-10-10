from flask import Blueprint, request, jsonify
from src.models.container import Container
from src.models.sensor_data import SensorData
from src.models.user import db
from datetime import datetime, timedelta
import math

route_optimization_bp = Blueprint("route_optimization", __name__)

def calculate_distance(lat1, lon1, lat2, lon2):
    """Calcula distância entre dois pontos em km"""
    if not all([lat1, lon1, lat2, lon2]):
        return 0
    
    # Fórmula de Haversine
    R = 6371  # Raio da Terra em km
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = (math.sin(delta_lat/2) * math.sin(delta_lat/2) + 
         math.cos(lat1_rad) * math.cos(lat2_rad) * 
         math.sin(delta_lon/2) * math.sin(delta_lon/2))
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return R * c

def solve_tsp_nearest_neighbor(locations, start_index=0):
    """Resolve TSP usando algoritmo do vizinho mais próximo"""
    n = len(locations)
    if n <= 1:
        return list(range(n))
    
    unvisited = set(range(n))
    route = [start_index]
    unvisited.remove(start_index)
    current = start_index
    
    while unvisited:
        nearest = min(unvisited, key=lambda x: calculate_distance(
            locations[current][0], locations[current][1],
            locations[x][0], locations[x][1]
        ))
        route.append(nearest)
        unvisited.remove(nearest)
        current = nearest
    
    return route

@route_optimization_bp.route("/optimize-route", methods=["POST"])
def optimize_route():
    """Gera rota otimizada para containers >75% cheios"""
    try:
        data = request.get_json() or {}
        fill_threshold = data.get("fill_threshold", 75.0)
        depot_lat = data.get("depot_latitude", -23.5505)  # Centro de SP
        depot_lon = data.get("depot_longitude", -46.6333)
        
        # Buscar containers com dados recentes
        recent_timestamp = int((datetime.utcnow() - timedelta(hours=24)).timestamp())
        
        # Query para buscar containers com nível alto
        containers_with_data = db.session.query(Container, SensorData).join(
            SensorData, Container.uid == SensorData.uid_sensor
        ).filter(
            Container.ativa == True,
            SensorData.timestamp >= recent_timestamp,
            Container.nivel >= fill_threshold, # Usar Container.nivel
            Container.coordenada_y.isnot(None),
            Container.coordenada_x.isnot(None)
        ).order_by(SensorData.timestamp.desc()).all()
        
        if not containers_with_data:
            return jsonify({
                "success": False,
                "message": "Nenhum container encontrado com nível >= 75%",
                "containers": [],
                "route": [],
                "total_distance": 0,
                "estimated_time": 0
            })
        
        # Remover duplicatas (manter apenas o dado mais recente de cada container)
        containers_dict = {}
        for container, sensor_data in containers_with_data:
            if container.uid not in containers_dict:
                containers_dict[container.uid] = (container, sensor_data)
        
        containers_list = list(containers_dict.values())
        
        # Preparar localizações (depósito + containers)
        locations = [(depot_lat, depot_lon)]  # Depósito
        for container, sensor_data in containers_list:
            locations.append((float(container.coordenada_y), float(container.coordenada_x)))
        
        # Resolver TSP
        optimal_route = solve_tsp_nearest_neighbor(locations, 0)
        
        # Calcular distância total
        total_distance = 0
        for i in range(len(optimal_route) - 1):
            current_idx = optimal_route[i]
            next_idx = optimal_route[i + 1]
            distance = calculate_distance(
                locations[current_idx][0], locations[current_idx][1],
                locations[next_idx][0], locations[next_idx][1]
            )
            total_distance += distance
        
        # Adicionar retorno ao depósito
        if len(optimal_route) > 1:
            last_idx = optimal_route[-1]
            return_distance = calculate_distance(
                locations[last_idx][0], locations[last_idx][1],
                locations[0][0], locations[0][1]
            )
            total_distance += return_distance
        
        # Preparar resposta
        route_points = []
        container_count = 0
        
        for i, route_idx in enumerate(optimal_route):
            if route_idx == 0:  # Depósito
                route_points.append({
                    "type": "depot",
                    "name": "Depósito",
                    "latitude": depot_lat,
                    "longitude": depot_lon,
                    "order": i + 1
                })
            else:  # Container
                container, sensor_data = containers_list[route_idx - 1]
                container_count += 1
                route_points.append({
                    "type": "container",
                    "id": container.uid, # Usar uid como id
                    "uid": container.uid,
                    "name": container.nome_amigavel,
                    "location": f"{container.coordenada_y}, {container.coordenada_x}",
                    "latitude": float(container.coordenada_y),
                    "longitude": float(container.coordenada_x),
                    "fill_level": container.nivel, # Usar Container.nivel
                    "battery_level": sensor_data.battery_pct,
                    "container_type": container.nome_amigavel, # Usar nome_amigavel como tipo
                    "order": i + 1,
                    "priority": "high" if container.nivel >= 90 else "medium" # Usar Container.nivel
                })
        
        # Adicionar retorno ao depósito
        route_points.append({
            "type": "depot",
            "name": "Retorno ao Depósito",
            "latitude": depot_lat,
            "longitude": depot_lon,
            "order": len(route_points) + 1
        })
        
        # Estimar tempo (30 km/h + 10 min por container)
        travel_time_hours = total_distance / 30
        collection_time_hours = container_count * (10 / 60)
        total_time_minutes = (travel_time_hours + collection_time_hours) * 60
        
        return jsonify({
            "success": True,
            "message": f"Rota otimizada para {container_count} containers",
            "containers_count": container_count,
            "route": route_points,
            "total_distance": round(total_distance, 2),
            "estimated_time": round(total_time_minutes),
            "depot_location": {"latitude": depot_lat, "longitude": depot_lon},
            "created_at": datetime.utcnow().isoformat(),
            "summary": {
                "high_priority": len([p for p in route_points if p.get("priority") == "high"]),
                "medium_priority": len([p for p in route_points if p.get("priority") == "medium"]),
                "total_containers": container_count
            }
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@route_optimization_bp.route("/containers-needing-collection", methods=["GET"])
def get_containers_needing_collection():
    """Lista containers que precisam de coleta (>75%)"""
    try:
        fill_threshold = request.args.get("threshold", 75.0, type=float)
        recent_timestamp = int((datetime.utcnow() - timedelta(hours=24)).timestamp())
        
        # Buscar containers com nível alto
        containers_with_data = db.session.query(Container, SensorData).join(
            SensorData, Container.uid == SensorData.uid_sensor
        ).filter(
            Container.ativa == True,
            SensorData.timestamp >= recent_timestamp,
            Container.nivel >= fill_threshold # Usar Container.nivel
        ).order_by(SensorData.timestamp.desc()).all()
        
        # Remover duplicatas
        containers_dict = {}
        for container, sensor_data in containers_with_data:
            if container.uid not in containers_dict:
                containers_dict[container.uid] = (container, sensor_data)
        
        result = []
        for container, sensor_data in containers_dict.values():
            result.append({
                "id": container.uid, # Usar uid como id
                "uid": container.uid,
                "name": container.nome_amigavel,
                "location": f"{container.coordenada_y}, {container.coordenada_x}",
                "latitude": float(container.coordenada_y),
                "longitude": float(container.coordenada_x),
                "container_type": container.nome_amigavel, # Usar nome_amigavel como tipo
                "fill_level": container.nivel, # Usar Container.nivel
                "battery_level": sensor_data.battery_pct,
                "last_update": datetime.fromtimestamp(sensor_data.timestamp).isoformat(),
                "priority": "high" if container.nivel >= 90 else "medium", # Usar Container.nivel
                "has_location": bool(container.coordenada_y and container.coordenada_x)
            })
        
        # Ordenar por nível de enchimento
        result.sort(key=lambda x: x["fill_level"], reverse=True)
        
        return jsonify({
            "success": True,
            "data": result,
            "total": len(result),
            "summary": {
                "high_priority": len([c for c in result if c["priority"] == "high"]),
                "medium_priority": len([c for c in result if c["priority"] == "medium"]),
                "with_location": len([c for c in result if c["has_location"]])
            }
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

