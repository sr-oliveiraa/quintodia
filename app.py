import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///task_manager.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'sua_chave_secreta'
# Inicialização das extensões

app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'uploads')  # Definindo o caminho da pasta "uploads"
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}  # Extensões permitidas para os arquivos de imagem

# Certifique-se de que a pasta de upload exista
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])
bcrypt = Bcrypt(app)
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Função para verificar se o arquivo é permitido
def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Modelo Casa
# Modelo Casa
class Casa(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    endereco = db.Column(db.String(200), nullable=True)
    num_moradores = db.Column(db.Integer, default=0)  # Campo para armazenar o número de moradores
    moradores = db.relationship('Usuario', backref='casa', lazy=True)

    def __repr__(self):
        return f'<Casa {self.nome}>'

class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    senha = db.Column(db.String(200), nullable=False)  # Garantindo que o campo senha não seja nulo
    casa_id = db.Column(db.Integer, db.ForeignKey('casa.id'), nullable=False)  # Relacionamento com a tabela Casa
    tarefas = db.relationship('Tarefa', backref='usuario', lazy=True)
    despesas = db.relationship('Despesa', backref='usuario', lazy=True)

    # Método para representar o usuário de forma mais legível
    def __repr__(self):
        return f'<Usuario {self.nome}>'


# Modelo Tarefa
class Tarefa(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    concluida = db.Column(db.Boolean, default=False)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    foto = db.Column(db.String(120), nullable=True)  # Coluna para a imagem


# Modelo Despesa
class Despesa(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    descricao = db.Column(db.String(100), nullable=False)
    valor = db.Column(db.Float, nullable=False)
    data_vencimento = db.Column(db.DateTime, nullable=False)
    pago = db.Column(db.Boolean, default=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)

@app.route('/')
def home():
    if 'usuario_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.form
        usuario = Usuario.query.filter_by(email=data['email']).first()
        
        if usuario and bcrypt.check_password_hash(usuario.senha, data['senha']):
            session['usuario_id'] = usuario.id  # Armazena o ID do usuário na sessão
            session['usuario_nome'] = usuario.nome  # Opcional, para exibir no template
            return redirect(url_for('dashboard'))
        
        flash('Credenciais inválidas', 'error')
    
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

    # Buscar total de tarefas do usuário
    total_tarefas = Tarefa.query.filter_by(usuario_id=usuario_id).count()

    # Buscar total de despesas do usuário
    total_despesas = db.session.query(db.func.coalesce(db.func.sum(Despesa.valor), 0)).filter_by(usuario_id=usuario_id).scalar()

    # Buscar número de moradores na casa do usuário
    num_moradores = Usuario.query.filter_by(casa_id=usuario.casa_id).count() if casa else 0

    return render_template('dashboard.html', 
                           usuario=usuario, 
                           total_tarefas=total_tarefas,
                           total_despesas=total_despesas, 
                           num_moradores=num_moradores, 
                           casa=casa)


@app.route('/logout')
def logout():
    session.pop('usuario_id', None)
    session.pop('usuario_nome', None)
    return redirect(url_for('login'))

@app.route('/tasks', methods=['GET', 'POST'])
def tasks():
    # Verifica se o usuário está logado
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    usuario = Usuario.query.get(session['usuario_id'])
    
    # Ação para criar nova tarefa
    if request.method == 'POST':
        titulo = request.form['titulo']
        descricao = request.form['descricao']
        foto = None
        
        # Verifica se existe arquivo para upload
        if 'foto' in request.files:
            file = request.files['foto']
            if file and allowed_file(file.filename):
                foto = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], foto))

        # Cria uma nova tarefa e a adiciona ao banco de dados
        nova_tarefa = Tarefa(titulo=titulo, descricao=descricao, foto=foto, usuario_id=usuario.id, concluida=False)
        db.session.add(nova_tarefa)
        db.session.commit()
        flash("Tarefa adicionada com sucesso!", "success")
        return redirect(url_for('tasks'))
    
    # Obtém todas as tarefas do usuário logado
    tarefas = Tarefa.query.filter_by(usuario_id=usuario.id).all()
    return render_template('tasks.html', tarefas=tarefas)

@app.route('/concluir_tarefa/<int:tarefa_id>', methods=['POST'])
def concluir_tarefa(tarefa_id):
    # Marca uma tarefa como concluída
    tarefa = Tarefa.query.get(tarefa_id)
    if tarefa:
        tarefa.concluida = True
        db.session.commit()
        flash("Tarefa marcada como concluída!", "success")
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
            usuario_id=usuario.id
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
        if despesa and despesa.usuario_id == usuario.id:
            despesa.descricao = descricao
            despesa.valor = valor
            despesa.data_vencimento = data_vencimento
            despesa.pago = pago
            db.session.commit()
            flash("Despesa atualizada com sucesso!", "success")
        else:
            flash("Erro ao atualizar a despesa. Tente novamente.", "error")
        
        return redirect(url_for('expenses'))

    # Buscar todas as despesas do usuário
    despesas = Despesa.query.filter_by(usuario_id=usuario.id).all()

    # Somar o total de despesas
    total_despesas = sum(d.valor for d in despesas)

    # Buscar número de moradores na casa
    num_moradores = Usuario.query.filter_by(casa_id=usuario.casa_id).count()

    # Calcular divisão da despesa
    valor_por_pessoa = total_despesas / num_moradores if num_moradores > 0 else 0

    return render_template('expenses.html', 
                           despesas=despesas, 
                           total_despesas=total_despesas, 
                           num_moradores=num_moradores, 
                           valor_por_pessoa=valor_por_pessoa)
