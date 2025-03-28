import os
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_from_directory
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
import matplotlib.pyplot as plt
import io
import base64
import requests  # Adicionado para fazer requisições HTTP
import logging  # Adicionado para logs
from groq import Groq  # Adicionado para usar a biblioteca groq
import uuid  # Adicionado para gerar nomes únicos para as fotos
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
import random
from flask_talisman import Talisman

# Configuração de logs
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql://neondb_owner:npg_QL5klvR2mqSN@ep-orange-mud-a8vh3oi3-pooler.eastus2.azure.neon.tech/neondb?sslmode=require')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.getenv('SECRET_KEY', 'sua_chave_secreta')
app.config['SECURITY_PASSWORD_SALT'] = os.getenv('SECURITY_PASSWORD_SALT', 'seu_salt_de_seguranca')

# Dicionário para rastrear tentativas de login
login_attempts = {}

# Tempo de bloqueio após 5 tentativas falhas (exemplo: 15 minutos)
lockout_time = timedelta(minutes=15)
# Inicialização das extensões

app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'uploads')  # Definindo o caminho da pasta "uploads"
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}  # Extensões permitidas para os arquivos de imagem

# Certifique-se de que a pasta de upload exista
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Adicione esta linha para servir arquivos estáticos da pasta de uploads
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

bcrypt = Bcrypt(app)
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Configuração de segurança com Talisman
talisman = Talisman(app, content_security_policy=None)

# Função para verificar se o arquivo é permitido
def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Função para gerar um nome de arquivo único
def generate_unique_filename(filename):
    ext = filename.rsplit('.', 1)[1].lower()
    unique_filename = f"{uuid.uuid4().hex}.{ext}"
    return unique_filename

s = URLSafeTimedSerializer(app.config['SECRET_KEY'])

def send_reset_email(user_email):
    token = s.dumps(user_email, salt=app.config['SECURITY_PASSWORD_SALT'])
    reset_url = url_for('reset_with_token', token=token, _external=True)
    
    # Configuração do Flask-Mail para Gmail
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME', 'cod.trab@gmail.com')
    app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD', 'egfl xxbh zwmp eloo')
    app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER', 'cod.trab@gmail.com')

    mail = Mail(app)

    # Envio do email com o link de reset
    msg = Message('Redefinição de Senha', recipients=[user_email])
    msg.body = f'Clique no link para redefinir sua senha: {reset_url}'
    try:
        mail.send(msg)
        print(f'Clique no link para redefinir sua senha: {reset_url}')
    except Exception as e:
        print(f'Erro ao enviar email: {e}')
        flash('Erro ao enviar email de recuperação de senha. Tente novamente mais tarde.', 'error')

def send_verification_email(user_email, verification_code):
    # Configuração do Flask-Mail para Gmail
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME', 'cod.trab@gmail.com')
    app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD', 'egfl xxbh zwmp eloo')
    app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER', 'cod.trab@gmail.com')

    mail = Mail(app)

    # Envio do email com o código de verificação
    msg = Message('Código de Verificação', recipients=[user_email])
    msg.body = f'Seu código de verificação é: {verification_code}'
    try:
        mail.send(msg)
        print(f'Código de verificação enviado para: {user_email}')
    except Exception as e:
        print(f'Erro ao enviar email: {e}')
        flash('Erro ao enviar email de verificação. Tente novamente mais tarde.', 'error')

@app.route('/verificar_email', methods=['GET', 'POST'])
def verificar_email():
    if request.method == 'POST':
        email = request.form['email']
        verification_code = request.form['verification_code']
        stored_code = session.get('verification_code')
        if stored_code and verification_code == stored_code:
            flash('Email verificado com sucesso!', 'success')
            return redirect(url_for('login'))
        else:
            flash('Código de verificação inválido.', 'error')
    return render_template('verificar_email.html')

@app.route('/enviar_codigo_verificacao', methods=['POST'])
def enviar_codigo_verificacao():
    email = request.form['email']
    user = Usuario.query.filter_by(email=email).first()
    if user:
        verification_code = str(random.randint(100000, 999999))
        session['verification_code'] = verification_code
        send_verification_email(user.email, verification_code)
        flash('Um código de verificação foi enviado para seu email.', 'success')
        return redirect(url_for('verificar_email'))
    else:
        flash('Email não encontrado.', 'error')
        return redirect(url_for('register'))

