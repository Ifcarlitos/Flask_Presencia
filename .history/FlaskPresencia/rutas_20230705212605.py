# coding=utf-8
from flask import Flask, render_template, request, redirect, url_for, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import Length, ValidationError, InputRequired
from flask_bcrypt import Bcrypt
from suds.client import Client
import json
import time
import pandas as pd
import xlsxwriter
import io
import datetime
#configuracion de la app:
from FlaskPresencia import app, db, bcrypt, login_manager
from FlaskPresencia.models import *
import FlaskPresencia.ConexionesBC.WSnav as ws
from FlaskPresencia.form import *

login_manager.login_view = 'login'

#funcion para devolver el usuario logueado:
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

#Rutas:
@app.route('/')
def index():
    #return render_template('home.html')
    return redirect(url_for('RegistroBasico'))

#Ruta para el login del usuario:
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user:
            if bcrypt.check_password_hash(user.password, form.password.data):
                login_user(user)
                return redirect(url_for('inicio'))
    return render_template('login.html', form=form)

#Ruta para el registro de usuarios, temporal solo para pruebas:
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        hashed_passw = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        new_user = User(username=form.username.data, password=hashed_passw, id_Empleado=form.username.data)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

#Ruta para el logout del usuario:
@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    #redireccionar a la pagina de /
    return redirect(url_for('index'))

#Ruta para el inicio del usuario:
@app.route('/inicio', methods=['GET', 'POST'])
@login_required
def inicio():
    #buscar tarea por empleado
    user = User.query.filter_by(username=current_user.username).first()
    accion = 'S'
    idEmpleado = user.id_Empleado
    ultimaAccion = RegistroMarcaje.query.filter_by(id_empleado=user.id_Empleado).order_by(RegistroMarcaje.id.desc()).first()
    if ultimaAccion != None:
        accion = ultimaAccion.tipo

    mostrar = True
    #Buscar tareas por empleado
    tareas = TareaEmpleado.query.filter_by(id_empleado=user.id_Empleado).all()

    #mirar si hay tareas
    if len(tareas) == 0:
        mostrar = False
    
    return render_template('inicio.html', tareas=tareas, accion=accion, idEmpleado=idEmpleado, mostrar=mostrar)

#Ruta para el registro de usuarios:
@app.route('/enviarRegistros', methods=['GET', 'POST'])
@login_required
def enviarRegistros():
     #sacar valores de json (proyecto, tarea, empleado, valor)
    datos = request.form
    #print(datos)
    idproyecto = datos['idProyecto']
    idtarea = datos['idTarea']
    idempleado = datos['idEmpleado']
    valor = datos['valor']
    #buscar si existe el proyecto
    proyecto = Proyecto.query.filter_by(id_proyecto=idproyecto).first()
    if proyecto == None:
        return 'El proyecto no existe'
    #buscar si existe la tarea
    tarea = Tarea.query.filter_by(id_tarea=idtarea).first()
    if tarea == None:
        return 'La tarea no existe'
    #creamos el RegistroMarcajePorTarea
    fecha = time.strftime("%Y-%m-%d")
    fecha = datetime.datetime.now().strftime("%d/%m/%Y")
    registro = RegistroMarcajePorTarea(proyecto=idproyecto, tarea=idtarea, id_empleado=idempleado, tiempo=valor, fecha=fecha)
    db.session.add(registro)
    db.session.commit()
    #mirar si configura el registro tambien es enviar por Odata
    configuracion = Config.query.filter_by(id=0).first()
    if configuracion != None:
        if configuracion.TipoConexionBC == 'Odata':
            idapp = configuracion.IdClienteBC
            valor = configuracion.secretClienteBC
            tenant = configuracion.tenantBC
            empresa = configuracion.empresaBC
            sincronizarMarcajesPorTareaFiltradoOdata(tenant,idapp,valor,empresa, registro)
        if configuracion.TipoConexionBC == 'Soap':
                url = configuracion.urlBC
                username = configuracion.usuarioSOAP
                password = configuracion.passwordSOAP
                print(url)
                print(username)
                print(password)
                sincronizarMarcajesPorTareaFiltradoSoap(url, username, password, registro)

    return 'ok'

#Ruta para la configuracion de la aplicacion:
@app.route('/Configuracion', methods=['GET', 'POST'])
@login_required
def Configuracion():
    #comprobar si el usuario es de rol administrador
    user = User.query.filter_by(username=current_user.username).first()
    if user.rol_admin == True:
        configuracion = Config.query.filter_by(id=0).first()
        if configuracion:
            #si existe la configuracion, cargar el formulario con los datos de la base de datos
            formulario = FormConfiguacion(formdata=request.form, obj=configuracion)
            if request.method == 'POST' :
                #actualizar los datos de la base de datos
                configuracion.Empresa = formulario.Empresa.data
                configuracion.TipoConexionBC = formulario.TipoConexionBC.data
                configuracion.IdClienteBC = formulario.idClienteBC.data
                configuracion.secretClienteBC = formulario.secretClienteBC.data
                configuracion.tenantBC = formulario.tenantBC.data
                configuracion.empresaBC = formulario.empresaBC.data
                configuracion.urlBC = formulario.urlBC.data
                configuracion.usuarioSOAP = formulario.usuarioSOAP.data
                configuracion.passwordSOAP = formulario.passwordSOAP.data

                #guardar los datos del formulario en la base de datos
                formulario.populate_obj(configuracion)
                db.session.commit()
                return redirect(url_for('Herramientas'))
            return render_template('EditarConfiguracion.html', form=formulario)
        else:
            return redirect(url_for('inicio'))
    else:
        return redirect(url_for('inicio'))

@app.route('/Herramientas', methods=['GET', 'POST'])
@login_required
def Herramientas():
    #comprobar si el usuario es de rol administrador
    user = User.query.filter_by(username=current_user.username).first()
    if user.rol_admin == True:
        return render_template('Herramientas.html', admin='S')
    else:
        return render_template('Herramientas.html', admin='N')

@app.route('/Herramientas/CambiarContrasena', methods=['GET', 'POST'])
@login_required
def CambiarContrasena():
    #Preparar el formulario en html
    formulario = '''
    <form>
        <div class="form-group">
            <label for="password">Contraseña actual</label>
            <input type="password" class="form-control" id="password" placeholder="Contraseña actual">
        </div>
        <div class="form-group">
            <label for="newPassword">Nueva contraseña</label>
            <input type="password" class="form-control" id="newPassword" placeholder="Nueva contraseña">
        </div>
        <div class="form-group">
            <label for="newPassword2">Repetir nueva contraseña</label>
            <input type="password" class="form-control" id="newPassword2" placeholder="Repetir nueva contraseña">
        </div>
        <button type="button" class="btn btn-primary" onclick="cambiarContrasena()">Cambiar contraseña</button>
    </form>
    <script>
        function cambiarContrasena(){
            var password = document.getElementById('password').value;
            var newPassword = document.getElementById('newPassword').value;
            var newPassword2 = document.getElementById('newPassword2').value;
            if (newPassword == newPassword2){
                $.ajax({
                    url: '/ActualizarContrasena',
                    type: 'POST',
                    data: 'password='+password+'&newPassword='+newPassword,
                    success: function(data){
                        if (data == 'OK'){
                            //alert('Contraseña actualizada correctamente');
                            window.location.href = '/Herramientas';
                        }else{
                            alert('Contraseña actual incorrecta');
                        }
                    }
                });
            }else{
                alert('Las contraseñas no coinciden');
            }
        }
    </script>
    '''
    return formulario

