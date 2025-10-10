from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from src.models.user import db

class SystemConfig(db.Model):
    __tablename__ = 'system_config'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False, index=True)
    value = db.Column(db.Text)
    description = db.Column(db.String(200))
    config_type = db.Column(db.String(50), default='string')  # string, integer, float, boolean, json
    is_sensitive = db.Column(db.Boolean, default=False)  # Para senhas e tokens
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self, include_sensitive=False):
        """Converte o objeto para dicionário"""
        value = self.value
        
        # Ocultar valores sensíveis se não autorizado
        if self.is_sensitive and not include_sensitive:
            value = '••••••••'
        
        # Converter tipos
        if self.config_type == 'integer' and value:
            try:
                value = int(value)
            except ValueError:
                pass
        elif self.config_type == 'float' and value:
            try:
                value = float(value)
            except ValueError:
                pass
        elif self.config_type == 'boolean' and value:
            value = value.lower() in ('true', '1', 'yes', 'on')
        
        return {
            'id': self.id,
            'key': self.key,
            'value': value,
            'description': self.description,
            'config_type': self.config_type,
            'is_sensitive': self.is_sensitive,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def get_typed_value(self):
        """Retorna o valor convertido para o tipo correto"""
        if not self.value:
            return None
            
        if self.config_type == 'integer':
            try:
                return int(self.value)
            except ValueError:
                return 0
        elif self.config_type == 'float':
            try:
                return float(self.value)
            except ValueError:
                return 0.0
        elif self.config_type == 'boolean':
            return self.value.lower() in ('true', '1', 'yes', 'on')
        elif self.config_type == 'json':
            import json
            try:
                return json.loads(self.value)
            except json.JSONDecodeError:
                return {}
        else:
            return self.value
    
    @staticmethod
    def get_config(key, default=None):
        """Método estático para buscar configuração por chave"""
        config = SystemConfig.query.filter_by(key=key).first()
        if config:
            return config.get_typed_value()
        return default
    
    @staticmethod
    def set_config(key, value, description=None, config_type='string', is_sensitive=False):
        """Método estático para definir configuração"""
        config = SystemConfig.query.filter_by(key=key).first()
        
        if config:
            config.value = str(value)
            config.updated_at = datetime.utcnow()
        else:
            config = SystemConfig(
                key=key,
                value=str(value),
                description=description,
                config_type=config_type,
                is_sensitive=is_sensitive
            )
            db.session.add(config)
        
        db.session.commit()
        return config
    
    def __repr__(self):
        return f'<SystemConfig {self.key}: {self.value}>'


class Alert(db.Model):
    __tablename__ = 'alerts'
    
    id = db.Column(db.Integer, primary_key=True)
    alert_type = db.Column(db.String(50), nullable=False)  # container_full, battery_low, sensor_offline, etc.
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    severity = db.Column(db.String(20), default='info')  # info, warning, error, critical
    container_uid = db.Column(db.String(50), db.ForeignKey('sensores.uid')) # Alterado para 'sensores.uid'
    # gateway_id = db.Column(db.String(20), db.ForeignKey('gateways.id')) # Removido
    is_read = db.Column(db.Boolean, default=False)
    is_resolved = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    resolved_at = db.Column(db.DateTime)
      # gateway = db.relationship('Gateway', backref='alerts') # Removido
    
    def to_dict(self):
        """Converte o objeto para dicionário"""
        return {
            'id': self.id,
            'alert_type': self.alert_type,
            'title': self.title,
            'message': self.message,
            'severity': self.severity,
            'container_uid': self.container_uid,
            # 'gateway_id': self.gateway_id, # Removido
            'is_read': self.is_read,
            'is_resolved': self.is_resolved,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'container': self.container.to_dict() if self.container else None,
            # 'gateway': self.gateway.to_dict() if self.gateway else None # Removido
        }
    
    def mark_read(self):
        """Marca o alerta como lido"""
        self.is_read = True
    
    def resolve(self):
        """Resolve o alerta"""
        self.is_resolved = True
        self.resolved_at = datetime.utcnow()
    
    def get_severity_color(self):
        """Retorna a cor baseada na severidade"""
        severity_colors = {
            'info': 'blue',
            'warning': 'yellow',
            'error': 'red',
            'critical': 'red'
        }
        return severity_colors.get(self.severity, 'gray')
    
    def get_time_ago(self):
        """Retorna o tempo decorrido desde a criação"""
        if not self.created_at:
            return 'Desconhecido'
        
        time_diff = datetime.utcnow() - self.created_at
        
        if time_diff.days > 0:
            return f'{time_diff.days} dia{"s" if time_diff.days > 1 else ""} atrás'
        elif time_diff.seconds > 3600:
            hours = time_diff.seconds // 3600
            return f'{hours}h atrás'
        elif time_diff.seconds > 60:
            minutes = time_diff.seconds // 60
            return f'{minutes} min atrás'
        else:
            return 'Agora mesmo'
    
    @staticmethod
    def create_alert(alert_type, title, message, severity='info', container_uid=None, gateway_id=None):
        """Método estático para criar alertas"""
        alert = Alert(
            alert_type=alert_type,
            title=title,
            message=message,
            severity=severity,
            container_uid=container_uid,
            # gateway_id=gateway_id # Removido
        )
        db.session.add(alert)
        db.session.commit()
        return alert
    
    def __repr__(self):
        return f'<Alert {self.alert_type}: {self.title}>'

