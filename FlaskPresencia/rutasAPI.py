# coding=utf-8
from flask import Flask, render_template, request, redirect, url_for, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import Length, ValidationError, InputRequired
from flask_bcrypt import Bcrypt
import json
import time
import pandas as pd
import xlsxwriter
import io

#configuracion de la app:
from FlaskPresencia import app, db, bcrypt, login_manager
from FlaskPresencia.models import *
import FlaskPresencia.ConexionesBC.WSnav as ws
from FlaskPresencia.form import *
from FlaskPresencia.rutas import *

#rutas de la api
@app.route('/api/registrarMarcageAPI', methods=['POST'])
def registrarMarcageAPI():
    #obtener datos de json
    data = request.get_json()
    #mirar si existe el usuario de conexion
    DatosConexion  = data['DatosConexion']
    usuario = DatosConexion['usuario']
    password = DatosConexion['password']
    
    estado, mensaje = ComprobarUsuario(usuario, password)
    if estado == 'Error':
        return json.dumps({'status':'ERROR', 'mensaje':mensaje})
    
    #Si no hay errores, registrar marcaje
    datosMarcage = data['datosMarcage']
    #obtener datos de la conexion
    id_empleado = datosMarcage['id_empleado']
    fecha = datosMarcage['fecha']
    hora = datosMarcage['hora']
    tipo = datosMarcage['tipo']
    #agrergar marcaje a la base de datos
    marcaje = RegistroMarcaje(id_empleado=id_empleado, fecha=fecha, hora=hora, tipo=tipo)
    db.session.add(marcaje)
    db.session.commit()
    return json.dumps({'status':'OK', 'mensaje':'Marcage registrado'})

@app.route('/api/registrarMarcageTareaAPI', methods=['POST'])
def registrarMarcageTareaAPI():
    #obtener datos de json
    data = request.get_json()
    #mirar si existe el usuario de conexion
    DatosConexion  = data['DatosConexion']
    usuario = DatosConexion['usuario']
    password = DatosConexion['password']
    
    estado, mensaje = ComprobarUsuario(usuario, password)
    if estado == 'Error':
        return json.dumps({'status':'ERROR', 'mensaje':mensaje})
    
    #Si no hay errores, registrar marcaje
    datosMarcage = data['datosMarcage']
    #obtener datos de la conexion
    id_empleado = datosMarcage['id_empleado']
    fecha = datosMarcage['fecha']
    tiempo = datosMarcage['tiempo']
    tarea = datosMarcage['tarea']
    proyecto = datosMarcage['proyecto']

    marcaje = RegistroMarcajePorTarea(id_empleado=id_empleado, fecha=fecha, tiempo=tiempo, tarea=tarea, proyecto=proyecto)
    db.session.add(marcaje)
    db.session.commit()
    return json.dumps({'status':'OK', 'mensaje':'Marcage registrado'})

@app.route('/api/obtenerMarcageAPI', methods=['POST'])
def obtenerMarcageAPI():
    #obtener datos de json
    data = request.get_json()
    #mirar si existe el usuario de conexion
    DatosConexion  = data['DatosConexion']
    print(DatosConexion)
    usuario = DatosConexion['usuario']
    password = DatosConexion['password']
    
    estado, mensaje = ComprobarUsuario(usuario, password)
    if estado == 'Error':
        return json.dumps({'status':'ERROR', 'mensaje':mensaje})
    
    #Si no hay errores, obtener marcajes
    #mirar si existe datosMarcage en el json
    if 'datosMarcage' not in data:
        id_empleado = usuario
        print(id_empleado)
    else:
        datosMarcage = data['datosMarcage']
        #obtener datos de la conexion
        id_empleado = datosMarcage['id_empleado']

    #obtener marcajes de la base de datos
    marcajes = RegistroMarcaje.query.filter_by(id_empleado=id_empleado).all()
    #convertir a json
    marcajes_json = []
    for marcaje in marcajes:
        marcajes_json.append({'id_empleado':marcaje.id_empleado, 'fecha':marcaje.fecha, 'hora':marcaje.hora, 'tipo':marcaje.tipo})
    return json.dumps({'status':'OK', 'mensaje':'Marcage obtenidos', 'datos':marcajes_json})

@app.route('/api/obtenerMarcageTareaAPI', methods=['POST'])
def obtenerMarcageTareaAPI():
    #obtener datos de json
    data = request.get_json()
    #mirar si existe el usuario de conexion
    DatosConexion  = data['DatosConexion']
    usuario = DatosConexion['usuario']
    password = DatosConexion['password']
    
    estado, mensaje = ComprobarUsuario(usuario, password)
    if estado == 'Error':
        return json.dumps({'status':'ERROR', 'mensaje':mensaje})
    
    #Si no hay errores, obtener marcajes
    #mirar si existe datosMarcage en el json
    if 'datosMarcage' not in data:
        id_empleado = usuario
    else:
        datosMarcage = data['datosMarcage']
        #obtener datos de la conexion
        id_empleado = datosMarcage['id_empleado']
    #obtener marcajes de la base de datos
    marcajes = RegistroMarcajePorTarea.query.filter_by(id_empleado=id_empleado).all()
    #convertir a json
    marcajes_json = []
    for marcaje in marcajes:
        marcajes_json.append({'id_empleado':marcaje.id_empleado, 'fecha':marcaje.fecha, 'tiempo':marcaje.tiempo, 'tarea':marcaje.tarea, 'proyecto':marcaje.proyecto})
    return json.dumps({'status':'OK', 'mensaje':'Marcage obtenidos', 'datos':marcajes_json})


#ultimmo marcaje
@app.route('/api/obtenerUltimoMarcageAPI', methods=['POST'])
def obtenerUltimoMarcageAPI():
    #obtener datos de json
    data = request.get_json()

    #mirar si existe el usuario de conexion
    DatosConexion  = data['DatosConexion']
    print(DatosConexion)
    usuario = DatosConexion['usuario']
    password = DatosConexion['password']
    
    estado, mensaje = ComprobarUsuario(usuario, password)
    if estado == 'Error':
        return json.dumps({'status':'ERROR', 'mensaje':mensaje})
    
    #Si no hay errores, obtener marcajes
    #mirar si existe datosMarcage en el json
    if 'datosMarcage' not in data:
        id_empleado = usuario
        print(id_empleado)
    else:
        datosMarcage = data['datosMarcage']
        #obtener datos de la conexion
        id_empleado = datosMarcage['id_empleado']

    #obtener el ultimo marcaje de la base de datos
    marcaje = RegistroMarcaje.query.filter_by(id_empleado=id_empleado).order_by(RegistroMarcaje.id.desc()).first()
    #convertir a json
    marcaje_json = {'id_empleado':marcaje.id_empleado, 'fecha':marcaje.fecha, 'hora':marcaje.hora, 'tipo':marcaje.tipo}
    return json.dumps({'status':'OK', 'mensaje':'Ultimo marcage obtenido', 'datos':marcaje_json})

def ComprobarUsuario(usuario, password):
    #mirar si existe el usuario de conexion
    user = User.query.filter_by(username=usuario).first()
    if user is None:
        return 'Error', 'Usuario no existe'
    #mirar si la contraseña es correcta
    if bcrypt.check_password_hash(user.password, password) == False:
        return 'Error', 'Contraseña incorrecta'
    #mirar si el usuario tiene permisos admin
    # if user.rol_admin == False:
    #     return 'Error', 'Usuario no tiene permisos'
    return 'OK', 'Usuario correcto'