@app.route('/recuperar_senha', methods=['GET', 'POST'])
def recuperar_senha():
    if request.method == 'POST':
        email = request.form['email']
        user = Usuario.query.filter_by(email=email).first()
        if user:
            send_reset_email(user.email)
            flash('Um link de recuperação de senha foi enviado para seu email.', 'success')
        else:
            flash('Email não encontrado.', 'error')
    return render_template('recuperar_senha.html')

@app.route('/reset/<token>', methods=['GET', 'POST'])
def reset_with_token(token):
    try:
        email = s.loads(token, salt=app.config['SECURITY_PASSWORD_SALT'], max_age=3600)
    except (SignatureExpired, BadSignature):
        flash('O link de recuperação de senha é inválido ou expirou.', 'error')
        return redirect(url_for('recuperar_senha'))

    if request.method == 'POST':
        senha = request.form['senha']
        confirmar_senha = request.form['confirmar_senha']
        if senha != confirmar_senha:
            flash('As senhas não coincidem.', 'error')
            return redirect(url_for('reset_with_token', token=token))
        
        user = Usuario.query.filter_by(email=email).first()
        if user:
            hashed_password = bcrypt.generate_password_hash(senha).decode('utf-8')
            user.senha = hashed_password
            db.session.commit()
            flash('Sua senha foi atualizada com sucesso!', 'success')
            return redirect(url_for('login'))
        else:
            flash('Usuário não encontrado.', 'error')
            return redirect(url_for('recuperar_senha'))

    return render_template('reset_senha.html', token=token)