@app.route('/editar_despesa/<int:despesa_id>', methods=['GET', 'POST'])
def editar_despesa(despesa_id):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    usuario = Usuario.query.get(session['usuario_id'])
    despesa = Despesa.query.get_or_404(despesa_id)

    # Verifica se o usuário é o proprietário da despesa
    if despesa.usuario_id != usuario.id:
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


@app.route('/add_resident', methods=['GET', 'POST'])
def add_resident():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        
        # Verifica se o email já está em uso por outro morador
        if Usuario.query.filter_by(email=email).first():
            flash('Este email já está em uso por outro morador!', 'danger')
            return redirect(url_for('house_info'))  # Volta para a página de casa/moradores

        # Cria um novo morador
        novo_morador = Usuario(nome=nome, email=email)
        db.session.add(novo_morador)
        db.session.commit()

        flash('Morador adicionado com sucesso!', 'success')
        return redirect(url_for('house_info'))  # Redireciona para a página de casa/moradores

    return render_template('add_resident.html')  # Se for GET, exibe o formulário de adição


from flask import flash, redirect, url_for, request
from flask_bcrypt import Bcrypt
from sqlalchemy.exc import IntegrityError
bcrypt = Bcrypt(app)  # Se não foi feito ainda, você precisa inicializar o Bcrypt com o app Flask

@app.route('/adicionar_morador', methods=['POST'])
def adicionar_morador():
    nome = request.form.get('nome')
    email = request.form.get('email')
    senha = request.form.get('senha')  # Captura a senha do formulário

    # Validação dos campos
    if not nome or not email or not senha:
        flash("Todos os campos são obrigatórios!", "error")
        return redirect(url_for('house_info'))

    # Verificar se o e-mail já está cadastrado
    morador_existente = Usuario.query.filter_by(email=email).first()
    if morador_existente:
        flash("Já existe um morador com esse e-mail!", "error")
        return redirect(url_for('house_info'))

    # Gerar o hash da senha
    hashed_password = bcrypt.generate_password_hash(senha).decode('utf-8')

    try:
        # Adiciona o novo morador (ajuste o casa_id conforme necessário)
        novo_morador = Usuario(nome=nome, email=email, senha=hashed_password, casa_id=1)
        db.session.add(novo_morador)
        db.session.commit()

        flash("Morador adicionado com sucesso!", "success")
    except IntegrityError:
        db.session.rollback()  # Rollback em caso de erro de integridade (ex: chave duplicada)
        flash("Erro ao adicionar o morador. Tente novamente.", "error")

    return redirect(url_for('house_info'))




@app.route('/editar_morador/<int:morador_id>', methods=['GET', 'POST'])
def editar_morador(morador_id):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    # Buscar o morador pelo ID fornecido
    morador = Usuario.query.get_or_404(morador_id)
    
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        
        # Verifica se o email já está em uso
        if email != morador.email and Usuario.query.filter_by(email=email).first():
            flash('Este email já está em uso por outro morador!', 'danger')
            return redirect(url_for('house_info'))  # Volta para a página de casa/moradores

        # Atualiza os dados do morador
        morador.nome = nome
        morador.email = email
        db.session.commit()

        flash('Morador atualizado com sucesso!', 'success')
        return redirect(url_for('house_info'))  # Redireciona de volta para a página de casa/moradores
    
    return render_template('editar_morador.html', morador=morador)  # Se for GET, exibe o formulário de edição




@app.route('/register', methods=['POST', 'GET'])
def register():
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        senha = request.form['senha']
        confirmar_senha = request.form['confirmar-senha']
        nome_casa = request.form['nome-casa']
        endereco = request.form['endereco']
        
        if not all([nome, email, senha, confirmar_senha, nome_casa, endereco]):
            flash("Todos os campos são obrigatórios", "error")
            return redirect(url_for('register'))
        
        if senha != confirmar_senha:
            flash("As senhas não coincidem", "error")
            return redirect(url_for('register'))
        
        if Usuario.query.filter_by(email=email).first():
            flash("Email já registrado", "error")
            return redirect(url_for('register'))
        
        nova_casa = Casa(nome=nome_casa, endereco=endereco)
        db.session.add(nova_casa)
        db.session.commit()
        
        hashed_password = bcrypt.generate_password_hash(senha).decode('utf-8')
        novo_usuario = Usuario(nome=nome, email=email, senha=hashed_password, casa_id=nova_casa.id)
        db.session.add(novo_usuario)
        db.session.commit()
        
        flash("Cadastro realizado com sucesso! Faça login para continuar.", "success")
        return redirect(url_for('login'))
    
    return render_template('register.html')

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
