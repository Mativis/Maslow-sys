from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from models import db, User, Colaborador, Documento
from forms import LoginForm, ColaboradorForm, DocumentoForm, UsuarioForm
from utils import calcular_data_validade, get_documentos_vencidos, get_documentos_proximos_vencer
from datetime import datetime
import os
from werkzeug.utils import secure_filename
from flask_wtf.file import FileRequired # Importação necessária para manipular validação na edição

app = Flask(__name__)
app.config['SECRET_KEY'] = 'sua-chave-secreta-aqui'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///rh_documentos.db'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 128 * 1024 * 1024  # 16MB

# Inicializações
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Criar diretório de uploads
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@app.route('/')
@login_required
def dashboard():
    documentos_vencidos = get_documentos_vencidos()
    documentos_proximos = get_documentos_proximos_vencer()
    total_colaboradores = Colaborador.query.count()
    total_documentos = Documento.query.count()
    
    return render_template('dashboard.html', 
                         documentos_vencidos=documentos_vencidos,
                         documentos_proximos=documentos_proximos,
                         total_colaboradores=total_colaboradores,
                         total_documentos=total_documentos)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            flash(f'Bem-vindo, {user.username}!', 'success')
            return redirect(url_for('dashboard'))
        flash('Usuário ou senha inválidos', 'danger')
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Você saiu do sistema', 'info')
    return redirect(url_for('login'))

@app.route('/colaboradores')
@login_required
def colaboradores():
    if not current_user.has_permission('add_colaborador'):
        flash('Acesso não autorizado', 'warning')
        return redirect(url_for('dashboard'))
    
    colaboradores = Colaborador.query.all()
    return render_template('colaboradores.html', colaboradores=colaboradores)

@app.route('/colaborador/novo', methods=['GET', 'POST'])
@login_required
def novo_colaborador():
    if not current_user.has_permission('add_colaborador'):
        flash('Acesso não autorizado', 'warning')
        return redirect(url_for('dashboard'))
    
    form = ColaboradorForm()
    if form.validate_on_submit():
        try:
            colaborador = Colaborador(
                nome=form.nome.data,
                email=form.email.data,
                departamento=form.departamento.data,
                cargo=form.cargo.data,
                data_admissao=form.data_admissao.data
            )
            db.session.add(colaborador)
            db.session.commit()
            flash('Colaborador cadastrado com sucesso!', 'success')
            return redirect(url_for('colaboradores'))
        except Exception as e:
            db.session.rollback()
            flash('Erro ao cadastrar colaborador', 'danger')
    
    return render_template('colaborador_form.html', form=form, title='Novo Colaborador')

@app.route('/colaborador/editar/<int:colaborador_id>', methods=['GET', 'POST'])
@login_required
def editar_colaborador(colaborador_id):
    if not current_user.has_permission('add_colaborador'):
        flash('Acesso não autorizado', 'warning')
        return redirect(url_for('dashboard'))
    
    colaborador = Colaborador.query.get_or_404(colaborador_id)
    form = ColaboradorForm(obj=colaborador)
    
    if form.validate_on_submit():
        try:
            colaborador.nome = form.nome.data
            colaborador.email = form.email.data
            colaborador.departamento = form.departamento.data
            colaborador.cargo = form.cargo.data
            colaborador.data_admissao = form.data_admissao.data
            
            db.session.commit()
            flash('Colaborador atualizado com sucesso!', 'success')
            return redirect(url_for('colaboradores'))
        except Exception as e:
            db.session.rollback()
            flash('Erro ao atualizar colaborador', 'danger')
    
    return render_template('colaborador_form.html', form=form, colaborador=colaborador, title='Editar Colaborador')

