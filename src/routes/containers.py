from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
from sqlalchemy import desc, func

from src.models.container import Container
from src.models.sensor_data import SensorData
from src.models.config import Alert
from src.models.user import db

def calculate_fill_level(distance_cm):
    """
    Calcula o nível de preenchimento baseado na distância do sensor
    
    Args:
        distance_cm (int): Distância em centímetros
        
    Returns:
        int: Percentual de preenchimento (0-100)
    """
    if distance_cm is None:
        return 0
    
    # Assumindo que:
    # - Container vazio: 200cm de distância
    # - Container cheio: 20cm de distância
    max_distance = 200  # Container vazio
    min_distance = 20   # Container cheio
    
    # Calcular percentual (invertido, pois menor distância = mais cheio)
    if distance_cm >= max_distance:
        return 0  # Vazio
    elif distance_cm <= min_distance:
        return 100  # Cheio
    else:
        # Calcular percentual linear
        fill_percentage = ((max_distance - distance_cm) / (max_distance - min_distance)) * 100
        return max(0, min(100, int(fill_percentage)))

containers_bp = Blueprint("containers", __name__)

@containers_bp.route("/containers", methods=["GET"])
def get_containers():
    """Lista todos os containers com dados mais recentes"""
    try:
        # Parâmetros de filtro
        container_type = request.args.get("type")
        status_filter = request.args.get("status")
        search = request.args.get("search")
        
        # Query base
        query = Container.query.filter_by(ativa=True)
        
        # Filtrar por tipo (usando nome_amigavel como proxy)
        if container_type and container_type != "all":
            query = query.filter(Container.nome_amigavel.like(f"%{container_type}%"))
        
        # Filtrar por busca
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                db.or_(
                    Container.uid.like(search_term),
                    Container.nome_amigavel.like(search_term)
                )
            )
        
        containers = query.all()
        result = []
        
        for container in containers:
            # Buscar dados mais recentes do sensor
            latest_data = SensorData.query.filter_by(
                uid_sensor=container.uid
            ).order_by(desc(SensorData.timestamp)).first()
            
            container_dict = container.to_dict()
            
            if latest_data:
                container_dict["latest_data"] = latest_data.to_dict()
                # Calcular fill_level baseado na distância
                fill_level = calculate_fill_level(latest_data.dist) if latest_data.dist else 0
                container_dict["status"] = container.get_status(fill_level)
                container_dict["fill_level"] = fill_level
                container_dict["last_update"] = datetime.fromtimestamp(latest_data.timestamp).isoformat()
                
                # Verificar se está online baseado no timestamp
                last_update = datetime.fromtimestamp(latest_data.timestamp)
                time_diff = datetime.utcnow() - last_update
                container_dict["is_online"] = time_diff.total_seconds() < 1800  # 30 minutos
            else:
                container_dict["latest_data"] = None
                container_dict["status"] = "Sem dados"
                container_dict["last_update"] = None
                container_dict["is_online"] = False
            
            # Filtrar por status se especificado
            if status_filter and status_filter != "all":
                current_fill_level = container_dict.get("fill_level", 0)
                current_status = container_dict.get("status", "Sem dados")

                if status_filter == "cheios" and current_fill_level < 90:
                    continue
                elif status_filter == "altos" and not (70 <= current_fill_level < 90):
                    continue
                elif status_filter == "medios" and not (40 <= current_fill_level < 70):
                    continue
                elif status_filter == "baixos" and not (20 <= current_fill_level < 40):
                    continue
                elif status_filter == "vazios" and current_fill_level >= 20:
                    continue
                elif status_filter == "offline" and container_dict["is_online"]:
                    continue
            
            result.append(container_dict)
        
        return jsonify({
            "success": True,
            "data": result,
            "total": len(result)
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@containers_bp.route("/containers/<uid>", methods=["GET"])
def get_container(uid):
    """Busca um container específico por UID"""
    try:
        container = Container.query.filter_by(uid=uid, ativa=True).first()
        if not container:
            return jsonify({
                "success": False,
                "error": "Container não encontrado"
            }), 404
        
        # Buscar dados mais recentes
        latest_data = SensorData.query.filter_by(
            uid_sensor=uid
        ).order_by(desc(SensorData.timestamp)).first()
        
        container_dict = container.to_dict()
        
        if latest_data:
            container_dict["latest_data"] = latest_data.to_dict()
            # Calcular fill_level baseado na distância
            fill_level = calculate_fill_level(latest_data.dist) if latest_data.dist else 0
            container_dict["status"] = container.get_status(fill_level)
            container_dict["fill_level"] = fill_level
            
            # Verificar se está online baseado no timestamp
            last_update = datetime.fromtimestamp(latest_data.timestamp)
            time_diff = datetime.utcnow() - last_update
            container_dict["is_online"] = time_diff.total_seconds() < 1800  # 30 minutos
        else:
            container_dict["latest_data"] = None
            container_dict["status"] = "Sem dados"
            container_dict["is_online"] = False
        
        return jsonify({
            "success": True,
            "data": container_dict
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@containers_bp.route("/containers/<uid>/history", methods=["GET"])
def get_container_history(uid):
    """Busca histórico de dados de um container"""
    try:
        # Parâmetros
        hours = request.args.get("hours", 24, type=int)
        limit = request.args.get("limit", 100, type=int)
        
        # Verificar se container existe
        container = Container.query.filter_by(uid=uid, ativa=True).first()
        if not container:
            return jsonify({
                "success": False,
                "error": "Container não encontrado"
            }), 404
        
        # Buscar dados históricos
        since_timestamp = int((datetime.utcnow() - timedelta(hours=hours)).timestamp())
        
        history = SensorData.query.filter(
            SensorData.uid_sensor == uid,
            SensorData.timestamp >= since_timestamp
        ).order_by(desc(SensorData.timestamp)).limit(limit).all()
        
        result = [data.to_dict() for data in history]
        
        return jsonify({
            "success": True,
            "data": result,
            "total": len(result),
            "container": container.to_dict()
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@containers_bp.route("/containers", methods=["POST"])
def create_container():
    """Cria um novo container"""
    try:
        data = request.get_json()
        
        # Validar dados obrigatórios
        required_fields = ["uid", "nome_amigavel", "coordenada_x", "coordenada_y", "ativa", "nivel"]
        for field in required_fields:
            if field not in data:
                return jsonify({
                    "success": False,
                    "error": f"Campo obrigatório: {field}"
                }), 400
        
        # Verificar se UID já existe
        existing = Container.query.get(data["uid"])
        if existing:
            return jsonify({
                "success": False,
                "error": "UID já existe"
            }), 400
        
        # Criar container
        container = Container(
            uid=data["uid"],
            nome_amigavel=data["nome_amigavel"],
            coordenada_x=data["coordenada_x"],
            coordenada_y=data["coordenada_y"],
            ativa=data["ativa"],
            nivel=data["nivel"]
        )
        
        db.session.add(container)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "data": container.to_dict(),
            "message": "Container criado com sucesso"
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@containers_bp.route("/containers/<uid>", methods=["PUT"])
def update_container(uid):
    """Atualiza um container"""
    try:
        container = Container.query.get(uid)
        if not container:
            return jsonify({
                "success": False,
                "error": "Container não encontrado"
            }), 404
        
        data = request.get_json()
        
        # Atualizar campos
        if "nome_amigavel" in data:
            container.nome_amigavel = data["nome_amigavel"]
        if "coordenada_x" in data:
            container.coordenada_x = data["coordenada_x"]
        if "coordenada_y" in data:
            container.coordenada_y = data["coordenada_y"]
        if "ativa" in data:
            container.ativa = data["ativa"]
        if "nivel" in data:
            container.nivel = data["nivel"]
        
        container.last_updated = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            "success": True,
            "data": container.to_dict(),
            "message": "Container atualizado com sucesso"
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@containers_bp.route("/containers/<uid>", methods=["DELETE"])
def delete_container(uid):
    """Remove um container (soft delete) ou inativa"""
    try:
        container = Container.query.get(uid)
        if not container:
            return jsonify({
                "success": False,
                "error": "Container não encontrado"
            }), 404
        
        # Soft delete (inativar)
        container.ativa = False
        container.last_updated = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Container inativado com sucesso"
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@containers_bp.route("/containers/stats", methods=["GET"])
def get_containers_stats():
    """Retorna estatísticas dos containers"""
    try:
        # Contar containers por status
        containers = Container.query.filter_by(ativa=True).all()
        
        stats = {
            "total": len(containers),
            "cheios": 0,
            "altos": 0,
            "medios": 0,
            "baixos": 0,
            "vazios": 0,
            "offline": 0,
            "battery_avg": 0,
            "by_type": {}
        }
        
        battery_sum = 0
        battery_count = 0
        
        for container in containers:
            # Buscar dados mais recentes
            latest_data = SensorData.query.filter_by(
                uid_sensor=container.uid
            ).order_by(desc(SensorData.timestamp)).first()
            
            if latest_data:
                # Calcular fill_level baseado na distância
                fill_level = calculate_fill_level(latest_data.dist) if latest_data.dist else 0
                
                # Contar por status
                if fill_level >= 90:
                    stats["cheios"] += 1
                elif fill_level >= 70:
                    stats["altos"] += 1
                elif fill_level >= 40:
                    stats["medios"] += 1
                elif fill_level >= 20:
                    stats["baixos"] += 1
                else:
                    stats["vazios"] += 1
                
                # Verificar se está offline baseado no timestamp
                last_update = datetime.fromtimestamp(latest_data.timestamp)
                time_diff = datetime.utcnow() - last_update
                if time_diff.total_seconds() >= 1800:  # 30 minutos
                    stats["offline"] += 1
                
                # Calcular média da bateria
                if latest_data.battery_pct is not None:
                    battery_sum += latest_data.battery_pct
                    battery_count += 1
                
                # Contar por tipo (usando nome_amigavel como proxy)
                container_type = container.nome_amigavel
                if container_type not in stats["by_type"]:
                    stats["by_type"][container_type] = 0
                stats["by_type"][container_type] += 1
            else:
                stats["offline"] += 1
        
        # Calcular média da bateria
        if battery_count > 0:
            stats["battery_avg"] = round(battery_sum / battery_count, 1)
        
        return jsonify({
            "success": True,
            "data": stats
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

