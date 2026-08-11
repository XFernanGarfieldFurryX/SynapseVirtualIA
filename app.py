# ============================================================
# SYNAPSE VIRTUAL IA - Plataforma Educativa Inteligente
# Versión 2.3 (CON VERIFICACIÓN DE .ENV AL INICIO)
# ============================================================

import logging
import random
import re
from datetime import datetime, timedelta
from functools import wraps
 
import pymysql
import pytz
from dotenv import load_dotenv
from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
    Blueprint,
    current_app,
)
from flask_mail import Mail, Message
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.exceptions import HTTPException

from config import Config, get_config
from asistentes import (
    consultar_asistente_admin,
    responder_docente,
    responder_estudiante,
    responder_soporte,
)

# ------------------------------------------------------------
# LOGGING
# ------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

load_dotenv()

# ============================================================
# VERIFICACIÓN DE .ENV AL INICIO (MEJORADA)
# ============================================================
from config import config

print("\n" + "="*50)
print("🚀 INICIANDO SYNAPSE VIRTUAL IA")
print("="*50)
print(f"🔑 GEMINI_API_KEY: {'✅ Cargada' if config.GEMINI_API_KEY else '❌ NO CARGADA'}")
if config.GEMINI_API_KEY:
    print(f"   (primeros 10 caracteres: {config.GEMINI_API_KEY[:10]}...)")
print(f"🔄 IA_PROVIDER: {config.IA_PROVIDER}")
print(f"🗄️ MYSQL_HOST: {config.MYSQL_HOST}")
print("="*50 + "\n")

# ============================================================
# FUNCIONES DE SERVICIO
# ============================================================

def obtener_fecha_venezuela():
    tz = pytz.timezone("America/Caracas")
    return datetime.now(tz)

def obtener_conexion(app_config=None):
    try:
        if app_config is None:
            try:
                app_config = current_app.config
            except RuntimeError:
                from config import config
                return obtener_conexion_directa(config)
        
        conexion = pymysql.connect(
            host=app_config.get("MYSQL_HOST", "localhost"),
            port=app_config.get("MYSQL_PORT", 3306),
            user=app_config.get("MYSQL_USER", "root"),
            password=app_config.get("MYSQL_PASSWORD", ""),
            database=app_config.get("MYSQL_DB", "synapse_virtual_ia"),
            charset=app_config.get("MYSQL_CHARSET", "utf8mb4"),
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=10,
        )
        conexion.ping(reconnect=True)
        return conexion
    except Exception as e:
        logger.error(f"❌ Error al conectar a MySQL: {e}")
        return None

def obtener_conexion_directa(config_obj):
    try:
        conexion = pymysql.connect(
            host=config_obj.MYSQL_HOST,
            port=config_obj.MYSQL_PORT,
            user=config_obj.MYSQL_USER,
            password=config_obj.MYSQL_PASSWORD,
            database=config_obj.MYSQL_DB,
            charset=config_obj.MYSQL_CHARSET,
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=10,
        )
        conexion.ping(reconnect=True)
        return conexion
    except Exception as e:
        logger.error(f"❌ Error al conectar a MySQL: {e}")
        return None

def ejecutar_consulta(query, params=None, fetch_one=False, fetch_all=False, commit=False):
    conn = obtener_conexion()
    if not conn:
        return None
    try:
        with conn.cursor() as cursor:
            cursor.execute(query, params or ())
            if commit:
                conn.commit()
            if fetch_one:
                return cursor.fetchone()
            if fetch_all:
                return cursor.fetchall()
            return cursor.lastrowid if commit else None
    except Exception as e:
        logger.error(f"❌ Error ejecutando consulta: {e}")
        if commit:
            conn.rollback()
        return None
    finally:
        conn.close()

def enviar_correo(destinatario, asunto, mensaje_html):
    try:
        msg = Message(
            subject=asunto,
            recipients=[destinatario],
            html=mensaje_html,
            sender=current_app.config["MAIL_DEFAULT_SENDER"],
        )
        mail = current_app.extensions.get('mail')
        if mail:
            mail.send(msg)
            logger.info(f"✅ Correo enviado a {destinatario}")
            return True
        return False
    except Exception as e:
        logger.error(f"❌ Error al enviar correo: {e}")
        return False