# Rota de documentos do colaborador específico (ATUALIZADA com busca)
@app.route('/colaborador/<int:colaborador_id>/documentos')
@login_required
def documentos_colaborador(colaborador_id):
    colaborador = Colaborador.query.get_or_404(colaborador_id)
    
    # Lógica de pesquisa por nome do documento
    search_query = request.args.get('search', '').strip()
    
    query = Documento.query.filter_by(colaborador_id=colaborador_id)
    if search_query:
        # Busca insensível a caixa e parcial no nome do documento
        query = query.filter(Documento.nome.ilike(f'%{search_query}%'))
        
    documentos = query.all()
    
    return render_template('documentos_colaborador.html', 
                         colaborador=colaborador, 
                         documentos=documentos,
                         search_query=search_query) # Passa o termo de busca para o template

# Rota principal de documentos (mostra todos os colaboradores - ATUALIZADA com busca)
@app.route('/documentos')
@login_required
def documentos():
    # Lógica de pesquisa por nome do colaborador
    search_query = request.args.get('search', '').strip()
    
    query = Colaborador.query
    if search_query:
        # Busca insensível a caixa e parcial no nome do colaborador
        query = query.filter(Colaborador.nome.ilike(f'%{search_query}%'))
        
    colaboradores = query.all()
    
    # Contar documentos por colaborador
    for colaborador in colaboradores:
        colaborador.total_documentos = len(colaborador.documentos)
        colaborador.documentos_vencidos = len([d for d in colaborador.documentos if d.status_vencimento() == 'vencido'])
        colaborador.documentos_proximos = len([d for d in colaborador.documentos if d.status_vencimento() == 'proximo_vencer'])
    
    return render_template('documentos.html', colaboradores=colaboradores, search_query=search_query) # Passa o termo de busca para o template

# Rota para adicionar documento (ATUALIZADA para passar título)
@app.route('/documento/novo/<int:colaborador_id>', methods=['GET', 'POST'])
@login_required
def novo_documento(colaborador_id):
    if not current_user.has_permission('add_documento'):
        flash('Acesso não autorizado', 'warning')
        return redirect(url_for('documentos'))
    
    colaborador = Colaborador.query.get_or_404(colaborador_id)
    form = DocumentoForm()
    
    if form.validate_on_submit():
        try:
            arquivo = form.arquivo.data
            filename = secure_filename(arquivo.filename)
            arquivo_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            arquivo.save(arquivo_path)
            
            data_validade = calcular_data_validade(
                form.tipo_validade.data, 
                form.data_validade.data if form.tipo_validade.data == 'personalizado' else None
            )
            
            documento = Documento(
                colaborador_id=colaborador_id,
                nome=form.nome.data,
                tipo_validade=form.tipo_validade.data,
                data_validade=data_validade,
                arquivo=filename,
                observacoes=form.observacoes.data
            )
            
            db.session.add(documento)
            db.session.commit()
            flash('Documento adicionado com sucesso!', 'success')
            return redirect(url_for('documentos_colaborador', colaborador_id=colaborador_id))
        except Exception as e:
            db.session.rollback()
            flash('Erro ao adicionar documento', 'danger')
    
    return render_template('documento_form.html', form=form, colaborador=colaborador, title='Adicionar Novo Documento') # Título explícito