@app.route('/ActualizarContrasena', methods=['GET', 'POST'])
@login_required
def ActualizarContrasena():
    #comprobar si el usuario es de rol administrador
    user = User.query.filter_by(username=current_user.username).first()
    if request.method == 'POST':
            datos = request.form
            password = datos['password']
            newPassword = datos['newPassword']
            #comprobar si la contraseña actual es correcta
            if bcrypt.check_password_hash(user.password, password):
                #cambiar la contraseña
                hashed_passw = bcrypt.generate_password_hash(newPassword).decode('utf-8')
                user.password = hashed_passw
                db.session.commit()
                return 'OK'
            else:
                return 'KO'
    else:
        return 'KO'

@app.route('/Herramientas/VerEmpleados', methods=['GET', 'POST'])
@login_required
def VerEmpleados():
    usuarios = User.query.all()
    return render_template('VerEmpleados.html', usuarios=usuarios)

#editar_empleado
@app.route('/Herramientas/EditarEmpleado/<id>', methods=['GET', 'POST'])
@login_required
def editar_empleado(id):
    empleado = User.query.filter_by(id=id).first()
    if empleado:
        formulario = FormEmpleado(formdata=request.form, obj=empleado)
        #preparar el formulario
        if request.method == 'POST' and formulario.validate():
            #guardar los datos del formulario en la base de datos
            formulario.populate_obj(empleado)
            db.session.commit()
            return redirect(url_for('Herramientas'))
        return render_template('EditarEmpleado.html', form=formulario)
    else:
        return redirect(url_for('inicio'))

#eliminar_empleado
@app.route('/Herramientas/EliminarEmpleado/<id>', methods=['GET', 'POST'])
@login_required
def eliminar_empleado(id):
    empleado = User.query.filter_by(id=id).first()
    if empleado:
        db.session.delete(empleado)
        db.session.commit()
        return redirect(url_for('Herramientas'))
    else:
        return redirect(url_for('inicio'))
      
#hacer_admin
@app.route('/Herramientas/HacerAdmin/<id>', methods=['GET', 'POST'])
@login_required
def hacer_admin(id):
    user = User.query.filter_by(id=id).first()
    if user:
        if user.rol_admin == True:
            user.rol_admin = False
        else:
            user.rol_admin = True
        db.session.commit()
        return redirect(url_for('Herramientas'))

#crear_empleado
@app.route('/Herramientas/CrearEmpleado', methods=['GET', 'POST'])
@login_required
def crear_empleado():    
    form = FormEmpleado()
    if form.validate_on_submit():
        hashed_passw = bcrypt.generate_password_hash('admin123456789').decode('utf-8')
        new_user = User(username=form.username.data, password=hashed_passw, id_Empleado=form.id_Empleado.data, nombre=form.nombre.data, apellido=form.apellido.data)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('Herramientas'))
    return render_template('EditarEmpleado.html', form=form)

@app.route('/Herramientas/Proyectos', methods=['GET', 'POST'])
@login_required
def Proyectos():
    #comprobar si el usuario es de rol admin 
    user = User.query.filter_by(username=current_user.username).first()
    if user.rol_admin == True:
        proyectos = Proyecto.query.all()
        tablaHtml = '''
        <div class="row mt-2">
            <button class="col-sm btn btn-primary margin-Botones" type="button" onclick="crearProyecto()">
                    <div class="row mt-2">
                        <div class="col-sm">Crear Proyecto</div>
                    </div>
            </button>
        </div>
        <br>
        <div class="app-nb-table-responsive">
            <table id="DataTableMostrar" class="display table" style="width:100%">
                <thead>
                <tr>
                    <th>Id</th>
                    <th>Nombre</th>
                    <th>Cliente</th>
                    <th></th>
                </tr>
                </thead>
            </table>
        </div>
        '''
        #json de proyectos
        jsonProyectos = []
        for proyecto in proyectos:
            jsonProyectos.append({'id': proyecto.id_proyecto, 'nombre': proyecto.nombre_proyecto, 'cliente': proyecto.nombre_cliente})
        
        datos = {'tablaHtml': tablaHtml, 'jsonProyectos': jsonProyectos}
        return datos

@app.route('/Herramientas/CrearProyecto', methods=['GET', 'POST'])
@login_required
def HerramientaCrearProyecto():
    #comprobar si el usuario es de rol admin 
    user = User.query.filter_by(username=current_user.username).first()
    if user.rol_admin == True:
        formulario = '''
        <form>
            <div class="form-group">
                <label for="idProyecto">Nombre del proyecto</label>
                <input type="text" class="form-control" id="idProyecto" placeholder="Id del proyecto">
            </div>
            <div class="form-group">
                <label for="nombreProyecto">Nombre del proyecto</label>
                <input type="text" class="form-control" id="nombreProyecto" placeholder="Nombre del proyecto">
            </div>
            <div class="form-group">
                <label for="cliente">Id Cliente</label>
                <input type="text" class="form-control" id="idcliente" placeholder="Id Cliente">
            </div>
            <div class="form-group">
                <label for="cliente">Cliente</label>
                <input type="text" class="form-control" id="cliente" placeholder="Cliente">
            </div>
            <button type="button" class="btn btn-primary" onclick="crearProyectoBD()">Crear proyecto</button>
        </form>
        '''
        return formulario

@app.route('/CrearProyecto', methods=['GET', 'POST'])
@login_required
def CrearProyecto():
    #comprobar si el usuario es de rol admin 
    user = User.query.filter_by(username=current_user.username).first()
    if user.rol_admin == True:
        if request.method == 'POST':
            datos = request.form
            nombreProyecto = datos['nombreProyecto']
            cliente = datos['cliente']
            idCliente = datos['idcliente']
            idProyecto = datos['idProyecto']

            if idProyecto == '' or nombreProyecto == '' or cliente == '' or idCliente == '':
                return 'KO'

            #comprobar si el proyecto ya existe
            proyecto = Proyecto.query.filter_by(nombre_proyecto=nombreProyecto).first()
            if proyecto == None:
                #crear proyecto
                proyecto = Proyecto(nombre_proyecto=nombreProyecto, nombre_cliente=cliente, id_proyecto=idProyecto,id_cliente = idCliente)
                db.session.add(proyecto)
                db.session.commit()
                return 'OK'
            else:
                return 'KO'
        else:
            return 'KO'

@app.route('/Herramientas/verTareas', methods=['GET', 'POST'])
@login_required
def verTareas():
    #comprobar si el usuario es de rol admin 
    user = User.query.filter_by(username=current_user.username).first()
    if user.rol_admin == True:
        data = request.form
        idProyecto = data['idProyecto']
        tareas = Tarea.query.filter_by(id_proyecto=idProyecto).all()
        nombreProyecto = Proyecto.query.filter_by(id_proyecto=idProyecto).first()
        if nombreProyecto != None:
            nombreProyecto = nombreProyecto.nombre_proyecto
        else:
            nombreProyecto = ''
        tablaHtml = '''
        <div class="form-group">
            <h2>'''+nombreProyecto+'''</h2>
        </div>
        <br>
        <div class="row mt-2">
            <button class="col-sm btn btn-primary margin-Botones" type="button" attr_proyecto="'''+idProyecto+'''" onclick="crearTarea(this)">
                    <div class="row mt-2">
                        <div class="col-sm">Crear Tarea</div>
                    </div>
            </button>
        </div>
        <br>
        <div class="app-nb-table-responsive">
            <table id="DataTableMostrar" class="display table" style="width:100%">
                <thead>
                <tr>
                    <th>Id</th>
                    <th>Nombre</th>
                </tr>
                </thead>
            </table>
        </div>
        '''
        #json de proyectos
        jsonTareas = []
        for tarea in tareas:
            jsonTareas.append({'id': tarea.id_tarea, 'nombre': tarea.nombre_tarea})

        datos = {'tablaHtml': tablaHtml, 'jsonTareas': jsonTareas}
        return datos