class Casa(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    endereco = db.Column(db.String(200), nullable=True)
    num_moradores = db.Column(db.Integer, default=0)
    estado_emocional = db.Column(db.String(20), default="neutro")  # "feliz", "triste", "neutro", "animado", "relaxado", "irritado"
    nivel = db.Column(db.Integer, default=1)  # Nível da casa
    energia = db.Column(db.Integer, default=50)  # Energia da casa (0 a 100)

    moradores = db.relationship('Usuario', backref='casa', lazy=True)
    tarefas = db.relationship('Tarefa', backref='casa', lazy=True)  # Adicionado para permitir acesso às tarefas
    despesas = db.relationship('Despesa', backref='casa', lazy=True)  # Adicionado para permitir acesso às despesas

    def __repr__(self):
        return f'<Casa {self.nome}>'

    def atualizar_estado_emocional(self):
        tarefas_concluidas = sum(1 for tarefa in self.tarefas if tarefa.concluida)
        if tarefas_concluidas >= 10:
            self.estado_emocional = "animado"  # 🎉
        elif 5 <= tarefas_concluidas < 10:
            self.estado_emocional = "feliz"  # 😊
        elif 1 <= tarefas_concluidas < 5:
            self.estado_emocional = "relaxado"  # 😌
        elif tarefas_concluidas == 0:
            self.estado_emocional = "triste"  # 😢
        elif self.energia <= 20:
            self.estado_emocional = "irritado"  # 😡
        else:
            self.estado_emocional = "neutro"  # 😐
        db.session.commit()

    def obter_emoji_estado_emocional(self):
        emojis = {
            "animado": "🎉",
            "feliz": "😊",
            "relaxado": "😌",
            "triste": "😢",
            "irritado": "😡",
            "neutro": "😐"
        }
        return emojis.get(self.estado_emocional, "😐")

    def verificar_evolucao(self):
        tarefas_concluidas = sum(1 for tarefa in self.tarefas if tarefa.concluida)
        novo_nivel = (tarefas_concluidas // 5) + 1
        if novo_nivel > self.nivel:
            self.nivel = novo_nivel
            db.session.commit()
            return True  # Indica que houve evolução
        return False

    def ajustar_energia(self, delta):
        self.energia = max(0, min(100, self.energia + delta))
        db.session.commit()

    def verificar_eventos(self):
        if self.energia >= 80:
            return "surpresa"  # Evento positivo
        elif self.energia <= 20:
            return "crise"  # Evento negativo
        return None

class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    senha = db.Column(db.String(200), nullable=False)
    foto_url = db.Column(db.String(200), nullable=True)  # Adiciona o campo para a URL da foto

    casa_id = db.Column(db.Integer, db.ForeignKey('casa.id'), nullable=False)  # Relacionamento correto

    def __repr__(self):
        return f'<Usuario {self.nome}>'

class Tarefa(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    concluida = db.Column(db.Boolean, default=False)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    foto = db.Column(db.String(120), nullable=True)

    casa_id = db.Column(db.Integer, db.ForeignKey('casa.id'), nullable=False)  # Relacionado à Casa
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=True)
    usuario = db.relationship('Usuario', backref='tarefas_concluidas')

class Despesa(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    descricao = db.Column(db.String(100), nullable=False)
    valor = db.Column(db.Float, nullable=False)
    data_vencimento = db.Column(db.DateTime, nullable=False)
    pago = db.Column(db.Boolean, default=False)
    
    casa_id = db.Column(db.Integer, db.ForeignKey('casa.id'), nullable=False)  # Relacionado à Casa


@app.route('/')
def home():
    if 'usuario_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.form
        email = data['email'].strip().lower()
        senha = data['senha']

        # Verifica se o usuário está bloqueado por tentativas falhas
        if email in login_attempts and login_attempts[email]['locked_until'] > datetime.now():
            flash('Muitas tentativas falhas. Tente novamente mais tarde.', 'error')
            return render_template('login.html')

        usuario = Usuario.query.filter_by(email=email).first()

        if usuario and bcrypt.check_password_hash(usuario.senha, senha):
            session['usuario_id'] = usuario.id  # Armazena o ID do usuário na sessão
            session['usuario_nome'] = usuario.nome  # Opcional, para exibir no template
            
            # Resetar tentativas de login após sucesso
            login_attempts.pop(email, None)

            flash('Login bem-sucedido!', 'success')
            return redirect(url_for('dashboard'))
        
        # Se falhar, incrementar tentativas de login
        if not usuario:
            flash('Email não encontrado', 'error')
        elif not bcrypt.check_password_hash(usuario.senha, senha):
            flash('Senha incorreta', 'error')

        if email not in login_attempts:
            login_attempts[email] = {'attempts': 1, 'locked_until': datetime.now()}
        else:
            login_attempts[email]['attempts'] += 1
            if login_attempts[email]['attempts'] >= 5:
                login_attempts[email]['locked_until'] = datetime.now() + lockout_time
                flash('Muitas tentativas falhas. Conta temporariamente bloqueada.', 'error')

    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))  # Redireciona para login se não estiver logado

    usuario_id = session['usuario_id']

    # Buscar informações do usuário
    usuario = Usuario.query.get(usuario_id)

    if not usuario:
        flash("Usuário não encontrado!", "error")
        return redirect(url_for('login'))

    # Buscar informações da casa associada ao usuário
    casa = Casa.query.get(usuario.casa_id)
    casa.atualizar_estado_emocional()
    evento = casa.verificar_eventos()
    evoluiu = casa.verificar_evolucao()

    # Buscar todas as tarefas da casa do usuário
    tarefas = Tarefa.query.filter_by(casa_id=usuario.casa_id).all()

    # Buscar total de despesas do usuário nos últimos 30 dias
    data_limite = datetime.utcnow() - timedelta(days=30)
    total_despesas = db.session.query(
        db.func.coalesce(db.func.sum(Despesa.valor), 0)
    ).filter(
        Despesa.casa_id == usuario.casa_id,
        Despesa.data_vencimento >= data_limite
    ).scalar()

    # Buscar número de moradores na casa do usuário
    num_moradores = Usuario.query.filter_by(casa_id=usuario.casa_id).count() if casa else 0

    # Calcular ranking de usuários por tarefas concluídas
    ranking_usuarios = db.session.query(
        Usuario.nome, Usuario.foto_url.label('foto_perfil_url'), db.func.count(Tarefa.id).label('tarefas_concluidas')
    ).join(Tarefa, Tarefa.usuario_id == Usuario.id).filter(
        Tarefa.concluida == True, Usuario.casa_id == usuario.casa_id
    ).group_by(Usuario.id).order_by(db.func.count(Tarefa.id).desc()).all()

    return render_template('dashboard.html', 
                           usuario=usuario, 
                           tarefas=tarefas,
                           total_despesas=total_despesas, 
                           num_moradores=num_moradores, 
                           casa=casa,
                           ranking_usuarios=ranking_usuarios,
                           evento=evento, 
                           evoluiu=evoluiu)

@app.route('/logout')
def logout():
    session.pop('usuario_id', None)
    session.pop('usuario_nome', None)
    return redirect(url_for('login'))

@app.route('/tasks', methods=['GET', 'POST'])
def tasks():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    usuario_id = session['usuario_id']
    usuario = Usuario.query.get(usuario_id)

    if request.method == 'POST':
        titulo = request.form['titulo']
        descricao = request.form['descricao']
        foto = request.files['foto']

        if foto and allowed_file(foto.filename):
            filename = generate_unique_filename(foto.filename)
            foto.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            foto_url = filename
        else:
            foto_url = None

        nova_tarefa = Tarefa(
            titulo=titulo,
            descricao=descricao,
            foto=foto_url,
            casa_id=usuario.casa_id
        )
        db.session.add(nova_tarefa)
        db.session.commit()
        flash('Tarefa adicionada com sucesso!', 'success')
        return redirect(url_for('tasks'))

    tarefas = Tarefa.query.filter_by(casa_id=usuario.casa_id).order_by(Tarefa.data_criacao.desc()).all()
    return render_template('tasks.html', tarefas=tarefas)

@app.route('/tasks/concluir/<int:tarefa_id>', methods=['POST'])
def concluir_tarefa(tarefa_id):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    usuario = Usuario.query.get(session['usuario_id'])
    tarefa = Tarefa.query.get(tarefa_id)

    if tarefa and tarefa.casa_id == usuario.casa_id:
        tarefa.concluida = True
        tarefa.usuario_id = usuario.id  # Registra quem concluiu

        # Anexar imagem de prova, se fornecida
        foto_prova = request.files.get('foto_prova')
        if foto_prova and allowed_file(foto_prova.filename):
            filename = generate_unique_filename(foto_prova.filename)
            foto_prova.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            tarefa.foto = filename

        db.session.commit()
        flash(f"Tarefa '{tarefa.titulo}' concluída por {usuario.nome}!", "success")
    else:
        flash("Erro ao concluir tarefa.", "danger")

    return redirect(url_for('tasks'))

@app.route('/expenses', methods=['GET', 'POST'])
def expenses():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    usuario = Usuario.query.get(session['usuario_id'])
    
    # Se o formulário foi enviado (POST) para adicionar uma nova despesa
    if request.method == 'POST' and 'descricao' in request.form:
        descricao = request.form['descricao']
        valor = float(request.form['valor'])
        data_vencimento = datetime.strptime(request.form['data_vencimento'], '%Y-%m-%d')

        if not descricao or valor <= 0:
            flash("Descrição e valor devem ser preenchidos corretamente!", "error")
            return redirect(url_for('expenses'))

        # Criar nova despesa
        nova_despesa = Despesa(
            descricao=descricao,
            valor=valor,
            data_vencimento=data_vencimento,
            pago=False,
            casa_id=usuario.casa_id
        )

        db.session.add(nova_despesa)
        db.session.commit()
        flash("Despesa adicionada com sucesso!", "success")
        return redirect(url_for('expenses'))
    
    # Se o formulário foi enviado para editar uma despesa
    if request.method == 'POST' and 'despesa_id' in request.form:
        despesa_id = request.form['despesa_id']
        descricao = request.form['descricao']
        valor = float(request.form['valor'])
        data_vencimento = datetime.strptime(request.form['data_vencimento'], '%Y-%m-%d')
        pago = 'pago' in request.form  # Verifica se o campo "pago" foi marcado

        despesa = Despesa.query.get(despesa_id)
        if despesa and despesa.casa_id == usuario.casa_id:
            despesa.descricao = descricao
            despesa.valor = valor
            despesa.data_vencimento = data_vencimento
            despesa.pago = pago
            db.session.commit()
            flash("Despesa atualizada com sucesso!", "success")
        else:
            flash("Erro ao atualizar a despesa. Tente novamente.", "error")
        
        return redirect(url_for('expenses'))

    # Paginação
    page = request.args.get('page', 1, type=int)
    per_page = 6  # Número de despesas por página
    despesas_paginadas = Despesa.query.filter_by(casa_id=usuario.casa_id).order_by(Despesa.data_vencimento.desc()).paginate(page=page, per_page=per_page)

    # Somar o total de despesas não pagas
    total_despesas = sum(d.valor for d in Despesa.query.filter_by(casa_id=usuario.casa_id).all() if not d.pago)

    # Buscar número de moradores na casa
    num_moradores = Usuario.query.filter_by(casa_id=usuario.casa_id).count()

    # Calcular divisão da despesa
    valor_por_pessoa = total_despesas / num_moradores if num_moradores > 0 else 0

    return render_template('expenses.html', 
                           despesas=despesas_paginadas.items, 
                           total_despesas=total_despesas, 
                           num_moradores=num_moradores, 
                           valor_por_pessoa=valor_por_pessoa,
                           pagination=despesas_paginadas)

@app.route('/editar_despesa/<int:despesa_id>', methods=['GET', 'POST'])
def editar_despesa(despesa_id):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    usuario = Usuario.query.get(session['usuario_id'])
    despesa = Despesa.query.get_or_404(despesa_id)

    # Verifica se o usuário é o proprietário da despesa
    if despesa.casa.id != usuario.casa_id:
        flash("Você não tem permissão para editar essa despesa.", "error")
        return redirect(url_for('expenses'))

    if request.method == 'POST':
        descricao = request.form['descricao']
        valor = float(request.form['valor'])
        data_vencimento = datetime.strptime(request.form['data_vencimento'], '%Y-%m-%d')
        pago = 'pago' in request.form  # Verifica se o campo "pago" foi marcado

        # Atualiza a despesa com os novos dados
        despesa.descricao = descricao
        despesa.valor = valor
        despesa.data_vencimento = data_vencimento
        despesa.pago = pago
        db.session.commit()

        flash("Despesa atualizada com sucesso!", "success")
        return redirect(url_for('expenses'))

    return render_template('editar_despesa.html', despesa=despesa)


@app.route('/house_info', methods=['GET', 'POST'])
def house_info():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    usuario = Usuario.query.get(session['usuario_id'])
    casa = Casa.query.get(usuario.casa_id)

    # Se o método for POST, ou seja, o formulário foi enviado
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        
        # Verifica se o e-mail já está em uso
        if Usuario.query.filter_by(email=email).first():
            flash('Esse morador já existe!', 'danger')
            return redirect(url_for('house_info'))  # Redireciona para a página de casa/moradores

        # Cria o novo morador
        novo_morador = Usuario(nome=nome, email=email, casa_id=casa.id)

        # Adiciona o morador ao banco de dados
        db.session.add(novo_morador)
        db.session.commit()

        # Atualiza o número de moradores na casa
        casa.num_moradores += 1
        db.session.commit()

        flash('Morador adicionado com sucesso!', 'success')
        return redirect(url_for('house_info'))  # Redireciona para a página de casa/moradores
    
    # Se o método for GET, apenas exibe os dados
    moradores = Usuario.query.filter_by(casa_id=casa.id).all()
    return render_template('house_info.html', casa=casa, moradores=moradores)

# Variável de ambiente para a chave da API
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

def analyze_house_data(casa_id):
    # Buscar dados da casa
    despesas = Despesa.query.filter_by(casa_id=casa_id).all()
    tarefas = Tarefa.query.filter_by(casa_id=casa_id).all()
    moradores = Usuario.query.filter_by(casa_id=casa_id).all()

    # Análise financeira
    total_gasto = sum(despesa.valor for despesa in despesas)
    despesas_pagas = sum(despesa.valor for despesa in despesas if despesa.pago)
    despesas_pendentes = total_gasto - despesas_pagas

    # Média de gastos por morador
    total_moradores = len(moradores) if moradores else 1
    media_gasto_por_morador = total_gasto / total_moradores

    # Análise de tarefas
    total_tarefas = len(tarefas)
    tarefas_concluidas = sum(1 for tarefa in tarefas if tarefa.concluida)
    tarefas_pendentes = total_tarefas - tarefas_concluidas
    percentual_tarefas_concluidas = (tarefas_concluidas / total_tarefas * 100) if total_tarefas > 0 else 0

    # Preparação dos dados
    data = {
        "total_gasto": total_gasto,
        "despesas_pagas": despesas_pagas,
        "despesas_pendentes": despesas_pendentes,
        "media_gasto_por_morador": round(media_gasto_por_morador, 2),
        "total_tarefas": total_tarefas,
        "tarefas_concluidas": tarefas_concluidas,
        "tarefas_pendentes": tarefas_pendentes,
        "percentual_tarefas_concluidas": round(percentual_tarefas_concluidas, 2),
        "total_moradores": total_moradores
    }

    # Enviar para API externa usando a biblioteca groq (se chave estiver definida)
    if GROQ_API_KEY:
        try:
            logging.info("Enviando dados para a API externa...")
            client = Groq(api_key=GROQ_API_KEY)
            response = client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": f"Analise os seguintes dados da casa em português e forneça uma análise breve e organizada: {data}"
                    }
                ],
                model="gemma2-9b-it",
                temperature=0.6,
                max_tokens=350,
                top_p=1,
                stream=False,
                stop=None,
            )
            analysis = response.choices[0].message.content
            logging.info("Análise da API externa concluída com sucesso.")
            return {"insights_ia": analysis}
        except Exception as e:
            logging.error(f"Erro ao tentar analisar dados via API externa: {e}")
            return {"error": "Erro ao tentar analisar dados via API externa"}

    return data  # Retorna os dados locais se a API não estiver configurada

