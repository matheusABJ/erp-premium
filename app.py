import os
from flask import Flask, request, redirect, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
import matplotlib
matplotlib.use("Agg")  # IMPORTANTE para Render
import matplotlib.pyplot as plt
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4

app = Flask(__name__)
app.config['SECRET_KEY'] = 'erp_super_seguro'

# Corrige DATABASE_URL do Render
database_url = os.environ.get("DATABASE_URL")

if database_url:
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///erp.db"

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)

# ---------------- MODELOS ----------------

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(200))
    nivel = db.Column(db.String(20))

class Funcionario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100))
    escala = db.Column(db.String(20))
    salario = db.Column(db.Float)

class Registro(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    funcionario = db.Column(db.String(100))
    tipo = db.Column(db.String(20))

with app.app_context():
    db.create_all()
    if User.query.count() == 0:
        for i in range(1, 11):
            db.session.add(User(
                username=f"admin{i}",
                password=generate_password_hash("1234"),
                nivel="admin"
            ))
        db.session.commit()

# ---------------- LOGIN ----------------

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route("/", methods=["GET","POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(username=request.form["user"]).first()
        if user and check_password_hash(user.password, request.form["pass"]):
            login_user(user)
            return redirect("/dashboard")
        return "Login inválido"
    return """
    <h2>ERP Premium - Login</h2>
    <form method="post">
    Usuário: <input name="user"><br>
    Senha: <input name="pass" type="password"><br>
    <button>Entrar</button>
    </form>
    """

# ---------------- DASHBOARD ----------------

@app.route("/dashboard")
@login_required
def dashboard():

    faltas = Registro.query.filter_by(tipo="falta").count()
    advert = Registro.query.filter_by(tipo="advertencia").count()
    atest = Registro.query.filter_by(tipo="atestado").count()

    plt.figure()
    plt.pie([faltas or 1, advert or 1, atest or 1],
            labels=["Faltas","Advertências","Atestados"],
            autopct='%1.1f%%')
    plt.title("Relatório Geral")
    plt.savefig("grafico.png")
    plt.close()

    total_func = Funcionario.query.count()

    return f"""
    <h1>Painel Executivo ERP</h1>
    <p>Total Funcionários: {total_func}</p>
    <img src='/grafico'><br><br>
    <a href='/funcionarios'>Cadastrar Funcionários</a><br>
    <a href='/relatorio_pdf'>Gerar Relatório PDF</a><br>
    <a href='/logout'>Sair</a>
    """

@app.route("/grafico")
@login_required
def grafico():
    return send_file("grafico.png", mimetype='image/png')

# ---------------- FUNCIONÁRIOS ----------------

@app.route("/funcionarios", methods=["GET","POST"])
@login_required
def funcionarios():
    if request.method == "POST":
        db.session.add(Funcionario(
            nome=request.form["nome"],
            escala=request.form["escala"],
            salario=float(request.form["salario"])
        ))
        db.session.commit()

    lista = Funcionario.query.all()
    html = "<h2>Cadastro Funcionários</h2>"
    html += """
    <form method="post">
    Nome: <input name="nome"><br>
    Escala:
    <select name="escala">
    <option>12x36</option>
    <option>6x42</option>
    <option>5x2</option>
    </select><br>
    Salário: <input name="salario"><br>
    <button>Adicionar</button>
    </form><br>
    """

    for f in lista:
        html += f"<p>{f.nome} - {f.escala} - R${f.salario}</p>"

    html += "<br><a href='/dashboard'>Voltar</a>"
    return html

# ---------------- PDF ----------------

@app.route("/relatorio_pdf")
@login_required
def relatorio_pdf():

    arquivo = "relatorio_mensal.pdf"
    doc = SimpleDocTemplate(arquivo,pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("RELATÓRIO MENSAL ERP", styles['Title']))
    elements.append(Spacer(1,20))

    dados = [["Funcionário","Escala","Salário"]]

    for f in Funcionario.query.all():
        dados.append([f.nome,f.escala,str(f.salario)])

    tabela = Table(dados)
    elements.append(tabela)

    doc.build(elements)
    return send_file(arquivo, as_attachment=True)

@app.route("/logout")
def logout():
    logout_user()
    return redirect("/")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