@app.route('/Herramientas/CrearTarea', methods=['GET', 'POST'])
@login_required
def HerramientaCrearTarea():
    #comprobar si el usuario es de rol admin 
    user = User.query.filter_by(username=current_user.username).first()
    idProyecto = request.form['idProyecto']
    if user.rol_admin == True:
        formulario = '''
        <form>
            <div class="form-group">
                <label for="idProyecto">Id proyecto</label>
                <input type="text" class="form-control" id="idProyecto" placeholder="Id del proyecto" value="'''+idProyecto+'''" disabled>
            </div>
            <div class="form-group">
                <label for="idTarea">Id Tarea</label>
                <input type="text" class="form-control" id="idTarea" placeholder="Id Tarea">
            </div>
            <div class="form-group">
                <label for="nombreTarea">Nombre Tarea</label>
                <input type="text" class="form-control" id="nombreTarea" placeholder="Nombre Tarea">
            </div>
            <button type="button" class="btn btn-primary" onclick="crearTareaDB()">Crear Tarea</button>
        </form>
        '''
        return formulario

@app.route('/Herramientas/VerRegistros', methods=['GET', 'POST'])
@login_required
def verRegistros():
    registros = RegistroMarcaje.query.all()
    #ordenar de manera descendente por id
    registros = sorted(registros, key=lambda x: x.id, reverse=True)
    admin = User.query.filter_by(username=current_user.username).first()
    if admin.rol_admin == True:
        admin = True
    else:  
        admin = False

    empleados = User.query.filter_by().all()
    herramientas = True
    return render_template('VerRegistros.html', registros=registros, admin=admin, herramientas=herramientas, empleados=empleados)

@app.route('/Herramientas/AsignarEmpleadoTarea', methods=['GET', 'POST'])
@login_required
def AsignarEmpleadoTarea():
    #comprobar si el usuario es de rol admin 
    user = User.query.filter_by(username=current_user.username).first()
    if user.rol_admin == True:
        Empleados = User.query.filter_by().all()
        Tareas = Tarea.query.filter_by().all()
        #formulario con campos como select
        htmlFOrmulario = '''
        <form>
            <div class="form-group">
                <label for="idEmpleado">Id Empleado</label>
                <select class="form-control" id="idEmpleado">
                    <option value="">Selecciona un empleado</option>
        '''
        for empleado in Empleados:
            #si las variables son null no se muestran
            if empleado.id_Empleado == None:
                empleado.id_Empleado = ''
            if empleado.username == None:
                empleado.username = ''

            htmlFOrmulario += '''
                <option value="'''+empleado.id_Empleado+'''">'''+empleado.username+'''</option>
            '''
        htmlFOrmulario += '''
                </select>
            </div>
            <div class="form-group">
                <label for="idTarea">Id Tarea</label>
                <select class="form-control" id="idTarea">
                    <option value="">Selecciona una tarea</option>
        '''
        for tarea in Tareas:
            #si las variables son null no se muestran
            if tarea.id_tarea == None:
                tarea.id_tarea = ''
            if tarea.nombre_tarea == None:
                tarea.nombre_tarea = ''

            htmlFOrmulario += '''
                <option value="'''+tarea.id_tarea+'''" attrproyecto="'''+tarea.id_proyecto+'''">'''+tarea.nombre_proyecto+''' '''+tarea.nombre_tarea+'''</option>
            '''
        htmlFOrmulario += '''
                </select>
            </div>
            <button type="button" class="btn btn-primary" onclick="asignarEmpleadoTareaDB()">Asignar</button>
            </br>
            </br>
            <button type="button" class="btn btn-primary" onclick="asignacionesActuales()">Ver asignaciones Actuales</button>
        </form>
        '''

        return htmlFOrmulario

@app.route('/Herramientas/AsignarEmpleadoTareasDB', methods=['GET', 'POST'])
@login_required
def AsignarEmpleadoTareasDB():
    #comprobar si el usuario es de rol admin 
    user = User.query.filter_by(username=current_user.username).first()
    if user.rol_admin == True:
        if request.method == 'POST':
            datos = request.form
            idEmpleado = datos['idEmpleado']
            idTarea = datos['idTarea']
            idProyecto = datos['idProyecto']

            #comprobar si el empleado existe
            empleado = User.query.filter_by(id_Empleado=idEmpleado).first()
            if empleado == None:
                return 'El empleado no existe'

            #comprobar si la tarea existe
            tarea = Tarea.query.filter_by(id_tarea=idTarea).first()
            if tarea == None:
                return 'La tarea no existe'
            
            #comprobar si el proyecto existe
            proyecto = Proyecto.query.filter_by(id_proyecto=idProyecto).first()
            if proyecto == None:
                return 'El proyecto no existe'

            #comprobar si el empleado ya esta asignado a la tarea en TareaEmpleado
            # asignacion = TareaEmpleado.query.filter_by(id_tarea=idTarea, id_proyecto = idProyecto, id_empleado = idEmpleado).first()
            # if asignacion == None:
            #     return 'El empleado ya esta asignado a la tarea'

            #asignar empleado a la tarea
            asignacion = TareaEmpleado(id_tarea=idTarea, id_proyecto = idProyecto, id_empleado = idEmpleado, nombre_tarea = tarea.nombre_tarea, nombre_proyecto = proyecto.nombre_proyecto)
            db.session.add(asignacion)
            db.session.commit()
            return 'OK'

@app.route('/Herramientas/AsignacionesActuales', methods=['GET', 'POST'])
@login_required
def AsignacionesActuales():
    #comprobar si el usuario es de rol admin 
    user = User.query.filter_by(username=current_user.username).first()
    if user.rol_admin == True:
        asignaciones = TareaEmpleado.query.filter_by().all()
        return render_template('AsignacionesActuales.html', asignaciones=asignaciones)

@app.route('/Herramientas/eliminarAsignacion', methods=['GET', 'POST'])
@login_required
def eliminarAsignacion():
    #comprobar si el usuario es de rol admin 
    user = User.query.filter_by(username=current_user.username).first()
    if user.rol_admin == True:
        if request.method == 'POST':
            datos = request.form
            idEmpleado = datos['empleado']
            idTarea = datos['tarea']
            idProyecto = datos['proyecto']

            #comprobar si el empleado existe
            empleado = User.query.filter_by(id_Empleado=idEmpleado).first()
            if empleado == None:
                return 'El empleado no existe'

            #comprobar si la tarea existe
            tarea = Tarea.query.filter_by(id_tarea=idTarea).first()
            if tarea == None:
                return 'La tarea no existe'
            
            #comprobar si el proyecto existe
            proyecto = Proyecto.query.filter_by(id_proyecto=idProyecto).first()
            if proyecto == None:
                return 'El proyecto no existe'

            #comprobar si el empleado ya esta asignado a la tarea en TareaEmpleado
            asignacion = TareaEmpleado.query.filter_by(id_tarea=idTarea, id_proyecto = idProyecto, id_empleado = idEmpleado).first()
            if asignacion == None:
                return 'El empleado no esta asignado a la tarea'
    
            #eliminar asignacion
            #buscar sesion de la asignacion
            session = db.session.object_session(asignacion)
            session.delete(asignacion)
            session.commit()
            return 'OK'