@app.route('/analisar_dados')
def analyze():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    usuario = Usuario.query.get(session['usuario_id'])
    casa_id = usuario.casa_id

    analysis = analyze_house_data(casa_id)

    if "error" in analysis:
        flash(analysis["error"], "error")
        return jsonify({"error": analysis["error"]})

    return jsonify(analysis)

from flask import flash, redirect, url_for, request
from flask_bcrypt import Bcrypt
from sqlalchemy.exc import IntegrityError
import requests
from flask_mail import Mail, Message
bcrypt = Bcrypt(app)  # Se não foi feito ainda, você precisa inicializar o Bcrypt com o app Flask

@app.route('/adicionar_morador', methods=['POST'])
def adicionar_morador():
    nome = request.form.get('nome')
    email = request.form.get('email')
    senha = request.form.get('senha')  # Captura a senha do formulário
    foto = request.files.get('foto')  # Captura a foto do formulário

    # Verifica se o usuário está logado
    if 'usuario_id' not in session:
        flash("Você precisa estar logado para adicionar um morador.", "error")
        return redirect(url_for('login'))
    
    usuario_logado = Usuario.query.get(session['usuario_id'])
    casa_id_logado = usuario_logado.casa_id  # Pega a casa do usuário logado

    # Validação dos campos
    if not nome or not email or not senha or not foto:
        flash("Todos os campos são obrigatórios!", "error")
        return redirect(url_for('house_info'))

    # Verificar se o e-mail já está cadastrado
    morador_existente = Usuario.query.filter_by(email=email).first()
    if morador_existente:
        flash("Já existe um morador com esse e-mail!", "error")
        return redirect(url_for('house_info'))

    # Gerar o hash da senha
    hashed_password = bcrypt.generate_password_hash(senha).decode('utf-8')

    # Salvar a foto no servidor
    if foto and allowed_file(foto.filename):
        filename = generate_unique_filename(foto.filename)
        foto.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        foto_url = url_for('uploaded_file', filename=filename)
    else:
        foto_url = None

    try:
        # Adiciona o novo morador, associando à casa do usuário logado
        novo_morador = Usuario(nome=nome, email=email, senha=hashed_password, casa_id=casa_id_logado, foto_url=foto_url)
        db.session.add(novo_morador)
        db.session.commit()

        flash("Morador adicionado com sucesso!", "success")
    except IntegrityError:
        db.session.rollback()  # Rollback em caso de erro de integridade (ex: chave duplicada)
        flash("Erro ao adicionar o morador. Tente novamente.", "error")

    return redirect(url_for('house_info'))

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/editar_morador/<int:morador_id>', methods=['GET', 'POST'])
def editar_morador(morador_id):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    # Buscar o morador pelo ID fornecido
    morador = Usuario.query.get_or_404(morador_id)
    
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        foto = request.files.get('foto')  # Captura a foto do formulário
        
        # Verifica se o email já está em uso
        if email != morador.email and Usuario.query.filter_by(email=email).first():
            flash('Este email já está em uso por outro morador!', 'danger')
            return redirect(url_for('house_info'))  # Volta para a página de casa/moradores

        # Atualiza os dados do morador
        morador.nome = nome
        morador.email = email

        # Atualiza a foto do morador, se fornecida
        if foto and allowed_file(foto.filename):
            filename = generate_unique_filename(foto.filename)
            foto.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            morador.foto_url = url_for('uploaded_file', filename=filename)

        db.session.commit()

        flash('Morador atualizado com sucesso!', 'success')
        return redirect(url_for('house_info'))  # Redireciona de volta para a página de casa/moradores
    
    return render_template('editar_morador.html', morador=morador)  # Se for GET, exibe o formulário de edição

