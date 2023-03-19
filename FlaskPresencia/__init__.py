from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user

from FlaskPresencia.config import config

app = Flask(__name__)
app.config.from_object(config['development'])
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

login_manager = LoginManager()
login_manager.init_app(app)

import FlaskPresencia.models
from FlaskPresencia.models import User, Config

db.create_all()

#crear usuer admin si no esta creado
if User.query.filter_by(username='admin').first() is None:
    has_password = Bcrypt().generate_password_hash('admin123456789').decode('utf-8')
    admin = User(username='admin', password=has_password, nombre='admin', apellido='admin', id_Empleado='admin', rol_admin=True)
    db.session.add(admin)
    db.session.commit()
#crear config si no esta creada
if Config.query.filter_by(id=0).first() is None:
    config = Config(id=0, Empresa='Empresa', ImgEmpresaBase64='', ImgEmpresaTipo='', TipoConexionBC='SOAP', urlBC='https://api.businesscentral.dynamics.com/v2.0/BC/api/v1.0/', usuarioSOAP='admin', passwordSOAP='admin', tenantBC='admin', idClienteBC='admin', secretClienteBC='admin', empresaBC='admin', moduloBotTelegram=False, tokenBotTelegram='')
    db.session.add(config)
    db.session.commit()

import FlaskPresencia.form

import FlaskPresencia.rutas