@app.route('/Herramientas/VerRegistrosTareas', methods=['GET', 'POST'])
@login_required
def VerRegistrosTareas():
    #mostrar todos los registros
    registros = RegistroMarcajePorTarea.query.all()
    #ordenar de manera descendente por id
    registros = sorted(registros, key=lambda x: x.id, reverse=True)
    admin = False
    if current_user.rol_admin == True:
        admin = True
    
    empleados = User.query.filter_by().all()
    proyectos = Proyecto.query.filter_by().all()
    tareas = Tarea.query.filter_by().all()

    herramientas = True
    return render_template('VerHorasRegistradas.html', registros=registros, admin=admin, empleados=empleados, proyectos=proyectos, tareas=tareas, herramientas=herramientas)

@app.route('/Herramientas/VerLogs', methods=['GET', 'POST'])
@login_required
def VerLogs():
    #buscar archivo log.txt
    archivo = open('log.txt', 'r')
    #leer archivo
    contenido = archivo.read()
    #cerrar archivo
    archivo.close()
    #mostrar en html
    html = '''
    <h1>Logs</h1>
    <p>'''+contenido+'''</p>
    '''
    return html

#/Herramientas/CIM
@app.route('/Herramientas/CIM', methods=['GET', 'POST'])
@login_required
def CIM():
    fechaHoy = time.strftime("%Y-%m-%d")

    fechaHoyCon0 = str(fechaHoy)
    #si el mes es menor a 10, eliminar el 0
    if fechaHoy[5] == '0':
        fechaHoy = fechaHoy[:5]+fechaHoy[6:]
    #pasar fecha a str
    fechaHoySin0 = str(fechaHoy)
    
    #buscar registros de la fecha de hoy
    registrosTareas = RegistroMarcajePorTarea.query.filter_by(fecha=fechaHoyCon0).all()
    registrosEntradas = RegistroMarcaje.query.filter_by(fecha=fechaHoy, tipo='E').all()
    registrosSalidas = RegistroMarcaje.query.filter_by(fecha=fechaHoy, tipo='S').all()
    #enviar a html
    return render_template('CIM.html', registrosTareas=registrosTareas, registrosEntradas=registrosEntradas, registrosSalidas=registrosSalidas)

@app.route('/CrearTarea', methods=['GET', 'POST'])
@login_required
def CrearTarea():
    #comprobar si el usuario es de rol admin 
    user = User.query.filter_by(username=current_user.username).first()
    if user.rol_admin == True:
        if request.method == 'POST':
            datos = request.form
            idProyecto = datos['idProyecto']
            idTarea = datos['idTarea']
            nombreTarea = datos['nombreTarea']

            #buscar proyecto
            proyecto = Proyecto.query.filter_by(id_proyecto=idProyecto).first()

            if idProyecto == '' or idTarea == '' or nombreTarea == '':
                return 'El campo no puede estar vacio'
            
            if proyecto == None:
                return 'El proyecto no existe'

            nombreProyecto = proyecto.nombre_proyecto
            #comprobar si la tarea ya existe
            tarea = Tarea.query.filter_by(id_tarea=idTarea, id_proyecto = idProyecto).first()
            if tarea == None:
                #crear tarea
                tarea = Tarea(id_tarea=idTarea, nombre_tarea=nombreTarea, id_proyecto=idProyecto, nombre_proyecto= nombreProyecto)
                db.session.add(tarea)
                db.session.commit()
                return 'OK'
            else:
                return 'KO'
        else:
            return 'KO'

@app.route('/Registro', methods=['GET', 'POST'])
@login_required
def Registro():
    return render_template('Registro.html')

@app.route('/Registro/verRegistros', methods=['GET', 'POST'])
@login_required
def verRegistrosFiltrados():
    #FILTRAR POR el empleado que esta logueado en el campo id_empleado
    empleado = User.query.filter_by(username=current_user.username).first()
    registros = RegistroMarcaje.query.filter_by(id_empleado=empleado.id_Empleado).all()
    registros = RegistroMarcaje.query.all()
    #ordenar de manera descendente por id
    registros = sorted(registros, key=lambda x: x.id, reverse=True)
    admin = False
    if current_user.rol_admin == True:
        admin = True
    
    herramientas = False
    return render_template('VerRegistros.html', registros=registros, admin=admin, herramientas= herramientas)

#ruta /verRegistros/eliminar_registro con parametro id
@app.route('/verRegistros/eliminar_registro/<id>', methods=['GET', 'POST'])
@login_required
def VerRegistro_eliminar_registro(id):
    #comprobar si el usuario es de rol admin
    user = User.query.filter_by(username=current_user.username).first()
    if user.rol_admin == True:
        #comprobar si el registro existe
        registro = RegistroMarcaje.query.filter_by(id=id).first()
        if registro != None:
            #buscar la sesion del registro
            sesion =db.session.object_session(registro)
            #eliminar registro
            sesion.delete(registro)
            sesion.commit()
    #devolver a la pagina /Registro/verRegistros
    return redirect(url_for('Registro'))

#VerRegistro_editar_registro
@app.route('/verRegistros/editar_registro/<id>', methods=['GET', 'POST'])
@login_required
def VerRegistro_editar_registro(id):
    registro = RegistroMarcaje.query.filter_by(id=id).first()
    if registro:
        formulario = EditRegistroMarcaje(formdata=request.form, obj=registro)
        if request.method == 'POST' and formulario.validate():
            #guardar los datos del formulario en la base de datos
            formulario.populate_obj(registro)
            db.session.commit()
            return redirect(url_for('inicio'))
        return render_template('EditRegistroMarcaje.html', form=formulario)
    else:
        return redirect(url_for('inicio'))

@app.route('/Registro/verHorasRegistradas', methods=['GET', 'POST'])
@login_required
def verHorasRegistradasFiltrados():
    #FILTRAR POR el empleado que esta logueado en el campo id_empleado
    empleado = User.query.filter_by(username=current_user.username).first()
    registros = RegistroMarcajePorTarea.query.filter_by(id_empleado=empleado.id_Empleado).all()
    registros = RegistroMarcajePorTarea.query.all()
    #ordenar de manera descendente por id
    registros = sorted(registros, key=lambda x: x.id, reverse=True)
    admin = False
    if current_user.rol_admin == True:
        admin = True
    
    herramientas = False
    return render_template('VerHorasRegistradas.html', registros=registros, admin=admin, herramientas=herramientas)

#ruta /verHorasRegistradas/eliminar_registro con parametro id
@app.route('/verHorasRegistradas/eliminar_registro/<id>', methods=['GET', 'POST'])
@login_required
def VerHorasRegistradas_eliminar_registro(id):
    #comprobar si el usuario es de rol admin
    user = User.query.filter_by(username=current_user.username).first()
    if user.rol_admin == True:
        #comprobar si el registro existe
        registro = RegistroMarcajePorTarea.query.filter_by(id=id).first()
        if registro != None:
            #buscar la sesion del registro
            sesion =db.session.object_session(registro)
            #eliminar registro
            sesion.delete(registro)
            sesion.commit()
    #devolver a la pagina /Registro/verHorasRegistradas
    return redirect(url_for('Registro'))