@app.route('/register', methods=['POST', 'GET'])
def register():
    if request.method == 'POST':
        if 'send_code' in request.form:
            email = request.form['email']
            user = Usuario.query.filter_by(email=email).first()
            if user:
                flash("Email já registrado", "error")
                return redirect(url_for('register'))
            verification_code = str(random.randint(100000, 999999))
            session['verification_code'] = verification_code
            send_verification_email(email, verification_code)
            flash('Um código de verificação foi enviado para seu email.', 'success')
            return render_template('register.html', email=email, code_sent=True)
        
        elif 'verify_code' in request.form:
            email = request.form['email']
            verification_code = request.form['verification_code']
            stored_code = session.get('verification_code')
            if stored_code and verification_code == stored_code:
                flash('Email verificado com sucesso!', 'success')
                return render_template('register.html', email=email, email_verified=True)
            else:
                flash('Código de verificação inválido.', 'error')
                return render_template('register.html', email=email, code_sent=True)
        
        else:
            nome = request.form['nome']
            email = request.form['email']
            senha = request.form['senha']
            confirmar_senha = request.form['confirmar-senha']
            nome_casa = request.form['nome-casa']
            
            if not all([nome, email, senha, confirmar_senha, nome_casa]):
                flash("Todos os campos são obrigatórios", "error")
                return redirect(url_for('register'))
            
            if senha != confirmar_senha:
                flash("As senhas não coincidem", "error")
                return redirect(url_for('register'))
            
            if Usuario.query.filter_by(email=email).first():
                flash("Email já registrado", "error")
                return redirect(url_for('register'))
            
            nova_casa = Casa(nome=nome_casa)
            db.session.add(nova_casa)
            db.session.commit()
            
            hashed_password = bcrypt.generate_password_hash(senha).decode('utf-8')
            novo_usuario = Usuario(nome=nome, email=email, senha=hashed_password, casa_id=nova_casa.id)
            db.session.add(novo_usuario)
            db.session.commit()
            
            flash("Cadastro realizado com sucesso! Faça login para continuar.", "success")
            return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/grafico_gastos')
