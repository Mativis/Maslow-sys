from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import StringField, PasswordField, SelectField, DateField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Email, Length, Optional
from wtforms.validators import ValidationError

class LoginForm(FlaskForm):
    username = StringField('Usuário', validators=[DataRequired()])
    password = PasswordField('Senha', validators=[DataRequired()])
    submit = SubmitField('Entrar')

class ColaboradorForm(FlaskForm):
    nome = StringField('Nome Completo', validators=[DataRequired(), Length(max=100)])
    email = StringField('Email', validators=[Email()])
    departamento = StringField('Departamento', validators=[Length(max=50)])
    cargo = StringField('Cargo', validators=[Length(max=50)])
    data_admissao = DateField('Data de Admissão')
    submit = SubmitField('Cadastrar Colaborador')

class DocumentoForm(FlaskForm):
    nome = StringField('Nome do Documento', validators=[DataRequired(), Length(max=100)])
    tipo_validade = SelectField('Validade', choices=[
        ('indeterminado', 'Indeterminado'),
        ('3', '3 Meses'),
        ('6', '6 Meses'),
        ('12', '12 Meses'),
        ('personalizado', 'Data Personalizada')
    ], validators=[DataRequired()])
    data_validade = DateField('Data de Validade (para personalizado)', validators=[Optional()])
    arquivo = FileField('Arquivo', validators=[FileRequired(), FileAllowed(['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png'], 'Apenas documentos e imagens!')])
    observacoes = TextAreaField('Observações')
    submit = SubmitField('Adicionar Documento')

    def validate_data_validade(self, field):
        if self.tipo_validade.data == 'personalizado' and not field.data:
            raise ValidationError('Data de validade é obrigatória quando o tipo é "Data Personalizada"')

class UsuarioForm(FlaskForm):
    username = StringField('Usuário', validators=[DataRequired(), Length(max=80)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Senha', validators=[DataRequired(), Length(min=6)])
    role = SelectField('Cargo', choices=[
        ('visitante', 'Visitante'),
        ('operador', 'Operador'),
        ('gestor', 'Gestor'),
        ('administrador', 'Administrador')
    ], validators=[DataRequired()])
    submit = SubmitField('Cadastrar Usuário')

# NOVO FORMULÁRIO: Edição de Usuário
class EditarUsuarioForm(FlaskForm):
    username = StringField('Usuário', validators=[DataRequired(), Length(max=80)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    role = SelectField('Cargo', choices=[
        ('visitante', 'Visitante'),
        ('operador', 'Operador'),
        ('gestor', 'Gestor'),
        ('administrador', 'Administrador')
    ], validators=[DataRequired()])
    submit = SubmitField('Atualizar Usuário')