#VerHorasRegistradas_editar_registro
@app.route('/verHorasRegistradas/editar_registro/<id>', methods=['GET', 'POST'])
@login_required
def VerHorasRegistradas_editar_registro(id):
    registro = RegistroMarcajePorTarea.query.filter_by(id=id).first()
    if registro:
        formulario = EditRegistroMarcajePorTarea(formdata=request.form, obj=registro)
        if request.method == 'POST' and formulario.validate():
            #guardar los datos del formulario en la base de datos
            formulario.populate_obj(registro)
            db.session.commit()
            return redirect(url_for('inicio'))
        return render_template('EditRegistroMarcajePorTarea.html', form=formulario)
    else:
        return redirect(url_for('inicio'))

@app.route('/RegistroBasico', methods=['GET', 'POST'])
def RegistroBasico():
    return render_template('RegistroBasico.html')

@app.route('/RegistroBasico/ultimaAccion', methods=['GET', 'POST'])
def ultimaAccion():
    datos = request.form
    #comprobar si existe el empleado
    empleado = User.query.filter_by(id_Empleado=datos['cardNum']).first()

    if empleado == None:
        jsonEnvio = {
        'cardNum': datos['cardNum'],
        'accion': 'N',
        'nombre': 'No existe',
        'apellido': 'No existe'
        }
        return jsonEnvio
    

    nombreEmpleado = empleado.nombre
    apellidoEmpleado = empleado.apellido

    if nombreEmpleado == None:
        nombreEmpleado = ''
    
    if apellidoEmpleado == None:
        apellidoEmpleado = ''

    #buscar ultima accion en RegistroMarcaje del empleado
    ultimaAccion = RegistroMarcaje.query.filter_by(id_empleado=datos['cardNum']).order_by(RegistroMarcaje.id.desc()).first()
    if ultimaAccion == None:
        jsonEnvio = {
        'cardNum': datos['cardNum'],
        'accion': 'S',
        'nombre': nombreEmpleado,
        'apellido': apellidoEmpleado
        }
        return jsonEnvio
    else:
        jsonEnvio = {
        'cardNum': datos['cardNum'],
        'accion': ultimaAccion.tipo,
        'nombre': nombreEmpleado,
        'apellido': apellidoEmpleado
        }
        return jsonEnvio

@app.route('/RegistroBasico/Registrar', methods=['GET', 'POST'])
def Registrar():
    datos = request.form
    cardnum = datos['cardNum']
    fechaString = datos['fecha']
    horaString = datos['hora']
    accion = datos['accion']

    #si accion es diferente de S o E, error
    if accion != 'S' and accion != 'E':
        return 'KO'

    #COMPROBAR SI EXISTE EL EMPLEADO
    empleado = User.query.filter_by(username=cardnum).first()
    if empleado == None:
        return 'KO'
    else:
        #registrar marcaje
        registroMarcajeEmpleado = RegistroMarcaje(id_empleado=cardnum, fecha=fechaString, hora=horaString, tipo=accion)
        db.session.add(registroMarcajeEmpleado)
        db.session.commit()

        #mirar si configura el registro tambien es enviar por Odata
        configuracion = Config.query.filter_by(id=0).first()
        if configuracion != None:
            if configuracion.TipoConexionBC == 'Odata':
                idapp = configuracion.IdClienteBC
                valor = configuracion.secretClienteBC
                tenant = configuracion.tenantBC
                empresa = configuracion.empresaBC
                sincronizarMarcajeFiltradoOdata(tenant,idapp,valor,empresa, registroMarcajeEmpleado)
            if configuracion.TipoConexionBC == 'Soap':
                url = configuracion.urlBC
                username = configuracion.usuarioSOAP
                password = configuracion.passwordSOAP
                print(url)
                print(username)
                print(password)
                sincronizarMarcajeFiltradpSOAP(url,username,password,registroMarcajeEmpleado)
        return 'OK'
    
@app.route('/SincroBC', methods=['GET', 'POST'])
@login_required
def SincroBC():
    #mirar si el usuario es admin
    user = User.query.filter_by(username=current_user.username).first()
    if user.rol_admin == True:
        sincronizar()
    return redirect(url_for('inicio'))

#Funciones extra
def sincronizarMarcajeFiltradoOdata(tenant,idapp,valor,empresa, marcaje):
    try:
        #creamos json de envio
        empleado = marcaje.id_empleado
        fecha = marcaje.fecha
        #fecha en formato dd/mm/yyyy
        fecha = fecha[8:10]+"/"+fecha[5:7]+"/"+fecha[0:4]
        fecha = datetime.datetime.now().strftime("%d/%m/%Y")
        hora = marcaje.hora
        tipo = marcaje.tipo
        envioDatos = json.dumps({"input": "{\"empleado\":\""+empleado+"\",\"fecha\":\""+fecha+"\",\"hora\":\""+hora+"\",\"tipo\":\""+tipo+"\"}"})
        #enviamos datos
        datos = ws.getConnectionBC(tenant,idapp,valor,"NuevaEntradaSalida",empresa,envioDatos)
        datos = json.loads(datos)
        datos = datos["value"]
        if datos == "OK":
            marcaje.sincronizado = True
            db.session.commit()
    except:
        pass

def sincronizarMarcajesPorTareaFiltradoOdata(tenant,idapp,valor,empresa,registro):
    try:
        empleado = registro.id_empleado
        proyecto = registro.proyecto
        tarea = registro.tarea
        fecha = registro.fecha
        horas = registro.tiempo
        #fecha en formato yyyy-mm-dd
        fecha = fecha[0:4]+"-"+fecha[5:7]+"-"+fecha[8:10]
        fecha = datetime.datetime.now().strftime("%d/%m/%Y")
        comentarios = proyecto + " - " + tarea
        envioDatos = json.dumps({"input": "{\"empleado\":\""+empleado+"\",\"fecha\":\""+fecha+"\",\"horas\":\""+horas+"\",\"comentarios\":\""+comentarios+"\",\"proyecto\":\""+proyecto+"\",\"tarea\":\""+tarea+"\"}"})
        #enviamos datos
        datos = ws.getConnectionBC(tenant,idapp,valor,"CreateJobJournalLine",empresa,envioDatos)
        datos = json.loads(datos)
        datos = datos["value"]
        if datos == "OK":
            registro.sincronizado = True
            db.session.commit()
    except:
        pass

def sincronizarEmpleadosOdata(tenant,idapp,valor,empresa):
    datos = ws.getConnectionBC(tenant,idapp,valor,"getEmpleados",empresa,"")
    datos = json.loads(datos)
    try: 
        datos = datos["value"]
        datos = json.loads(datos)
        datos = datos["empleados"]
        for dato in datos:
            try:
                #Buscamos si existe el empleado existe en user
                user = User.query.filter_by(id_Empleado=dato["id"]).first()
                if user is None:
                    #Si no existe lo creamos
                    has_password = Bcrypt().generate_password_hash('admin').decode('utf-8')
                    admin = User(username=dato["id"], password=has_password, nombre=dato["nombre"], apellido=dato["apellidos"], id_Empleado=dato["id"], rol_admin=False)
                    db.session.add(admin)
                    db.session.commit()
                else:
                    #Si existe lo actualizamos
                    user.nombre = dato["nombre"]
                    user.apellido = dato["apellidos"]
                    db.session.commit()
            except:
                #si hya error escribimos en el archivo log
                f = open("log.txt", "a")
                f.write("Error al sincronizar empleados "+str(dato))
                f.close()
    except:
        #si hya error escribimos en el archivo log
        f = open("log.txt", "a")
        f.write("Error al sincronizar empleados "+str(datos))
        f.close()