def grafico_gastos():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    usuario = Usuario.query.get(session['usuario_id'])
    casa_id = usuario.casa_id

    # Buscar todas as despesas da casa do usuário
    despesas = Despesa.query.filter_by(casa_id=casa_id).all()

    # Preparar dados para o gráfico
    datas = [despesa.data_vencimento.strftime('%Y-%m') for despesa in despesas]
    valores = [despesa.valor for despesa in despesas]
    descricoes = [despesa.descricao for despesa in despesas]

    # Preparar dados para o gráfico de pizza
    categorias = list(set(descricoes))
    valores_por_categoria = [sum(despesa.valor for despesa in despesas if despesa.descricao == categoria) for categoria in categorias]

    # Criar gráfico de pizza
    plt.figure(figsize=(10, 7))
    plt.pie(valores_por_categoria, labels=categorias, autopct='%1.1f%%', startangle=140, colors=plt.cm.Paired.colors)
    plt.title('Distribuição de Gastos por Categoria')
    plt.axis('equal')  # Assegura que o gráfico seja desenhado como um círculo

    # Salvar gráfico em um buffer
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    image_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
    buf.close()

    return render_template('grafico_gastos.html', image_base64=image_base64)

@app.route('/manifest.json')
def manifest():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'manifest.json')

@app.route('/service-worker.js')
def service_worker():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'service-worker.js')

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)), debug=True)