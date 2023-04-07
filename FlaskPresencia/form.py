from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, BooleanField
from wtforms.validators import Length, ValidationError, InputRequired
from FlaskPresencia.models import *

#Formularios:
class RegisterForm(FlaskForm):
    username = StringField(validators=[InputRequired(), Length(min=4, max=50)], render_kw={"placeholder": "Username"},
    id="username", label="Nombre de usuario")
    password = PasswordField(validators=[InputRequired(), Length(min=4, max=50)], render_kw={"placeholder": "Password"},
    id="password", label="Contraseña")
    submit = SubmitField('Register', id="submit")

    def validate_username(self, username):
        existing_user_username = User.query.filter_by(username=username.data).first()
        if existing_user_username:
            raise ValidationError('El usuaio ya existe, por favor ingrese otro')

class LoginForm(FlaskForm):
    username = StringField(validators=[InputRequired(), Length(min=4, max=50)], render_kw={"placeholder": "Username"}, 
    id="username")
    password = PasswordField(validators=[InputRequired(), Length(min=4, max=50)], render_kw={"placeholder": "Password"},
    id="password")
    submit = SubmitField('Login', id="submit")

class EditRegistroMarcaje(FlaskForm):
    #Mostrar label en el formulario
    id_empleado = StringField(validators=[InputRequired(), Length(min=0, max=50)], render_kw={"placeholder": "id_empleado"},
    id="id_empleado", label="ID Empleado")
    fecha = StringField(validators=[InputRequired(), Length(min=0, max=50)], render_kw={"placeholder": "fecha"},
    id="fecha", label="Fecha")
    #input tipo time
    hora = StringField(validators=[InputRequired(), Length(min=0, max=50)], render_kw={"placeholder": "hora"},
    id="hora", label="Hora")
    #tipo opciones: entrada (E) o salida (S)
    tipo   = SelectField(validators=[InputRequired(), Length(min=0, max=50)], render_kw={"placeholder": "tipo"},
    id="tipo", label="Tipo", choices=[('E', 'Entrada'), ('S', 'Salida')])
    submit = SubmitField('Editar', id="submit")

class EditRegistroMarcajePorTarea(FlaskForm):
    id_empleado = StringField(validators=[InputRequired(), Length(min=0, max=50)], render_kw={"placeholder": "id_empleado"},
    id="id_empleado", label="ID Empleado")
    tiempo = StringField(validators=[InputRequired(), Length(min=0, max=50)], render_kw={"placeholder": "tiempo"},
    id="tiempo", label="Tiempo")
    fecha = StringField(validators=[InputRequired(), Length(min=0, max=50)], render_kw={"placeholder": "fecha"},
    id="fecha", label="Fecha")
    #select de los proyectos
    proyectos = Proyecto.query.all()
    proyecto = SelectField(validators=[InputRequired(), Length(min=0, max=50)], render_kw={"placeholder": "proyecto"},
    id="Proyecto", label="Proyecto", choices=[(proyecto.id_proyecto, proyecto.nombre_proyecto) for proyecto in proyectos])
    #select de las tareas
    tareas = Tarea.query.all()
    tarea = SelectField(validators=[InputRequired(), Length(min=0, max=50)], render_kw={"placeholder": "tarea"},
    id="Tarea", label="Tarea", choices=[(tarea.id_tarea, tarea.nombre_tarea) for tarea in tareas])
    submit = SubmitField('Editar', id="submit")

class FormConfiguacion(FlaskForm):
    Empresa = StringField(validators=[InputRequired(), Length(min=0, max=50)], render_kw={"placeholder": "Empresa"},
    id="Empresa", label="Empresa")
    ImgEmpresaBase64 = StringField(validators=[InputRequired(), Length(min=0, max=50)], render_kw={"placeholder": "ImgEmpresaBase64"},
    id="ImgEmpresaBase64", label="ImgEmpresaBase64")
    ImgEmpresaTipo = StringField(validators=[InputRequired(), Length(min=0, max=50)], render_kw={"placeholder": "ImgEmpresaTipo"},
    id="ImgEmpresaTipo", label="ImgEmpresaTipo")
    #tipo opciones: <option>Ninguna</option><option>Soap</option><option>Odata</option>
    TipoConexionBC = SelectField(validators=[InputRequired(), Length(min=0, max=50)], render_kw={"placeholder": "TipoConexionBC"},
    id="TipoConexionBC", label="TipoConexionBC", choices=[('Ninguna', 'Ninguna'), ('Soap', 'Soap'), ('Odata', 'Odata')])
    urlBC = StringField(validators=[InputRequired(), Length(min=0, max=50)], render_kw={"placeholder": "urlBC"},
    id="urlBC", label="urlBC")
    usuarioSOAP = StringField(validators=[InputRequired(), Length(min=0, max=50)], render_kw={"placeholder": "usuarioSOAP"},
    id="usuarioSOAP", label="usuarioSOAP")
    passwordSOAP = StringField(validators=[InputRequired(), Length(min=0, max=50)], render_kw={"placeholder": "passwordSOAP"},
    id="passwordSOAP", label="passwordSOAP")
    tenantBC = StringField(validators=[InputRequired(), Length(min=0, max=50)], render_kw={"placeholder": "tenantBC"},
    id="tenantBC", label="tenantBC")
    idClienteBC = StringField(validators=[InputRequired(), Length(min=0, max=50)], render_kw={"placeholder": "idClienteBC"},
    id="idClienteBC", label="idClienteBC")
    secretClienteBC = StringField(validators=[InputRequired(), Length(min=0, max=50)], render_kw={"placeholder": "secretClienteBC"},
    id="secretClienteBC", label="secretClienteBC")
    empresaBC = StringField(validators=[InputRequired(), Length(min=0, max=50)], render_kw={"placeholder": "empresaBC"},
    id="empresaBC", label="empresaBC")
    submit = SubmitField('Editar', id="submit")


class FormEmpleado(FlaskForm):
    #Mostrar label en el formulario
    username = StringField(validators=[InputRequired(), Length(min=0, max=50)], render_kw={"placeholder": "username"},
    id="username", label="Nombre de usuario")
    nombre = StringField(validators=[InputRequired(), Length(min=0, max=50)], render_kw={"placeholder": "nombre"},
    id="nombre", label="Nombre")
    apellido = StringField(validators=[InputRequired(), Length(min=0, max=50)], render_kw={"placeholder": "apellido"},
    id="apellido", label="Apellido")
    id_Empleado = StringField(validators=[InputRequired(), Length(min=0, max=50)], render_kw={"placeholder": "id_Empleado"},
    id="id_Empleado", label="ID Empleado")
    submit = SubmitField('Guardar', id="submit")