def sincronizarProyectosOdata(tenant,idapp,valor,empresa):
    datos = ws.getConnectionBC(tenant,idapp,valor,"GetJob",empresa,"")
    datos = json.loads(datos)

    try:
        datos = datos["value"]
        datos = json.loads(datos)
        proyectos = datos["proyectos"]
        tareas = datos["tareas"]

        for proyecto in proyectos:
            try:
                #Buscamos si existe el proyecto en la base de datos
                proyectoBD = Proyecto.query.filter_by(id_proyecto=proyecto["proyecto"]).first()
                if proyectoBD is None:
                    #Si no existe lo creamos
                    admin = Proyecto(id_proyecto=proyecto["proyecto"], nombre_proyecto=proyecto["descripcion"], id_cliente=proyecto["idCliente"], nombre_cliente=proyecto["cliente"])
                    db.session.add(admin)
                    db.session.commit()
                else:
                    #Si existe lo actualizamos
                    proyectoBD.nombre = proyecto["nombre"]
                    proyectoBD.id_cliente = proyecto["id_cliente"]
                    proyectoBD.nombre_cliente = proyecto["nombre_cliente"]
                    db.session.commit()
            except:
                #si hya error escribimos en el archivo log
                f = open("log.txt", "a")
                f.write("Error al sincronizar proyectos "+str(proyecto))
                f.close()
        
        for tarea in tareas:
            try:
                #Buscamos si existe la tarea en la base de datos
                tareaBD = Tarea.query.filter_by(id_tarea=tarea["tarea"], id_proyecto=tarea["proyecto"]).first()
                if tareaBD is None:
                    #Si no existe lo creamos
                    admin = Tarea(id_tarea=tarea["tarea"], nombre_tarea=tarea["descripcion"], id_proyecto=tarea["proyecto"], nombre_proyecto=tarea["descripcionProyecto"])
                    db.session.add(admin)
                    db.session.commit()
                else:
                    #Si existe lo actualizamos
                    tareaBD.nombre_tarea = tarea["descripcion"]
                    tareaBD.nombre_proyecto = tarea["descripcionProyecto"]
                    db.session.commit()
            except:
                #si hya error escribimos en el archivo log
                f = open("log.txt", "a")
                f.write("Error al sincronizar tareas "+str(tarea))
                f.close()
    except:
        #si hya error escribimos en el archivo log
        f = open("log.txt", "a")
        f.write("Error al sincronizar proyectos "+str(datos))
        f.close()

def sincronizarTareasEmpleadosOdata(tenant,idapp,valor,empresa):
    #getTareasEmpleado
    datos = ws.getConnectionBC(tenant,idapp,valor,"getTareasEmpleado",empresa,"")
    datos = json.loads(datos)
    try:
        datos = datos["value"]
        datos = json.loads(datos)
        datos = datos["tareasEmpleado"]
        for dato in datos:
            try:
                #si existe en TareaEmpleado
                tareaEmpleado = TareaEmpleado.query.filter_by(id_empleado=dato["empleado"], id_tarea=dato["tarea"], id_proyecto=dato["proyecto"]).first()
                if tareaEmpleado is None:
                    #Si no existe lo creamos
                    admin = TareaEmpleado(id_empleado=dato["empleado"], id_tarea=dato["tarea"], id_proyecto=dato["proyecto"], nombre_tarea=dato["descripcionTarea"], nombre_proyecto=dato["descripcionProyecto"])
                    db.session.add(admin)
                    db.session.commit()
                else:
                    #Si existe lo actualizamos
                    tareaEmpleado.nombre_tarea = dato["descripcionTarea"]
                    tareaEmpleado.nombre_proyecto = dato["descripcionProyecto"]
                    db.session.commit()
            except:
                #si hya error escribimos en el archivo log
                f = open("log.txt", "a")
                f.write("Error al sincronizar tareas de empleados "+str(dato))
                f.close()
    except:
        #si hya error escribimos en el archivo log
        f = open("log.txt", "a")
        f.write("Error al sincronizar tareas de empleados "+str(datos))
        f.close()

def sincronizarMarcajesOdata(tenant,idapp,valor,empresa):
    #buscar marcajes desde RegistroMarcaje
    marcajes = RegistroMarcaje.query.filter_by(sincronizado=False).all()
    for marcaje in marcajes:
        try:
            #creamos json de envio
            empleado = marcaje.id_empleado
            fecha = marcaje.fecha
            #fecha en formato dd/mm/yyyy
            fecha = fecha[8:10]+"/"+fecha[5:7]+"/"+fecha[0:4]
            fecha = datetime.datetime.now().strftime("%d/%m/%Y")
            hora = marcaje.hora
            tipo = marcaje.tipo
            envioDatos = json.dumps({"input": "{\"empleado\":\""+empleado+"\",\"fecha\":\""+fecha+"\",\"hora\":\""+hora+"\",\"tipo\":\""+tipo+"\"}"})
            #enviamos datos
            datos = ws.getConnectionBC(tenant,idapp,valor,"NuevaEntradaSalida",empresa,envioDatos)
            datos = json.loads(datos)
            datos = datos["value"]
            if datos == "OK":
                marcaje.sincronizado = True
                db.session.commit()
        except:
            #escritura en archivo de log
            f = open("log.txt", "a")
            f.write("Error al sincronizar marcaje: " + str(marcaje.id))
            f.close()
            
def sincronizarMarcajesPorTareaOdata(tenant,idapp,valor,empresa):
    #buscar marcajes desde RegistroMarcaje en RegistroMarcajePorTarea
    marcajes = RegistroMarcajePorTarea.query.filter_by(sincronizado=False).all()
    for registro in marcajes:
        try:
            empleado = registro.id_empleado
            proyecto = registro.proyecto
            tarea = registro.tarea
            fecha = registro.fecha
            horas = registro.tiempo
            #fecha en formato yyyy-mm-dd
            fecha = fecha[0:4]+"-"+fecha[5:7]+"-"+fecha[8:10]
            fecha = datetime.datetime.now().strftime("%d/%m/%Y")
            comentarios = proyecto + " - " + tarea

            envioDatos = json.dumps({"input": "{\"empleado\":\""+empleado+"\",\"fecha\":\""+fecha+"\",\"horas\":\""+horas+"\",\"comentarios\":\""+comentarios+"\",\"proyecto\":\""+proyecto+"\",\"tarea\":\""+tarea+"\"}"})
            #enviamos datos
            datos = ws.getConnectionBC(tenant,idapp,valor,"CreateJobJournalLine",empresa,envioDatos)
            datos = json.loads(datos)
            datos = datos["value"]
            if datos == "OK":
                registro.sincronizado = True
                db.session.commit()
        except:
            #crear arhivo de log
            f = open("log.txt", "a")
            f.write("Error al sincronizar marcaje por tarea: " + str(registro.id))
            f.close()

