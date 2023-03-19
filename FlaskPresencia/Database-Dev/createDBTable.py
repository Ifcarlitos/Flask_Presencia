from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from config import config
from flask_bcrypt import Bcrypt

app = Flask(__name__)
app.config.from_object(config['development'])
db = SQLAlchemy(app)

#Modelos de la base de datos:
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable = False, unique=True)
    password = db.Column(db.String(250), nullable = False)
    nombre = db.Column(db.String(250), nullable = True)
    apellido = db.Column(db.String(250), nullable = True)
    id_Empleado = db.Column(db.String(250), nullable = True)
    rol_admin = db.Column(db.Boolean, nullable = True, default=False)

class RegistroMarcaje(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    id_empleado = db.Column(db.String(250), nullable = False)
    fecha = db.Column(db.String(250), nullable = True)
    hora = db.Column(db.String(250), nullable = True)
    tipo = db.Column(db.String(250), nullable = False)
    sincronizado = db.Column(db.Boolean, nullable = True, default=False)

class RegistroMarcajePorTarea(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    id_empleado = db.Column(db.String(250), nullable = False)
    tiempo = db.Column(db.String(250), nullable = True)
    fecha = db.Column(db.String(250), nullable = True)
    proyecto = db.Column(db.String(250), nullable = True)
    tarea = db.Column(db.String(250), nullable = True)
    sincronizado = db.Column(db.Boolean, nullable = True, default=False)

class Config(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    Empresa = db.Column(db.String(250), nullable = False)
    ImgEmpresaBase64 = db.Column(db.String(250), nullable = True)
    ImgEmpresaTipo = db.Column(db.String(250), nullable = True)
    TipoConexionBC = db.Column(db.String(250), nullable = True)
    urlBC = db.Column(db.String(250), nullable = True)
    usuarioSOAP = db.Column(db.String(250), nullable = True)
    passwordSOAP = db.Column(db.String(250), nullable = True)
    tenantBC = db.Column(db.String(250), nullable = True)
    idClienteBC = db.Column(db.String(250), nullable = True)
    secretClienteBC = db.Column(db.String(250), nullable = True)
    empresaBC = db.Column(db.String(250), nullable = True)
    moduloBotTelegram = db.Column(db.Boolean, nullable = True, default=False)
    tokenBotTelegram = db.Column(db.String(250), nullable = True)

class Proyecto(db.Model):
    id_proyecto = db.Column(db.String(250), primary_key=True)
    nombre_proyecto = db.Column(db.String(250), nullable = False)
    id_cliente = db.Column(db.String(250), nullable = False)
    nombre_cliente = db.Column(db.String(250), nullable = False)

class Tarea(db.Model):
    #id autoincremental
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_tarea = db.Column(db.String(250))
    nombre_tarea = db.Column(db.String(250), nullable = False)
    id_proyecto = db.Column(db.String(250), nullable = False)
    nombre_proyecto = db.Column(db.String(250), nullable = False)

class TareaEmpleado(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    id_empleado = db.Column(db.String(250), nullable = False)
    id_tarea = db.Column(db.String(250), nullable = False)
    nombre_tarea = db.Column(db.String(250), nullable = False)
    id_proyecto = db.Column(db.String(250), nullable = False)
    nombre_proyecto = db.Column(db.String(250), nullable = False)


def createDB():
    db.create_all()
    #crear usuer admin si no esta creado
    if User.query.filter_by(username='admin').first() is None:
        has_password = Bcrypt().generate_password_hash('admin').decode('utf-8')
        admin = User(username='admin', password=has_password, nombre='admin', apellido='admin', id_Empleado='admin', rol_admin=True)
        db.session.add(admin)
        db.session.commit()
    #crear config si no esta creada
    if Config.query.filter_by(id=0).first() is None:
        config = Config(id=0, Empresa='Empresa', ImgEmpresaBase64='', ImgEmpresaTipo='', TipoConexionBC='SOAP', urlBC='https://api.businesscentral.dynamics.com/v2.0/BC/api/v1.0/', usuarioSOAP='admin', passwordSOAP='admin', tenantBC='admin', idClienteBC='admin', secretClienteBC='admin', empresaBC='admin', moduloBotTelegram=False, tokenBotTelegram='')
        db.session.add(config)
        db.session.commit()