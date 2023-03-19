#pip install suds
import config
import sqlalchemy
import json
from models import *
import ConexionesBC.WSnav as ws
from suds.client import Client
from flask_bcrypt import Bcrypt

#client = Client(url="",username="",password="")
#respuesta = client.service.wsGetEmployeeByCardNumber("","")
# idapp = '44dd2790-02fb-42c0-9d0d-36eeb8fd4cee'
# valor = 'VO_8Q~e6XM7isBVpsCGPViyuMyTTRSSCewoIfat4'
# idsectreto = '79171359-8529-4ee7-95b3-3eacd8a1d081'
# tenant = '5f5f63d8-e0f2-4301-9e3e-8817644d3071'
# empresa = '''CRONUS%20ES''' 
  
def sincronizarEmpleadosOdata(tenant,idapp,valor,empresa):
    datos = ws.getConnectionBC(tenant,idapp,valor,"getEmpleados",empresa,"")
    datos = json.loads(datos)
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

def sincronizarProyectosOdata(tenant,idapp,valor,empresa):
    datos = ws.getConnectionBC(tenant,idapp,valor,"GetJob",empresa,"")
    datos = json.loads(datos)
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

def sincronizarTareasEmpleadosOdata(tenant,idapp,valor,empresa):
    #getTareasEmpleado
    datos = ws.getConnectionBC(tenant,idapp,valor,"getTareasEmpleado",empresa,"")
    datos = json.loads(datos)
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

#Funcion para sincronizar los datos de la base de datos con Business Central
def sincronizar():
    configuracion = Config.query.filter_by(id=0).first()
    print(configuracion.TipoConexionBC)
    if configuracion.TipoConexionBC == "SOAP":
        print("Conectando con SOAP")
    elif configuracion.TipoConexionBC == "OData":
        idapp = configuracion.idClienteBC
        valor = configuracion.secretClienteBC
        tenant = configuracion.tenantBC
        empresa = configuracion.empresaBC

        # idapp = '44dd2790-02fb-42c0-9d0d-36eeb8fd4cee'
        # valor = 'VO_8Q~e6XM7isBVpsCGPViyuMyTTRSSCewoIfat4'
        # idsectreto = '79171359-8529-4ee7-95b3-3eacd8a1d081'
        # tenant = '5f5f63d8-e0f2-4301-9e3e-8817644d3071'
        # empresa = '''CRONUS%20ES'''    

        sincronizarEmpleadosOdata(tenant,idapp,valor,empresa)
        sincronizarProyectosOdata(tenant,idapp,valor,empresa)
        sincronizarTareasEmpleadosOdata(tenant,idapp,valor,empresa)
        sincronizarMarcajesOdata(tenant,idapp,valor,empresa)
        sincronizarMarcajesPorTareaOdata(tenant,idapp,valor,empresa)
    else:
        print("No se ha seleccionado un tipo de conexion")

#funcion main
if __name__ == '__main__':
    sincronizar()