#Soap:
def sincronizarMarcajeFiltradpSOAP(url,username,password,marcaje):
    try:
        client = Client(url=url,username=username,password=password)
        #creamos json de envio
        empleado = marcaje.id_empleado
        fecha = marcaje.fecha
        #fecha en formato dd/mm/yyyy
        fecha = fecha[8:10]+"/"+fecha[5:7]+"/"+fecha[0:4]
        #fecha de hoy en formato dd/mm/yyyy
        fecha = datetime.datetime.now().strftime("%d/%m/%Y")
        hora = marcaje.hora
        tipo = marcaje.tipo
        envioDatos = "{\"empleado\":\""+empleado+"\",\"fecha\":\""+fecha+"\",\"hora\":\""+hora+"\",\"tipo\":\""+tipo+"\"}"
        respuesta = client.service.NuevaEntradaSalida(envioDatos)
        if respuesta == "OK":
            marcaje.sincronizado = True
            db.session.commit()
    except:
        pass

def sincronizarMarcajesPorTareaFiltradoSoap(url,username,password,registro):
    try:
        client = Client(url=url,username=username,password=password)
        empleado = registro.id_empleado
        proyecto = registro.proyecto
        tarea = registro.tarea
        fecha = registro.fecha
        horas = registro.tiempo
        #fecha en formato yyyy-mm-dd
        fecha = fecha[0:4]+"-"+fecha[5:7]+"-"+fecha[8:10]
        fecha = datetime.datetime.now().strftime("%d/%m/%Y")
        comentarios = proyecto + " - " + tarea
        envioDatos = "{\"empleado\":\""+empleado+"\",\"fecha\":\""+fecha+"\",\"horas\":\""+horas+"\",\"comentarios\":\""+comentarios+"\",\"proyecto\":\""+proyecto+"\",\"tarea\":\""+tarea+"\"}"
        #enviamos datos

        print(envioDatos)

        respuesta = client.service.CreateJobJournalLine(envioDatos)
        if respuesta == "OK":
            registro.sincronizado = True
            db.session.commit()
    except:
        pass

def sincronizarEmpleadosSoap(url,username,password):
    #datos = ws.getConnectionBC(tenant,idapp,valor,"getEmpleados",empresa,"")
    #datos = json.loads(datos)
    try: 
        client = Client(url=url,username=username,password=password)
        datos = client.service.getEmpleados()
        datos = json.loads(datos)
        datos = datos["empleados"]
        for dato in datos:
            try:
                #Buscamos si existe el empleado existe en user
                user = User.query.filter_by(id_Empleado=dato["id"]).first()
                if user is None:
                    #Si no existe lo creamos
                    has_password = Bcrypt().generate_password_hash('admin').decode('utf-8')
                    admin = User(username=dato["id"], password=has_password, nombre=dato["nombre"], apellido=dato["apellidos"], id_Empleado=dato["id"], rol_admin=False)
                    db.session.add(admin)
                    db.session.commit()
                else:
                    #Si existe lo actualizamos
                    user.nombre = dato["nombre"]
                    user.apellido = dato["apellidos"]
                    db.session.commit()
            except:
                #si hya error escribimos en el archivo log
                f = open("log.txt", "a")
                f.write("Error al sincronizar empleados "+str(dato))
                f.close()
    except:
        #si hya error escribimos en el archivo log
        f = open("log.txt", "a")
        f.write("Error al sincronizar empleados "+str(datos))
        f.close()

def sincronizarProyectosSoap(url,username,password):
    try:
        client = Client(url=url,username=username,password=password)
        datos = client.service.GetJob()
        datos = json.loads(datos)
        proyectos = datos["proyectos"]
        tareas = datos["tareas"]

        for proyecto in proyectos:
            try:
                #Buscamos si existe el proyecto en la base de datos
                proyectoBD = Proyecto.query.filter_by(id_proyecto=proyecto["proyecto"]).first()
                if proyectoBD is None:
                    #Si no existe lo creamos
                    admin = Proyecto(id_proyecto=proyecto["proyecto"], nombre_proyecto=proyecto["descripcion"], id_cliente=proyecto["idCliente"], nombre_cliente=proyecto["cliente"])
                    db.session.add(admin)
                    db.session.commit()
                else:
                    #Si existe lo actualizamos
                    proyectoBD.nombre = proyecto["nombre"]
                    proyectoBD.id_cliente = proyecto["id_cliente"]
                    proyectoBD.nombre_cliente = proyecto["nombre_cliente"]
                    db.session.commit()
            except:
                #si hya error escribimos en el archivo log
                f = open("log.txt", "a")
                f.write("Error al sincronizar proyectos "+str(proyecto))
                f.close()
        
        for tarea in tareas:
            try:
                #Buscamos si existe la tarea en la base de datos
                tareaBD = Tarea.query.filter_by(id_tarea=tarea["tarea"], id_proyecto=tarea["proyecto"]).first()
                if tareaBD is None:
                    #Si no existe lo creamos
                    admin = Tarea(id_tarea=tarea["tarea"], nombre_tarea=tarea["descripcion"], id_proyecto=tarea["proyecto"], nombre_proyecto=tarea["descripcionProyecto"])
                    db.session.add(admin)
                    db.session.commit()
                else:
                    #Si existe lo actualizamos
                    tareaBD.nombre_tarea = tarea["descripcion"]
                    tareaBD.nombre_proyecto = tarea["descripcionProyecto"]
                    db.session.commit()
            except:
                #si hya error escribimos en el archivo log
                f = open("log.txt", "a")
                f.write("Error al sincronizar tareas "+str(tarea))
                f.close()
    except:
        #si hya error escribimos en el archivo log
        f = open("log.txt", "a")
        f.write("Error al sincronizar proyectos "+str(datos))
        f.close()

def sincronizarTareasEmpleadosSoap(url,username,password):
    try:
        client = Client(url=url,username=username,password=password)
        datos = client.service.getTareasEmpleado()
        datos = json.loads(datos)
        datos = datos["tareasEmpleado"]
        for dato in datos:
            try:
                #si existe en TareaEmpleado
                tareaEmpleado = TareaEmpleado.query.filter_by(id_empleado=dato["empleado"], id_tarea=dato["tarea"], id_proyecto=dato["proyecto"]).first()
                if tareaEmpleado is None:
                    #Si no existe lo creamos
                    admin = TareaEmpleado(id_empleado=dato["empleado"], id_tarea=dato["tarea"], id_proyecto=dato["proyecto"], nombre_tarea=dato["descripcionTarea"], nombre_proyecto=dato["descripcionProyecto"])
                    db.session.add(admin)
                    db.session.commit()
                else:
                    #Si existe lo actualizamos
                    tareaEmpleado.nombre_tarea = dato["descripcionTarea"]
                    tareaEmpleado.nombre_proyecto = dato["descripcionProyecto"]
                    db.session.commit()
            except:
                #si hya error escribimos en el archivo log
                f = open("log.txt", "a")
                f.write("Error al sincronizar tareas de empleados "+str(dato))
                f.close()
    except:
        #si hya error escribimos en el archivo log
        f = open("log.txt", "a")
        f.write("Error al sincronizar tareas de empleados "+str(datos))
        f.close()

