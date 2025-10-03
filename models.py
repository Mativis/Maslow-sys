from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import os

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='visitante')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def has_permission(self, permission):
        roles_permissions = {
            'visitante': ['download'],
            'operador': ['download', 'add_documento', 'add_colaborador', 'renovar_documento'],
            'gestor': ['download', 'add_documento', 'add_colaborador', 'renovar_documento', 'edit_documento', 'delete_documento'],
            'administrador': ['download', 'add_documento', 'add_colaborador', 'renovar_documento', 'edit_documento', 'delete_documento', 'add_usuario']
        }
        return permission in roles_permissions.get(self.role, [])

class Colaborador(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120))
    departamento = db.Column(db.String(50))
    cargo = db.Column(db.String(50))
    data_admissao = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    documentos = db.relationship('Documento', backref='colaborador', lazy=True, cascade='all, delete-orphan')

class Documento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    colaborador_id = db.Column(db.Integer, db.ForeignKey('colaborador.id'), nullable=False)
    nome = db.Column(db.String(100), nullable=False)
    tipo_validade = db.Column(db.String(20), nullable=False)  # indeterminado, 3, 6, 12, personalizado
    data_upload = db.Column(db.DateTime, default=datetime.utcnow)
    data_validade = db.Column(db.Date)
    arquivo = db.Column(db.String(200), nullable=False)
    observacoes = db.Column(db.Text)
    
    def status_vencimento(self):
        if self.tipo_validade == 'indeterminado':
            return 'válido'
        
        hoje = datetime.now().date()
        if self.data_validade < hoje:
            return 'vencido'
        elif (self.data_validade - hoje).days <= 30:
            return 'proximo_vencer'
        else:
            return 'válido'

# NOVO MODELO: Log de Auditoria
class LogAuditoria(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    acao = db.Column(db.String(100), nullable=False)  # Ex: 'criar_usuario', 'editar_usuario', 'excluir_documento'
    descricao = db.Column(db.Text, nullable=False)
    tabela_afetada = db.Column(db.String(50))  # Ex: 'user', 'documento', 'colaborador'
    registro_id = db.Column(db.Integer)  # ID do registro afetado
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relacionamento com usuário
    usuario = db.relationship('User', backref='logs')