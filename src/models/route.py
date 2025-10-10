from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from src.models.user import db

class Route(db.Model):
    __tablename__ = 'routes'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    route_id = db.Column(db.String(20), unique=True, nullable=False)  # RT001, RT002, etc.
    status = db.Column(db.String(20), default='Planejada')  # Planejada, Em Andamento, Concluída, Pausada
    driver_name = db.Column(db.String(100))
    vehicle_name = db.Column(db.String(100))
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)
    estimated_duration = db.Column(db.Integer)  # Duração estimada em minutos
    actual_duration = db.Column(db.Integer)     # Duração real em minutos
    total_distance = db.Column(db.Float)        # Distância total em km
    fuel_saved = db.Column(db.Float)            # Combustível economizado em %
    co2_reduced = db.Column(db.Float)           # CO2 reduzido em kg
    progress = db.Column(db.Integer, default=0) # Progresso em %
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamento com containers da rota
    route_containers = db.relationship('RouteContainer', backref='route', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        """Converte o objeto para dicionário"""
        containers = [rc.to_dict() for rc in self.route_containers]
        
        return {
            'id': self.id,
            'name': self.name,
            'route_id': self.route_id,
            'status': self.status,
            'driver_name': self.driver_name,
            'vehicle_name': self.vehicle_name,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'estimated_duration': self.estimated_duration,
            'actual_duration': self.actual_duration,
            'total_distance': self.total_distance,
            'fuel_saved': self.fuel_saved,
            'co2_reduced': self.co2_reduced,
            'progress': self.progress,
            'containers': containers,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def get_container_count(self):
        """Retorna o número de containers na rota"""
        return len(self.route_containers)
    
    def get_status_color(self):
        """Retorna a cor baseada no status"""
        status_colors = {
            'Planejada': 'blue',
            'Em Andamento': 'green',
            'Concluída': 'gray',
            'Pausada': 'orange'
        }
        return status_colors.get(self.status, 'gray')
    
    def start_route(self):
        """Inicia a rota"""
        self.status = 'Em Andamento'
        self.start_time = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def pause_route(self):
        """Pausa a rota"""
        self.status = 'Pausada'
        self.updated_at = datetime.utcnow()
    
    def complete_route(self):
        """Completa a rota"""
        self.status = 'Concluída'
        self.end_time = datetime.utcnow()
        self.progress = 100
        
        if self.start_time:
            duration = self.end_time - self.start_time
            self.actual_duration = int(duration.total_seconds() / 60)
        
        self.updated_at = datetime.utcnow()
    
    def __repr__(self):
        return f'<Route {self.route_id}: {self.name}>'


class RouteContainer(db.Model):
    __tablename__ = 'route_containers'
    
    id = db.Column(db.Integer, primary_key=True)
    route_id = db.Column(db.Integer, db.ForeignKey('routes.id'), nullable=False)
    container_uid = db.Column(db.String(50), db.ForeignKey('sensores.uid'), nullable=False)
    order_index = db.Column(db.Integer, nullable=False)  # Ordem na rota
    is_collected = db.Column(db.Boolean, default=False)
    collected_at = db.Column(db.DateTime)
    
    # Relacionamento com container
    container = db.relationship('Container', backref='route_assignments')
    
    def to_dict(self):
        """Converte o objeto para dicionário"""
        return {
            'id': self.id,
            'route_id': self.route_id,
            'container_uid': self.container_uid,
            'order_index': self.order_index,
            'is_collected': self.is_collected,
            'collected_at': self.collected_at.isoformat() if self.collected_at else None,
            'container': self.container.to_dict() if self.container else None
        }
    
    def mark_collected(self):
        """Marca o container como coletado"""
        self.is_collected = True
        self.collected_at = datetime.utcnow()
    
    def __repr__(self):
        return f'<RouteContainer {self.route_id}-{self.container_uid}>'