def sincronizarMarcajesSoap(url,username,password):
    #buscar marcajes desde RegistroMarcaje
    marcajes = RegistroMarcaje.query.filter_by(sincronizado=False).all()
    for marcaje in marcajes:
        try:
            #creamos json de envio
            empleado = marcaje.id_empleado
            fecha = marcaje.fecha
            #fecha en formato dd/mm/yyyy
            fecha = fecha[8:10]+"/"+fecha[5:7]+"/"+fecha[0:4]
            fecha = datetime.datetime.now().strftime("%d/%m/%Y")
            hora = marcaje.hora
            tipo = marcaje.tipo
            envioDatos = json.dumps({"input": "{\"empleado\":\""+empleado+"\",\"fecha\":\""+fecha+"\",\"hora\":\""+hora+"\",\"tipo\":\""+tipo+"\"}"})
            #enviamos datos
            client = Client(url=url,username=username,password=password)
            datos = client.service.NuevaEntradaSalida(envioDatos)
            datos = json.loads(datos)
            datos = datos["value"]
            if datos == "OK":
                marcaje.sincronizado = True
                db.session.commit()
        except:
            #escritura en archivo de log
            f = open("log.txt", "a")
            f.write("Error al sincronizar marcaje: " + str(marcaje.id))
            f.close()
            
def sincronizarMarcajesPorTareaSoap(url,username,password):
    #buscar marcajes desde RegistroMarcaje en RegistroMarcajePorTarea
    marcajes = RegistroMarcajePorTarea.query.filter_by(sincronizado=False).all()
    for registro in marcajes:
        try:
            empleado = registro.id_empleado
            proyecto = registro.proyecto
            tarea = registro.tarea
            fecha = registro.fecha
            horas = registro.tiempo
            #fecha en formato yyyy-mm-dd
            fecha = fecha[0:4]+"-"+fecha[5:7]+"-"+fecha[8:10]
            fecha = datetime.datetime.now().strftime("%d/%m/%Y")
            comentarios = proyecto + " - " + tarea

            envioDatos = json.dumps({"input": "{\"empleado\":\""+empleado+"\",\"fecha\":\""+fecha+"\",\"horas\":\""+horas+"\",\"comentarios\":\""+comentarios+"\",\"proyecto\":\""+proyecto+"\",\"tarea\":\""+tarea+"\"}"})
            #enviamos datos
            print(envioDatos)
            client = Client(url=url,username=username,password=password)
            datos = client.service.CreateJobJournalLine(envioDatos)
            datos = json.loads(datos)
            datos = datos["value"]
            if datos == "OK":
                registro.sincronizado = True
                db.session.commit()
            
        except:
            #crear arhivo de log
            f = open("log.txt", "a")
            f.write("Error al sincronizar marcaje por tarea: " + str(registro.id))
            f.close()

#Funcion para sincronizar los datos de la base de datos con Business Central
def sincronizar():
    #borrar los datos del archivo log.txt
    f = open("log.txt", "w")
    f.write("")
    f.close()

    configuracion = Config.query.filter_by(id=0).first()
    print(configuracion.TipoConexionBC)
    if configuracion.TipoConexionBC == "Soap":
        url = configuracion.urlBC
        username = configuracion.usuarioSOAP
        password = configuracion.passwordSOAP
        
        print(url)
        print(username)
        print(password)
        sincronizarEmpleadosSoap(url,username,password)
        sincronizarProyectosSoap(url,username,password)
        sincronizarTareasEmpleadosSoap(url,username,password)
        sincronizarMarcajesSoap(url,username,password)
        sincronizarMarcajesPorTareaSoap(url,username,password)
        
    elif configuracion.TipoConexionBC == "Odata":
        idapp = configuracion.idClienteBC
        valor = configuracion.secretClienteBC
        tenant = configuracion.tenantBC
        empresa = configuracion.empresaBC

        # idapp = '44dd2790-02fb-42c0-9d0d-36eeb8fd4cee'
        # valor = 'VO_8Q~e6XM7isBVpsCGPViyuMyTTRSSCewoIfat4'
        # idsectreto = '79171359-8529-4ee7-95b3-3eacd8a1d081'
        # tenant = '5f5f63d8-e0f2-4301-9e3e-8817644d3071'
        # empresa = '''CRONUS%20ES'''    

        print(tenant)
        print(idapp)
        print(valor)
        print(empresa)

        sincronizarEmpleadosOdata(tenant,idapp,valor,empresa)
        sincronizarProyectosOdata(tenant,idapp,valor,empresa)
        sincronizarTareasEmpleadosOdata(tenant,idapp,valor,empresa)
        sincronizarMarcajesOdata(tenant,idapp,valor,empresa)
        sincronizarMarcajesPorTareaOdata(tenant,idapp,valor,empresa)
    else:
        print("No se ha seleccionado un tipo de conexion")

@app.route('/Analisis', methods=['GET', 'POST'])
@login_required
def Analisis():
    return render_template('Analisis.html')

#/exportarExcelRegistros
@app.route('/exportarExcelRegistros', methods=['GET', 'POST'])
@login_required
def exportarExcelRegistros():
    #miramos si el usuario es administrador
    user = User.query.filter_by(id=current_user.id).first()
    if user.rol_admin:
        #si es admin exportamos todos los registros
        registros = RegistroMarcaje.query.all()
        registroPorTareas = RegistroMarcajePorTarea.query.all()
    else:
        #si no es admin exportamos los registros del usuario
        registros = RegistroMarcaje.query.filter_by(id_empleado=current_user.id).all()
        registroPorTareas = RegistroMarcajePorTarea.query.filter_by(id_empleado=current_user.id).all()
    #creamos el archivo excel con pandas
    df = pd.DataFrame(columns=['id','id_empleado','fecha','hora','tipo'])
    for registro in registros:
        df = df.append({'id':registro.id,'id_empleado':registro.id_empleado,'fecha':registro.fecha,'hora':registro.hora,'tipo':registro.tipo},ignore_index=True)
    #enviamos el archivo excel al navegador
    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, sheet_name='Sheet1')
    writer.save()
    output.seek(0)
    
    return send_file(output, attachment_filename="registros.xlsx", as_attachment=True)

#/exportarExcelRegistrosTarea
@app.route('/exportarExcelRegistrosTarea', methods=['GET', 'POST'])
@login_required
def exportarExcelRegistrosTarea():
    #miramos si el usuario es administrador
    user = User.query.filter_by(id=current_user.id).first()
    if user.rol_admin:
        registros = RegistroMarcajePorTarea.query.all()
    else:
        registros = RegistroMarcajePorTarea.query.filter_by(id_empleado=current_user.id).all()
    #creamos el archivo excel con pandas
    df = pd.DataFrame(columns=['id','id_empleado','fecha','tiempo','proyecto','tarea','sincronizado'])
    for registro in registros:
        df = df.append({'id':registro.id,'id_empleado':registro.id_empleado,'fecha':registro.fecha,'tiempo':registro.tiempo,'proyecto':registro.proyecto,'tarea':registro.tarea,'sincronizado':registro.sincronizado},ignore_index=True)
    #enviamos el archivo excel al navegador
    output2 = io.BytesIO()
    writer = pd.ExcelWriter(output2, engine='xlsxwriter')
    df.to_excel(writer, sheet_name='Sheet1')
    writer.save()
    output2.seek(0)
    
    return send_file(output2, attachment_filename="registrosTarea.xlsx", as_attachment=True)

# #/InformePdfRegistros
# @app.route('/InformePdfRegistros', methods=['GET', 'POST'])
# @login_required
# def InformePdfRegistros():