def registrar_auditoria(accion, modulo):
    if "id" not in session:
        return None
    ip = request.remote_addr or "0.0.0.0"
    query = """
        INSERT INTO auditoria (id_usuario, usuario, rol, accion, modulo, fecha, ip)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    params = (
        session.get("id"),
        session.get("nombre"),
        session.get("rol"),
        accion,
        modulo,
        obtener_fecha_venezuela(),
        ip,
    )
    return ejecutar_consulta(query, params, commit=True)

# ============================================================
# FUNCIÓN: OBTENER ESTADÍSTICAS
# ============================================================
def obtener_stats():
    stats = {
        'total_usuarios': 0,
        'tickets_abiertos': 0,
        'tickets_cerrados': 0,
        'total_calificaciones': 0,
    }
    total_usuarios = ejecutar_consulta("SELECT COUNT(*) AS total FROM usuarios", fetch_one=True)
    if total_usuarios:
        stats['total_usuarios'] = total_usuarios['total']
    tickets_abiertos = ejecutar_consulta("SELECT COUNT(*) AS total FROM tickets WHERE estado='abierto'", fetch_one=True)
    if tickets_abiertos:
        stats['tickets_abiertos'] = tickets_abiertos['total']
    tickets_cerrados = ejecutar_consulta("SELECT COUNT(*) AS total FROM tickets WHERE estado='cerrado'", fetch_one=True)
    if tickets_cerrados:
        stats['tickets_cerrados'] = tickets_cerrados['total']
    total_calif = ejecutar_consulta("SELECT COUNT(*) AS total FROM calificaciones", fetch_one=True)
    if total_calif:
        stats['total_calificaciones'] = total_calif['total']
    return stats

# ------------------------------------------------------------
# DECORADORES
# ------------------------------------------------------------

def login_requerido(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "id" not in session:
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated

def rol_requerido(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if "rol" not in session or session["rol"] not in roles:
                flash("No tienes permisos para acceder.", "danger")
                return redirect(url_for("public.index"))
            return f(*args, **kwargs)
        return decorated
    return decorator

def manejar_excepciones(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"❌ Error en {f.__name__}: {e}")
            flash("Ocurrió un error inesperado.", "danger")
            return redirect(request.referrer or url_for("public.index"))
    return decorated

# ------------------------------------------------------------
# BLUEPRINTS
# ------------------------------------------------------------

public_bp = Blueprint('public', __name__, url_prefix='')
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
docente_bp = Blueprint('docente', __name__, url_prefix='/docente')
estudiante_bp = Blueprint('estudiante', __name__, url_prefix='/estudiante')
soporte_bp = Blueprint('soporte', __name__, url_prefix='/soporte')
ia_bp = Blueprint('ia', __name__, url_prefix='/ia')

# ------------------------------------------------------------
# RUTAS PÚBLICAS
# ------------------------------------------------------------

@public_bp.route('/')
def index():
    stats = obtener_stats()
    return render_template('index.html', stats=stats, session=session)

@public_bp.route('/health')
def health():
    conn = obtener_conexion()
    status = {
        "status": "ok" if conn else "error",
        "database": "connected" if conn else "disconnected",
        "timestamp": obtener_fecha_venezuela().isoformat(),
    }
    if conn:
        conn.close()
    return status, 200 if conn else 503

# ------------------------------------------------------------
# RUTAS DE AUTENTICACIÓN (MEJORADAS)
# ------------------------------------------------------------

@auth_bp.route('/login', methods=['GET', 'POST'])
@manejar_excepciones
def login():
    if request.method == 'POST':
        usuario_o_correo = request.form.get('usuario', '').strip().lower()
        password = request.form.get('password', '').strip()
        
        if not usuario_o_correo or not password:
            flash('Usuario y contraseña son obligatorios.', 'warning')
            return render_template('login.html')

        # 🔍 Buscar en la tabla 'usuarios_final' por correo o por nombre de usuario
        user = None
        if '@' in usuario_o_correo:
            user = ejecutar_consulta(
                "SELECT * FROM usuarios WHERE correo = %s AND activo = 1", 
                (usuario_o_correo,), 
                fetch_one=True
            )
        else:
            user = ejecutar_consulta(
                "SELECT * FROM usuarios WHERE usuario = %s AND activo = 1", 
                (usuario_o_correo,), 
                fetch_one=True
            )

        # 🔍 Comparación de contraseñas en TEXTO PLANO (Plan B)
        if user and user['password'] == password:
            session['id'] = user['id']
            session['nombre'] = user['nombre']
            session['rol'] = user['rol']
            session['correo'] = user['correo']
            session.permanent = True

            registrar_auditoria('Inicio de sesión exitoso', 'Login')

            # Redirecciones según el rol
            redirecciones = {
                'admin': 'admin.administracion',
                'profesor': 'docente.profesores',
                'estudiante': 'estudiante.estudiantes',
                'soporte': 'soporte.soporte',
            }
            return redirect(url_for(redirecciones.get(user['rol'], 'soporte.soporte')))
        else:
            logger.warning(f"⚠️ Falló login para {usuario_o_correo}")
            flash('Credenciales inválidas o usuario inactivo.', 'danger')
            return render_template('login.html')

    return render_template('login.html')

@auth_bp.route('/logout')
@login_requerido
def logout():
    registrar_auditoria('Cerró sesión', 'Login')
    session.clear()
    flash('Sesión cerrada exitosamente.', 'info')
    return redirect(url_for('public.index'))

@auth_bp.route('/recuperar', methods=['GET', 'POST'])
@manejar_excepciones
def recuperar():
    if request.method == 'POST':
        correo = request.form.get('usuario', '').strip().lower()
        if not correo:
            flash('Ingresa tu correo electrónico.', 'warning')
            return render_template('recuperar.html')

        usuario = ejecutar_consulta(
            "SELECT id, nombre, correo FROM usuarios WHERE correo=%s",
            (correo,),
            fetch_one=True
        )
        if not usuario:
            flash('No se encontró una cuenta con ese correo.', 'danger')
            return render_template('recuperar.html')

        codigo = str(random.randint(100000, 999999))
        expiracion = datetime.now() + timedelta(minutes=10)
        ejecutar_consulta("DELETE FROM reset_codigos WHERE id_usuario = %s", (usuario['id'],), commit=True)
        ejecutar_consulta(
            "INSERT INTO reset_codigos (id_usuario, codigo, fecha_expiracion) VALUES (%s, %s, %s)",
            (usuario['id'], codigo, expiracion),
            commit=True
        )
        flash('Código enviado a tu correo.', 'success')
        return redirect(url_for('auth.verificar_codigo', correo=usuario['correo']))

    return render_template('recuperar.html')

@auth_bp.route('/verificar_codigo', methods=['GET', 'POST'])
@manejar_excepciones
def verificar_codigo():
    if request.method == 'POST':
        correo = request.form.get('correo', '').strip().lower()
        codigo = request.form.get('codigo', '').strip()
        if not correo or not codigo or len(codigo) != 6 or not codigo.isdigit():
            flash('Datos inválidos.', 'danger')
            return render_template('verificar_codigo.html', correo=correo)

        usuario = ejecutar_consulta(
            "SELECT id FROM usuarios WHERE correo=%s",
            (correo,),
            fetch_one=True
        )
        if not usuario:
            flash('Usuario no encontrado.', 'danger')
            return render_template('verificar_codigo.html', correo=correo)

        res = ejecutar_consulta(
            "SELECT fecha_expiracion, usado FROM reset_codigos WHERE id_usuario=%s AND codigo=%s",
            (usuario['id'], codigo),
            fetch_one=True
        )
        if res and not res['usado'] and datetime.now() <= res['fecha_expiracion']:
            session['reset_usuario_id'] = usuario['id']
            session['reset_codigo'] = codigo
            return redirect(url_for('auth.restablecer'))
        else:
            flash('Código inválido o expirado.', 'danger')
            return render_template('verificar_codigo.html', correo=correo)

    correo = request.args.get('correo', '')
    return render_template('verificar_codigo.html', correo=correo)

@auth_bp.route('/restablecer', methods=['GET', 'POST'])
@manejar_excepciones
def restablecer():
    if 'reset_usuario_id' not in session or 'reset_codigo' not in session:
        flash('Acceso no autorizado.', 'danger')
        return redirect(url_for('auth.recuperar'))

    if request.method == 'POST':
        nueva = request.form.get('password', '').strip()
        confirmar = request.form.get('confirmar_password', '').strip()
        if len(nueva) < 6:
            flash('La contraseña debe tener al menos 6 caracteres.', 'danger')
            return render_template('restablecer.html')
        if nueva != confirmar:
            flash('Las contraseñas no coinciden.', 'danger')
            return render_template('restablecer.html')

        hashed = generate_password_hash(nueva)
        exito = ejecutar_consulta(
            "UPDATE usuarios SET password=%s WHERE id=%s",
            (hashed, session['reset_usuario_id']),
            commit=True
        )
        if exito is not None:
            ejecutar_consulta(
                "UPDATE reset_codigos SET usado=TRUE WHERE id_usuario=%s AND codigo=%s",
                (session['reset_usuario_id'], session['reset_codigo']),
                commit=True
            )
            flash('Contraseña actualizada correctamente.', 'success')
            session.pop('reset_usuario_id', None)
            session.pop('reset_codigo', None)
            return redirect(url_for('auth.login'))
        else:
            flash('Error al actualizar la contraseña.', 'danger')

    return render_template('restablecer.html')

# ------------------------------------------------------------
# RUTAS DE ADMINISTRACIÓN
# ------------------------------------------------------------

@admin_bp.route('/dashboard', methods=['GET', 'POST'])
@login_requerido
@rol_requerido('admin')
@manejar_excepciones
def administracion():
    respuesta = ''
    if request.method == 'POST':
        pregunta = request.form.get('pregunta', '').strip()
        if pregunta:
            respuesta = f"🛠 Consulta administrativa: '{pregunta}' (pendiente de implementación)"
            registrar_auditoria(f'Consulta admin: {pregunta[:50]}', 'Administración')
        else:
            flash('Escribe una consulta.', 'warning')

    stats = obtener_stats()
    return render_template('administracion.html', respuesta=respuesta, stats=stats)

# ============================================================
# ADMIN: AUDITORÍA AVANZADA
# ============================================================
 
@admin_bp.route('/auditoria', methods=['GET'])
@login_requerido
@rol_requerido('admin')
@manejar_excepciones
def auditoria():
    """Lista registros de auditoría con filtros y paginación."""
    # Obtener parámetros de filtro
    usuario_filtro = request.args.get('usuario', '').strip()
    modulo_filtro = request.args.get('modulo', '').strip()
    fecha_desde = request.args.get('fecha_desde', '').strip()
    fecha_hasta = request.args.get('fecha_hasta', '').strip()
    pagina = request.args.get('pagina', 1, type=int)
    por_pagina = 10

    # Construir consulta base
    query = """
        SELECT a.*
        FROM auditoria a
        WHERE 1=1
    """
    params = []
    count_query = "SELECT COUNT(*) AS total FROM auditoria a WHERE 1=1"
    count_params = []

    if usuario_filtro:
        query += " AND a.usuario LIKE %s"
        params.append(f"%{usuario_filtro}%")
        count_query += " AND a.usuario LIKE %s"
        count_params.append(f"%{usuario_filtro}%")
    if modulo_filtro:
        query += " AND a.modulo LIKE %s"
        params.append(f"%{modulo_filtro}%")
        count_query += " AND a.modulo LIKE %s"
        count_params.append(f"%{modulo_filtro}%")
    if fecha_desde:
        query += " AND a.fecha >= %s"
        params.append(fecha_desde)
        count_query += " AND a.fecha >= %s"
        count_params.append(fecha_desde)
    if fecha_hasta:
        query += " AND a.fecha <= %s"
        params.append(fecha_hasta + " 23:59:59")
        count_query += " AND a.fecha <= %s"
        count_params.append(fecha_hasta + " 23:59:59")

    # Obtener total de registros para paginación
    total_result = ejecutar_consulta(count_query, count_params, fetch_one=True)
    total_registros = total_result['total'] if total_result else 0
    total_paginas = (total_registros + por_pagina - 1) // por_pagina

    # Obtener registros con paginación
    query += " ORDER BY a.fecha DESC LIMIT %s OFFSET %s"
    params.append(por_pagina)
    params.append((pagina - 1) * por_pagina)

    registros = ejecutar_consulta(query, params, fetch_all=True) or []

    # Lista de módulos únicos para el filtro
    modulos = ejecutar_consulta(
        "SELECT DISTINCT modulo FROM auditoria ORDER BY modulo",
        fetch_all=True
    ) or []
    modulos = [m['modulo'] for m in modulos if m['modulo']]

    return render_template(
        'auditoria.html',
        registros=registros,
        modulos=modulos,
        usuario_filtro=usuario_filtro,
        modulo_filtro=modulo_filtro,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        pagina=pagina,
        total_paginas=total_paginas,
        total_registros=total_registros,
        por_pagina=por_pagina
    )

@admin_bp.route('/auditoria/detalle/<int:auditoria_id>')
@login_requerido
@rol_requerido('admin')
@manejar_excepciones
def auditoria_detalle(auditoria_id):
    """Obtiene los detalles de un registro de auditoría (para modal)."""
    registro = ejecutar_consulta(
        "SELECT * FROM auditoria WHERE id = %s",
        (auditoria_id,),
        fetch_one=True
    )
    if not registro:
        return {"error": "Registro no encontrado"}, 404

    detalles = ejecutar_consulta(
        "SELECT campo, valor_anterior, valor_nuevo FROM detalle_auditoria WHERE id_auditoria = %s",
        (auditoria_id,),
        fetch_all=True
    ) or []

    return render_template(
        'auditoria_detalle.html',
        registro=registro,
        detalles=detalles
    )

@admin_bp.route('/auditoria/eliminar/<int:auditoria_id>', methods=['POST'])
@login_requerido
@rol_requerido('admin')
@manejar_excepciones
def auditoria_eliminar(auditoria_id):
    """Elimina un registro de auditoría y sus detalles."""
    # Verificar que existe
    registro = ejecutar_consulta(
        "SELECT id FROM auditoria WHERE id = %s",
        (auditoria_id,),
        fetch_one=True
    )
    if not registro:
        flash('Registro no encontrado.', 'danger')
        return redirect(url_for('admin.auditoria'))

    # Eliminar detalles (ON DELETE CASCADE, pero si no está configurado, lo hacemos manual)
    ejecutar_consulta(
        "DELETE FROM detalle_auditoria WHERE id_auditoria = %s",
        (auditoria_id,),
        commit=True
    )
    # Eliminar registro
    exito = ejecutar_consulta(
        "DELETE FROM auditoria WHERE id = %s",
        (auditoria_id,),
        commit=True
    )
    if exito is not None:
        flash('✅ Registro de auditoría eliminado correctamente.', 'success')
    else:
        flash('Error al eliminar el registro.', 'danger')

    return redirect(url_for('admin.auditoria'))

@admin_bp.route('/auditoria/limpiar', methods=['POST'])
@login_requerido
@rol_requerido('admin')
@manejar_excepciones
def auditoria_limpiar():
    """Elimina TODOS los registros de auditoría (con confirmación en el frontend)."""
    # Primero eliminar detalles
    ejecutar_consulta("DELETE FROM detalle_auditoria", commit=True)
    # Luego eliminar auditoria
    exito = ejecutar_consulta("DELETE FROM auditoria", commit=True)
    if exito is not None:
        flash('✅ Todos los registros de auditoría han sido eliminados.', 'success')
    else:
        flash('Error al limpiar la auditoría.', 'danger')
    return redirect(url_for('admin.auditoria'))

# ============================================================
# ADMIN: GESTIÓN DE USUARIOS
# ============================================================

@admin_bp.route('/usuarios')
@login_requerido
@rol_requerido('admin')
@manejar_excepciones
def listar_usuarios():
    logger.info("🔍 Ejecutando consulta de usuarios...")
    
    total = ejecutar_consulta("SELECT COUNT(*) AS total FROM usuarios", fetch_one=True)
    logger.info(f"📊 Total de usuarios en BD: {total['total'] if total else 0}")
    
    usuarios = ejecutar_consulta(
        "SELECT id, nombre, correo, rol, activo, fecha_creacion FROM usuarios ORDER BY id",
        fetch_all=True
    ) or []
    
    logger.info(f"👥 Usuarios obtenidos: {len(usuarios)}")
    for u in usuarios:
        logger.info(f"  - {u['nombre']} ({u['rol']}) - Activo: {u['activo']}")
    
    return render_template('admin_usuarios.html', usuarios=usuarios)

@admin_bp.route('/usuario/editar/<int:user_id>', methods=['GET', 'POST'])
@login_requerido
@rol_requerido('admin')
@manejar_excepciones
def editar_usuario(user_id):
    usuario = ejecutar_consulta(
        "SELECT * FROM usuarios WHERE id = %s",
        (user_id,),
        fetch_one=True
    )
    if not usuario:
        flash('Usuario no encontrado.', 'danger')
        return redirect(url_for('admin.listar_usuarios'))

    if request.method == 'POST':
        rol = request.form.get('rol')
        activo = request.form.get('activo') == 'on'
        nueva_password = request.form.get('password', '').strip()
        
        if rol not in ['admin', 'profesor', 'estudiante', 'soporte']:
            flash('Rol inválido.', 'danger')
            return render_template('admin_editar_usuario.html', usuario=usuario)
        
        if nueva_password:
            if len(nueva_password) < 6:
                flash('La contraseña debe tener al menos 6 caracteres.', 'danger')
                return render_template('admin_editar_usuario.html', usuario=usuario)
            hashed = generate_password_hash(nueva_password)
            exito = ejecutar_consulta(
                "UPDATE usuarios SET rol = %s, activo = %s, password = %s WHERE id = %s",
                (rol, activo, hashed, user_id),
                commit=True
            )
        else:
            exito = ejecutar_consulta(
                "UPDATE usuarios SET rol = %s, activo = %s WHERE id = %s",
                (rol, activo, user_id),
                commit=True
            )
        
        if exito is not None:
            registrar_auditoria(f'Usuario {usuario["nombre"]} actualizado (rol={rol}, activo={activo})', 'Admin')
            flash('Usuario actualizado correctamente.', 'success')
            return redirect(url_for('admin.listar_usuarios'))
        else:
            flash('Error al actualizar el usuario.', 'danger')
    
    return render_template('admin_editar_usuario.html', usuario=usuario)

@admin_bp.route('/usuario/eliminar/<int:user_id>', methods=['POST'])
@login_requerido
@rol_requerido('admin')
@manejar_excepciones
def eliminar_usuario(user_id):
    if user_id == session.get('id'):
        flash('No puedes eliminarte a ti mismo.', 'danger')
        return redirect(url_for('admin.listar_usuarios'))
    
    usuario = ejecutar_consulta(
        "SELECT nombre FROM usuarios WHERE id = %s",
        (user_id,),
        fetch_one=True
    )
    if not usuario:
        flash('Usuario no encontrado.', 'danger')
        return redirect(url_for('admin.listar_usuarios'))
    
    exito = ejecutar_consulta(
        "DELETE FROM usuarios WHERE id = %s",
        (user_id,),
        commit=True
    )
    if exito is not None:
        registrar_auditoria(f'Usuario "{usuario["nombre"]}" (ID {user_id}) eliminado', 'Admin')
        flash(f'✅ Usuario "{usuario["nombre"]}" eliminado correctamente.', 'success')
    else:
        flash('Error al eliminar el usuario.', 'danger')
    
    return redirect(url_for('admin.listar_usuarios'))

@admin_bp.route('/usuario/resetear_password/<int:user_id>', methods=['POST'])
@login_requerido
@rol_requerido('admin')
@manejar_excepciones
def resetear_password(user_id):
    """Resetea la contraseña de un usuario a '123456'."""
    usuario = ejecutar_consulta(
        "SELECT nombre FROM usuarios WHERE id = %s",
        (user_id,),
        fetch_one=True
    )
    if not usuario:
        flash('Usuario no encontrado.', 'danger')
        return redirect(url_for('admin.listar_usuarios'))
    
    nueva_password = '123456'
    hashed = generate_password_hash(nueva_password)
    exito = ejecutar_consulta(
        "UPDATE usuarios SET password = %s WHERE id = %s",
        (hashed, user_id),
        commit=True
    )
    if exito is not None:
        registrar_auditoria(f'Contraseña de "{usuario["nombre"]}" reseteada a {nueva_password}', 'Admin')
        flash(f'✅ Contraseña de "{usuario["nombre"]}" reseteada a "{nueva_password}".', 'success')
    else:
        flash('Error al resetear la contraseña.', 'danger')
    
    return redirect(url_for('admin.listar_usuarios'))

# ============================================================
# ADMIN: CREAR USUARIO
# ============================================================

@admin_bp.route('/usuario/crear', methods=['GET', 'POST'])
@login_requerido
@rol_requerido('admin')
@manejar_excepciones
def crear_usuario():
    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        correo = request.form.get('correo', '').strip().lower()
        rol = request.form.get('rol')
        password = request.form.get('password', '').strip()
        
        if not nombre or not correo or not password:
            flash('Todos los campos son obligatorios.', 'danger')
            return render_template('admin_crear_usuario.html')
        
        if not re.match(r"[^@]+@[^@]+\.[^@]+", correo):
            flash('Correo electrónico inválido.', 'danger')
            return render_template('admin_crear_usuario.html')
        
        if rol not in ['admin', 'profesor', 'estudiante', 'soporte']:
            flash('Rol inválido.', 'danger')
            return render_template('admin_crear_usuario.html')
        
        if len(password) < 6:
            flash('La contraseña debe tener al menos 6 caracteres.', 'danger')
            return render_template('admin_crear_usuario.html')
        
        existe = ejecutar_consulta(
            "SELECT id FROM usuarios WHERE correo = %s",
            (correo,),
            fetch_one=True
        )
        if existe:
            flash('El correo ya está registrado.', 'danger')
            return render_template('admin_crear_usuario.html')
        
        hashed = generate_password_hash(password)
        exito = ejecutar_consulta(
            "INSERT INTO usuarios (nombre, correo, password, rol) VALUES (%s, %s, %s, %s)",
            (nombre, correo, hashed, rol),
            commit=True
        )
        if exito is not None:
            registrar_auditoria(f'Usuario "{nombre}" creado (rol={rol})', 'Admin')
            flash(f'✅ Usuario "{nombre}" creado correctamente.', 'success')
            return redirect(url_for('admin.listar_usuarios'))
        else:
            flash('Error al crear el usuario.', 'danger')
    
    return render_template('admin_crear_usuario.html')

# ============================================================
# ADMIN: GESTIÓN DE TICKETS
# ============================================================

@admin_bp.route('/tickets')
@login_requerido
@rol_requerido('admin')
@manejar_excepciones
def listar_tickets():
    tickets = ejecutar_consulta(
        """
        SELECT t.*, u.nombre AS usuario_nombre 
        FROM tickets t 
        JOIN usuarios u ON t.usuario_id = u.id 
        ORDER BY t.fecha_creacion DESC
        """,
        fetch_all=True
    ) or []
    return render_template('admin_tickets.html', tickets=tickets)

@admin_bp.route('/ticket/actualizar/<int:ticket_id>', methods=['POST'])
@login_requerido
@rol_requerido('admin')
@manejar_excepciones
def actualizar_ticket(ticket_id):
    nuevo_estado = request.form.get('estado')
    if nuevo_estado not in ['abierto', 'en proceso', 'cerrado']:
        flash('Estado inválido.', 'danger')
        return redirect(url_for('admin.listar_tickets'))
    
    exito = ejecutar_consulta(
        "UPDATE tickets SET estado = %s WHERE id = %s",
        (nuevo_estado, ticket_id),
        commit=True
    )
    if exito is not None:
        registrar_auditoria(f'Ticket #{ticket_id} actualizado a "{nuevo_estado}"', 'Admin')
        flash('Ticket actualizado correctamente.', 'success')
    else:
        flash('Error al actualizar el ticket.', 'danger')
    
    return redirect(url_for('admin.listar_tickets'))

@admin_bp.route('/ticket/eliminar/<int:ticket_id>', methods=['POST'])
@login_requerido
@rol_requerido('admin')
@manejar_excepciones
def eliminar_ticket(ticket_id):
    ticket = ejecutar_consulta(
        "SELECT id, asunto FROM tickets WHERE id = %s",
        (ticket_id,),
        fetch_one=True
    )
    if not ticket:
        flash('Ticket no encontrado.', 'danger')
        return redirect(url_for('admin.listar_tickets'))
    
    exito = ejecutar_consulta(
        "DELETE FROM tickets WHERE id = %s",
        (ticket_id,),
        commit=True
    )
    if exito is not None:
        registrar_auditoria(f'Ticket #{ticket_id} "{ticket["asunto"]}" eliminado', 'Admin')
        flash(f'✅ Ticket #{ticket_id} eliminado correctamente.', 'success')
    else:
        flash('Error al eliminar el ticket.', 'danger')
    
    return redirect(url_for('admin.listar_tickets'))

# ============================================================
# ADMIN: GESTIÓN DE CALIFICACIONES (VERSIÓN MEJORADA)
# ============================================================

@admin_bp.route('/calificaciones')
@login_requerido
@rol_requerido('admin', 'profesor')
@manejar_excepciones
def listar_calificaciones():
    """Lista todas las calificaciones con filtros opcionales."""
    filtro_estudiante = request.args.get('estudiante_id', '').strip()
    filtro_materia = request.args.get('materia_id', '').strip()
    filtro_lapso = request.args.get('lapso', '').strip()

    query = """
        SELECT c.id, c.nota, c.lapso, c.observacion,
               u.nombre AS estudiante_nombre, u.id AS estudiante_id,
               m.nombre AS materia_nombre, m.id AS materia_id
        FROM calificaciones c
        JOIN usuarios u ON c.estudiante_id = u.id
        JOIN materias m ON c.materia_id = m.id
        WHERE 1=1
    """
    params = []

    if filtro_estudiante:
        query += " AND u.id = %s"
        params.append(filtro_estudiante)
    if filtro_materia:
        query += " AND m.id = %s"
        params.append(filtro_materia)
    if filtro_lapso:
        query += " AND c.lapso = %s"
        params.append(filtro_lapso)

    query += " ORDER BY u.nombre, m.nombre, c.lapso"

    calificaciones = ejecutar_consulta(query, params, fetch_all=True) or []

    # Listas para los filtros
    estudiantes = ejecutar_consulta(
        "SELECT id, nombre FROM usuarios WHERE rol = 'estudiante' ORDER BY nombre",
        fetch_all=True
    ) or []
    materias = ejecutar_consulta(
        "SELECT id, nombre FROM materias ORDER BY nombre",
        fetch_all=True
    ) or []
    lapsos = ['1er Lapso', '2do Lapso', '3er Lapso']

    return render_template(
        'admin_calificaciones.html',
        calificaciones=calificaciones,
        estudiantes=estudiantes,
        materias=materias,
        lapsos=lapsos,
        filtro_estudiante=filtro_estudiante,
        filtro_materia=filtro_materia,
        filtro_lapso=filtro_lapso
    )


@admin_bp.route('/calificacion/crear', methods=['GET', 'POST'])
@login_requerido
@rol_requerido('admin', 'profesor')
@manejar_excepciones
def crear_calificacion():
    """Crea una nueva calificación con validación de duplicado."""
    if request.method == 'POST':
        estudiante_id = request.form.get('estudiante_id')
        materia_id = request.form.get('materia_id')
        lapso = request.form.get('lapso')
        nota = request.form.get('nota')
        observacion = request.form.get('observacion', '').strip()

        # Validaciones básicas
        if not estudiante_id or not materia_id or not lapso or not nota:
            flash('Todos los campos son obligatorios.', 'danger')
            return redirect(url_for('admin.crear_calificacion'))

        try:
            nota = float(nota)
            if nota < 0 or nota > 20:
                flash('La nota debe estar entre 0 y 20.', 'danger')
                return redirect(url_for('admin.crear_calificacion'))
        except ValueError:
            flash('Formato de nota inválido.', 'danger')
            return redirect(url_for('admin.crear_calificacion'))

        # Verificar que el estudiante existe y es estudiante
        estudiante = ejecutar_consulta(
            "SELECT id FROM usuarios WHERE id = %s AND rol = 'estudiante'",
            (estudiante_id,),
            fetch_one=True
        )
        if not estudiante:
            flash('Estudiante no válido.', 'danger')
            return redirect(url_for('admin.crear_calificacion'))

        # Verificar que la materia existe
        materia = ejecutar_consulta(
            "SELECT id FROM materias WHERE id = %s",
            (materia_id,),
            fetch_one=True
        )
        if not materia:
            flash('Materia no válida.', 'danger')
            return redirect(url_for('admin.crear_calificacion'))

        # Verificar duplicado (mismo estudiante, materia, lapso)
        existe = ejecutar_consulta(
            "SELECT id FROM calificaciones WHERE estudiante_id = %s AND materia_id = %s AND lapso = %s",
            (estudiante_id, materia_id, lapso),
            fetch_one=True
        )
        if existe:
            flash('Ya existe una calificación para este estudiante, materia y lapso.', 'danger')
            return redirect(url_for('admin.crear_calificacion'))

        # Insertar
        exito = ejecutar_consulta(
            "INSERT INTO calificaciones (estudiante_id, materia_id, lapso, nota, observacion) VALUES (%s, %s, %s, %s, %s)",
            (estudiante_id, materia_id, lapso, nota, observacion),
            commit=True
        )
        if exito is not None:
            registrar_auditoria(f'Calificación creada: Estudiante {estudiante_id}, Materia {materia_id}, Lapso {lapso}', 'Admin')
            flash('✅ Calificación creada correctamente.', 'success')
            return redirect(url_for('admin.listar_calificaciones'))
        else:
            flash('Error al crear la calificación.', 'danger')

    # GET: mostrar formulario
    estudiantes = ejecutar_consulta(
        "SELECT id, nombre FROM usuarios WHERE rol = 'estudiante' ORDER BY nombre",
        fetch_all=True
    ) or []
    materias = ejecutar_consulta(
        "SELECT id, nombre FROM materias ORDER BY nombre",
        fetch_all=True
    ) or []
    lapsos = ['1er Lapso', '2do Lapso', '3er Lapso']

    return render_template(
        'admin_crear_calificacion.html',
        estudiantes=estudiantes,
        materias=materias,
        lapsos=lapsos
    )


@admin_bp.route('/calificacion/editar/<int:calificacion_id>', methods=['GET', 'POST'])
@login_requerido
@rol_requerido('admin', 'profesor')
@manejar_excepciones
def editar_calificacion(calificacion_id):
    """Edita solo lapso, nota y observación (no permite cambiar estudiante ni materia)."""
    calificacion = ejecutar_consulta(
        """
        SELECT c.*, u.nombre AS estudiante_nombre, m.nombre AS materia_nombre
        FROM calificaciones c
        JOIN usuarios u ON c.estudiante_id = u.id
        JOIN materias m ON c.materia_id = m.id
        WHERE c.id = %s
        """,
        (calificacion_id,),
        fetch_one=True
    )
    if not calificacion:
        flash('Calificación no encontrada.', 'danger')
        return redirect(url_for('admin.listar_calificaciones'))

    if request.method == 'POST':
        lapso = request.form.get('lapso')
        nota = request.form.get('nota')
        observacion = request.form.get('observacion', '').strip()

        if not lapso or not nota:
            flash('Lapso y nota son obligatorios.', 'danger')
            return render_template('admin_editar_calificacion.html', calificacion=calificacion)

        try:
            nota = float(nota)
            if nota < 0 or nota > 20:
                flash('La nota debe estar entre 0 y 20.', 'danger')
                return render_template('admin_editar_calificacion.html', calificacion=calificacion)
        except ValueError:
            flash('Formato de nota inválido.', 'danger')
            return render_template('admin_editar_calificacion.html', calificacion=calificacion)

        exito = ejecutar_consulta(
            "UPDATE calificaciones SET lapso = %s, nota = %s, observacion = %s WHERE id = %s",
            (lapso, nota, observacion, calificacion_id),
            commit=True
        )
        if exito is not None:
            registrar_auditoria(f'Calificación #{calificacion_id} actualizada', 'Admin')
            flash('✅ Calificación actualizada correctamente.', 'success')
            return redirect(url_for('admin.listar_calificaciones'))
        else:
            flash('Error al actualizar la calificación.', 'danger')

    lapsos = ['1er Lapso', '2do Lapso', '3er Lapso']
    return render_template(
        'admin_editar_calificacion.html',
        calificacion=calificacion,
        lapsos=lapsos
    )


@admin_bp.route('/calificacion/eliminar/<int:calificacion_id>', methods=['POST'])
@login_requerido
@rol_requerido('admin', 'profesor')
@manejar_excepciones
def eliminar_calificacion(calificacion_id):
    """Elimina una calificación."""
    calificacion = ejecutar_consulta(
        "SELECT id FROM calificaciones WHERE id = %s",
        (calificacion_id,),
        fetch_one=True
    )
    if not calificacion:
        flash('Calificación no encontrada.', 'danger')
        return redirect(url_for('admin.listar_calificaciones'))

    exito = ejecutar_consulta(
        "DELETE FROM calificaciones WHERE id = %s",
        (calificacion_id,),
        commit=True
    )
    if exito is not None:
        registrar_auditoria(f'Calificación #{calificacion_id} eliminada', 'Admin')
        flash('✅ Calificación eliminada correctamente.', 'success')
    else:
        flash('Error al eliminar la calificación.', 'danger')

    return redirect(url_for('admin.listar_calificaciones'))

# ------------------------------------------------------------
# RUTAS DE DOCENTES, ESTUDIANTES, SOPORTE E IA (sin cambios)
# ------------------------------------------------------------
@docente_bp.route('/panel', methods=['GET', 'POST'])
@login_requerido
@rol_requerido('profesor', 'admin')
@manejar_excepciones
def profesores():
    respuesta = ''
    if request.method == 'POST':
        pregunta = request.form.get('pregunta', '').strip()
        if pregunta:
            respuesta = responder_docente(pregunta)
            registrar_auditoria(f'Consulta docente: {pregunta[:50]}', 'Asistente')
        else:
            flash('Escribe una pregunta.', 'warning')
    return render_template('profesores.html', respuesta=respuesta)

@estudiante_bp.route('/panel', methods=['GET', 'POST'])
@login_requerido
@rol_requerido('estudiante', 'admin')
@manejar_excepciones
def estudiantes():
    respuesta = ''
    if request.method == 'POST':
        pregunta = request.form.get('pregunta', '').strip()
        if pregunta:
            respuesta = responder_estudiante(pregunta)
            registrar_auditoria(f'Consulta estudiante: {pregunta[:50]}', 'Asistente')
        else:
            flash('Escribe una pregunta.', 'warning')
    return render_template('estudiantes.html', respuesta=respuesta)

@estudiante_bp.route('/lapsos')
@login_requerido
@manejar_excepciones
def lapsos():
    if session['rol'] == 'estudiante':
        query = """
            SELECT c.*, m.nombre AS materia_nombre
            FROM calificaciones c
            JOIN materias m ON c.materia_id = m.id
            WHERE c.estudiante_id = %s
        """
        params = (session['id'],)
    else:
        query = """
            SELECT c.*, u.nombre AS estudiante_nombre, m.nombre AS materia_nombre
            FROM calificaciones c
            JOIN usuarios u ON c.estudiante_id = u.id
            JOIN materias m ON c.materia_id = m.id
        """
        params = ()
    notas = ejecutar_consulta(query, params, fetch_all=True) or []
    return render_template('lapsos.html', notas=notas)

@estudiante_bp.route('/actividades')
@login_requerido
@manejar_excepciones
def actividades():
    materias = ejecutar_consulta("SELECT * FROM materias", fetch_all=True) or []
    return render_template('actividades.html', actividades=materias)

@soporte_bp.route('/panel', methods=['GET', 'POST'])
@login_requerido
@manejar_excepciones
def soporte():
    respuesta = ''
    if request.method == 'POST':
        pregunta = request.form.get('pregunta', '').strip()
        if pregunta:
            respuesta = responder_soporte(pregunta)
            ticket_id = ejecutar_consulta(
                "INSERT INTO tickets (usuario_id, asunto, descripcion, estado) VALUES (%s, %s, %s, 'abierto')",
                (session['id'], 'Consulta desde soporte', pregunta),
                commit=True
            )
            if ticket_id:
                registrar_auditoria(f'Ticket creado: {pregunta[:50]}', 'Soporte')
                flash('Ticket creado exitosamente.', 'success')
            else:
                flash('Error al crear el ticket.', 'danger')
        else:
            flash('Describe el problema.', 'warning')

    if session['rol'] in ('admin', 'soporte'):
        tickets = ejecutar_consulta("SELECT * FROM tickets ORDER BY fecha_creacion DESC", fetch_all=True) or []
    else:
        tickets = ejecutar_consulta(
            "SELECT * FROM tickets WHERE usuario_id=%s ORDER BY fecha_creacion DESC",
            (session['id'],),
            fetch_all=True
        ) or []
    return render_template('soporte.html', respuesta=respuesta, tickets=tickets)

@ia_bp.route('/consulta', methods=['GET', 'POST'])
@login_requerido  # Solo requiere inicio de sesión
@manejar_excepciones
def ia():
    respuesta = ''
    if request.method == 'POST':
        pregunta = request.form.get('pregunta', '').strip()
        if pregunta:
            # Usar el asistente según el rol del usuario
            rol = session.get('rol')
            if rol == 'admin':
                respuesta = consultar_asistente_admin(pregunta)
            elif rol == 'profesor':
                respuesta = responder_docente(pregunta)
            elif rol == 'estudiante':
                respuesta = responder_estudiante(pregunta)
            elif rol == 'soporte':
                respuesta = responder_soporte(pregunta)
            else:
                respuesta = consultar_asistente_admin(pregunta)  # fallback
            registrar_auditoria(f'Consulta IA: {pregunta[:50]}', 'IA')
        else:
            flash('Escribe una pregunta.', 'warning')
    return render_template('ia.html', respuesta=respuesta)

# ------------------------------------------------------------
# INICIALIZACIÓN DE BASE DE DATOS
# ------------------------------------------------------------

def inicializar_base_datos():
    tablas = {
        'usuarios': """
            CREATE TABLE IF NOT EXISTS usuarios (
                id INT AUTO_INCREMENT PRIMARY KEY,
                nombre VARCHAR(100) NOT NULL,
                correo VARCHAR(100) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                rol ENUM('admin','profesor','estudiante','soporte') NOT NULL,
                activo BOOLEAN DEFAULT TRUE,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """,
        'auditoria': """
            CREATE TABLE IF NOT EXISTS auditoria (
                id INT AUTO_INCREMENT PRIMARY KEY,
                id_usuario INT,
                usuario VARCHAR(100),
                rol VARCHAR(20),
                accion VARCHAR(255),
                modulo VARCHAR(50),
                fecha DATETIME,
                ip VARCHAR(45)
            )
        """,
        'detalle_auditoria': """
            CREATE TABLE IF NOT EXISTS detalle_auditoria (
                id INT AUTO_INCREMENT PRIMARY KEY,
                id_auditoria INT,
                campo VARCHAR(50),
                valor_anterior TEXT,
                valor_nuevo TEXT,
                FOREIGN KEY (id_auditoria) REFERENCES auditoria(id) ON DELETE CASCADE
            )
        """,
        'reset_codigos': """
            CREATE TABLE IF NOT EXISTS reset_codigos (
                id INT AUTO_INCREMENT PRIMARY KEY,
                id_usuario INT,
                codigo VARCHAR(6),
                fecha_expiracion DATETIME,
                usado BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (id_usuario) REFERENCES usuarios(id) ON DELETE CASCADE
            )
        """,
        'tickets': """
            CREATE TABLE IF NOT EXISTS tickets (
                id INT AUTO_INCREMENT PRIMARY KEY,
                usuario_id INT,
                asunto VARCHAR(255),
                descripcion TEXT,
                estado ENUM('abierto','en proceso','cerrado') DEFAULT 'abierto',
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
            )
        """,
        'materias': """
            CREATE TABLE IF NOT EXISTS materias (
                id INT AUTO_INCREMENT PRIMARY KEY,
                nombre VARCHAR(100) NOT NULL,
                descripcion TEXT
            )
        """,
        'calificaciones': """
            CREATE TABLE IF NOT EXISTS calificaciones (
                id INT AUTO_INCREMENT PRIMARY KEY,
                estudiante_id INT,
                materia_id INT,
                lapso VARCHAR(10),
                nota DECIMAL(5,2),
                observacion TEXT,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (estudiante_id) REFERENCES usuarios(id) ON DELETE CASCADE,
                FOREIGN KEY (materia_id) REFERENCES materias(id) ON DELETE CASCADE
            )
        """
    }
    for nombre, sql in tablas.items():
        ejecutar_consulta(sql, commit=True)
        logger.info(f"✅ Tabla '{nombre}' verificada/creada.")

def inicializar_usuarios():
    usuarios = [
        ('admin', 'Admin1234*', 'admin', 'Administrador'),
        ('docente', 'Docente1234*', 'profesor', 'Profesor Juan'),
        ('estudiante', 'Estudiante1234*', 'estudiante', 'Estudiante Carlos'),
        ('soporte', 'Soporte1234*', 'soporte', 'Soporte Técnico'),
    ]
    for usuario, password, rol, nombre in usuarios:
        correo = f"{usuario}@synapse.edu"
        existe = ejecutar_consulta(
            "SELECT id FROM usuarios WHERE correo = %s",
            (correo,),
            fetch_one=True
        )
        if not existe:
            pw = generate_password_hash(password)
            ejecutar_consulta(
                "INSERT INTO usuarios (nombre, correo, password, rol) VALUES (%s, %s, %s, %s)",
                (nombre, correo, pw, rol),
                commit=True
            )
            logger.info(f"✅ {rol.capitalize()} creado: {usuario} / {password}")
        else:
            logger.info(f"ℹ️ Usuario {usuario} ya existe, omitiendo.")

# ------------------------------------------------------------
# FÁBRICA DE APLICACIONES
# ------------------------------------------------------------

def create_app(config_class=Config):
    app = Flask(__name__, template_folder='Frontend/HTMLS', static_folder='static')
    app.config.from_object(config_class)

    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(
        minutes=app.config.get('PERMANENT_SESSION_LIFETIME', 30)
    )
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['SESSION_COOKIE_SECURE'] = app.config.get('SESSION_COOKIE_SECURE', False)
    app.config['SESSION_REFRESH_EACH_REQUEST'] = True

    mail = Mail(app)
    app.extensions['mail'] = mail

    app.register_blueprint(public_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(docente_bp)
    app.register_blueprint(estudiante_bp)
    app.register_blueprint(soporte_bp)
    app.register_blueprint(ia_bp)

    @app.route('/index')
    def redirect_index():
        return redirect(url_for('public.index'))
    
    @app.context_processor
    def utility_processor():
        def url_for_old(endpoint, **kwargs):
            mapping = {
                'index': 'public.index',
                'login': 'auth.login',
                'logout': 'auth.logout',
                'administracion': 'admin.administracion',
                'profesores': 'docente.profesores',
                'estudiantes': 'estudiante.estudiantes',
                'soporte': 'soporte.soporte',
                'ia': 'ia.ia',
                'auditoria': 'admin.auditoria',
                'lapsos': 'estudiante.lapsos',
                'actividades': 'estudiante.actividades',
            }
            real_endpoint = mapping.get(endpoint, endpoint)
            return url_for(real_endpoint, **kwargs)
        return dict(url_for_old=url_for_old)

    with app.app_context():
        inicializar_base_datos()
        inicializar_usuarios()

    @app.errorhandler(HTTPException)
    def handle_http_exception(e):
        logger.error(f"HTTP {e.code}: {e.description}")
        return render_template('error.html', error=f"{e.code} - {e.name}"), e.code

    @app.errorhandler(404)
    def error_404(e):
        return render_template('error.html', error='404 - Página no encontrada'), 404

    @app.errorhandler(500)
    def error_500(e):
        return render_template('error.html', error='500 - Error interno del servidor'), 500

    @app.before_request
    def log_request_info():
        logger.info(f"📥 {request.method} {request.path} - IP: {request.remote_addr}")

    return app

# ------------------------------------------------------------
# INICIO DEL SERVIDOR
# ------------------------------------------------------------

# <--- ESTA LÍNEA ES LA QUE LE FALTA A GUNICORN
app = create_app()

if __name__ == '__main__':
    logger.info("""
    =========================================
        🚀 SYNAPSE VIRTUAL IA 2.2 INICIANDO
    =========================================
    """)
     
    from config import config
    conn = obtener_conexion_directa(config)
    if conn:
        logger.info("✅ MySQL conectado correctamente.")
        conn.close()
    else:
        logger.warning("⚠️ No se pudo conectar a MySQL. Revisa las credenciales.")

    app.run(host='0.0.0.0', port=5000, debug=True)