# Rota para editar documento (NOVA)
@app.route('/documento/editar/<int:documento_id>', methods=['GET', 'POST'])
@login_required
def editar_documento(documento_id):
    if not current_user.has_permission('edit_documento'):
        flash('Acesso não autorizado', 'warning')
        return redirect(url_for('documentos'))
    
    documento = Documento.query.get_or_404(documento_id)
    colaborador = Colaborador.query.get_or_404(documento.colaborador_id)
    
    # Preenche o formulário com os dados existentes
    form = DocumentoForm(obj=documento)
    
    # Remove a validação FileRequired para edição, permitindo que o campo de arquivo fique vazio
    form.arquivo.validators = [v for v in form.arquivo.validators if not isinstance(v, FileRequired)]

    if form.validate_on_submit():
        try:
            # 1. Tratar o upload do arquivo
            if form.arquivo.data and form.arquivo.data.filename:
                arquivo = form.arquivo.data
                filename = secure_filename(arquivo.filename)
                arquivo_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                
                # Deletar o arquivo antigo
                old_file_path = os.path.join(app.config['UPLOAD_FOLDER'], documento.arquivo)
                if os.path.exists(old_file_path):
                    os.remove(old_file_path)
                    
                arquivo.save(arquivo_path)
                documento.arquivo = filename # Atualiza o nome do arquivo no banco
            
            # 2. Recalcular a data de validade
            data_validade = calcular_data_validade(
                form.tipo_validade.data, 
                form.data_validade.data if form.tipo_validade.data == 'personalizado' else None
            )
            
            # 3. Atualizar campos do documento
            documento.nome = form.nome.data
            documento.tipo_validade = form.tipo_validade.data
            documento.data_validade = data_validade
            documento.observacoes = form.observacoes.data
            
            db.session.commit()
            flash('Documento atualizado com sucesso!', 'success')
            return redirect(url_for('documentos_colaborador', colaborador_id=colaborador.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar documento: {e}', 'danger')

    return render_template('documento_form.html', form=form, colaborador=colaborador, documento=documento, title='Editar Documento')

# Rota para excluir documento (NOVA)
@app.route('/documento/excluir/<int:documento_id>', methods=['POST'])
@login_required
def excluir_documento(documento_id):
    if not current_user.has_permission('delete_documento'):
        flash('Acesso não autorizado', 'warning')
        return redirect(url_for('documentos'))
    
    documento = Documento.query.get_or_404(documento_id)
    colaborador_id = documento.colaborador_id
    
    try:
        # 1. Deletar o arquivo do sistema de arquivos
        arquivo_path = os.path.join(app.config['UPLOAD_FOLDER'], documento.arquivo)
        if os.path.exists(arquivo_path):
            os.remove(arquivo_path)
            
        # 2. Deletar o registro do banco de dados
        db.session.delete(documento)
        db.session.commit()
        flash('Documento excluído com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir documento: {e}', 'danger')
        
    return redirect(url_for('documentos_colaborador', colaborador_id=colaborador_id))

@app.route('/download/<int:documento_id>')
@login_required
def download_documento(documento_id):
    if not current_user.has_permission('download'):
        flash('Acesso não autorizado', 'warning')
        return redirect(url_for('dashboard'))
    
    documento = Documento.query.get_or_404(documento_id)
    arquivo_path = os.path.join(app.config['UPLOAD_FOLDER'], documento.arquivo)
    
    if not os.path.exists(arquivo_path):
        flash('Arquivo não encontrado', 'danger')
        return redirect(url_for('documentos'))
    
    return send_file(arquivo_path, as_attachment=True)

@app.route('/usuarios')
@login_required
def usuarios():
    if current_user.role != 'administrador':
        flash('Acesso não autorizado', 'warning')
        return redirect(url_for('dashboard'))
    
    usuarios = User.query.all()
    return render_template('usuarios.html', usuarios=usuarios)

@app.route('/usuario/novo', methods=['GET', 'POST'])
@login_required
def novo_usuario():
    if current_user.role != 'administrador':
        flash('Acesso não autorizado', 'warning')
        return redirect(url_for('dashboard'))
    
    form = UsuarioForm()
    if form.validate_on_submit():
        try:
            # Verificar se usuário já existe
            if User.query.filter_by(username=form.username.data).first():
                flash('Usuário já existe', 'danger')
                return render_template('usuario_form.html', form=form)
            
            user = User(
                username=form.username.data,
                email=form.email.data,
                role=form.role.data
            )
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            flash('Usuário cadastrado com sucesso!', 'success')
            return redirect(url_for('usuarios'))
        except Exception as e:
            db.session.rollback()
            flash('Erro ao cadastrar usuário', 'danger')
    
    return render_template('usuario_form.html', form=form)

# Criar banco de dados e usuário admin padrão
with app.app_context():
    db.create_all()
    # Criar usuário admin padrão se não existir
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', email='admin@empresa.com', role='administrador')
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        print("Usuário admin criado: admin / admin123")

if __name__ == '__main__':
    app.run(debug=True)