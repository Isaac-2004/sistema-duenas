import json
from functools import wraps
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
import bcrypt
from app.db import query, execute

auth_bp = Blueprint('auth', __name__)


# ── Decoradores ────────────────────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


def requiere_permiso(codigo):
    """Verifica que el usuario tenga el permiso indicado (o sea admin)."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('auth.login'))
            if not session.get('es_admin') and codigo not in session.get('permisos', []):
                flash('No tienes permiso para realizar esta acción.', 'danger')
                return redirect(url_for('dashboard.index'))
            return f(*args, **kwargs)
        return decorated
    return decorator


# ── Helpers ────────────────────────────────────────────────────────────────────

def tiene_permiso(codigo):
    """Verifica permisos desde templates o código Python."""
    if session.get('es_admin'):
        return True
    return codigo in session.get('permisos', [])


def current_user():
    if 'user_id' not in session:
        return None
    return {
        'id':       session['user_id'],
        'username': session.get('username'),
        'nombre':   session.get('nombre'),
        'es_admin': session.get('es_admin', False),
        'permisos': session.get('permisos', []),
    }


def log_auditoria(accion, modulo, descripcion, tabla=None, id_registro=None,
                  datos_ant=None, datos_nuevo=None, resultado='EXITO'):
    """Registra un evento en audit_logs. Nunca lanza excepción."""
    try:
        execute(
            "INSERT INTO audit_logs "
            "(id_usuario, accion, modulo, tabla_afectada, id_registro, "
            "descripcion, datos_anteriores, datos_nuevos, ip_address, user_agent, resultado) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (
                session.get('user_id'),
                accion, modulo, tabla, id_registro, descripcion,
                json.dumps(datos_ant, default=str) if datos_ant else None,
                json.dumps(datos_nuevo, default=str) if datos_nuevo else None,
                request.remote_addr,
                (request.user_agent.string or '')[:500] if request.user_agent else None,
                resultado,
            )
        )
    except Exception:
        pass


def _cargar_permisos(id_usuario, id_rol, es_admin):
    if es_admin:
        return []  # admin omite verificación de permisos
    try:
        rows = query(
            "SELECT p.codigo FROM roles_permisos rp "
            "JOIN permisos p ON rp.id_permiso = p.id_permiso "
            "WHERE rp.id_rol = %s", (id_rol,)
        )
        permisos = {r['codigo'] for r in rows}

        extras = query(
            "SELECT p.codigo, upe.tipo FROM usuarios_permisos_extra upe "
            "JOIN permisos p ON upe.id_permiso = p.id_permiso "
            "WHERE upe.id_usuario = %s", (id_usuario,)
        )
        for e in extras:
            if e['tipo'] == 'GRANT':
                permisos.add(e['codigo'])
            else:
                permisos.discard(e['codigo'])
        return list(permisos)
    except Exception:
        return []


def _registrar_intento(username, exitoso, motivo=None):
    try:
        ua = (request.user_agent.string or '')[:500] if request.user_agent else ''
        execute(
            "INSERT INTO login_intentos "
            "(username_input, ip_address, user_agent, exitoso, motivo_fallo) "
            "VALUES (%s,%s,%s,%s,%s)",
            (username, request.remote_addr, ua, 1 if exitoso else 0, motivo)
        )
    except Exception:
        pass


# ── Rutas ──────────────────────────────────────────────────────────────────────

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard.index'))

    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        usuario = query(
            "SELECT u.*, r.es_admin FROM usuarios u "
            "JOIN roles r ON u.id_rol = r.id_rol "
            "WHERE u.username = %s",
            (username,), fetchone=True
        )

        if not usuario:
            _registrar_intento(username, False, 'USUARIO_NO_EXISTE')
            error = 'Usuario o contraseña incorrectos.'
        else:
            estado = usuario['estado']

            # Desbloqueo automático si ya expiró el período
            if estado == 'BLOQUEADO' and usuario.get('bloqueado_hasta'):
                if datetime.now() > usuario['bloqueado_hasta']:
                    execute(
                        "UPDATE usuarios SET estado='ACTIVO', intentos_fallidos=0, "
                        "bloqueado_hasta=NULL WHERE id_usuario=%s",
                        (usuario['id_usuario'],)
                    )
                    estado = 'ACTIVO'

            if estado == 'BLOQUEADO':
                _registrar_intento(username, False, 'BLOQUEADO')
                hasta = usuario.get('bloqueado_hasta')
                msg = f'Cuenta bloqueada hasta {hasta.strftime("%H:%M")}.' if hasta else 'Cuenta bloqueada.'
                error = msg + ' Contacta al administrador.'
            elif estado != 'ACTIVO':
                error = 'Cuenta inactiva. Contacta al administrador.'
            else:
                # Verificar contraseña
                try:
                    pw_ok = bcrypt.checkpw(
                        password.encode('utf-8'),
                        usuario['password_hash'].encode('utf-8')
                    )
                except Exception:
                    pw_ok = False

                if not pw_ok:
                    _registrar_intento(username, False, 'CLAVE_INCORRECTA')
                    error = 'Usuario o contraseña incorrectos.'
                else:
                    _registrar_intento(username, True)
                    permisos = _cargar_permisos(
                        usuario['id_usuario'], usuario['id_rol'], bool(usuario['es_admin'])
                    )
                    session.permanent = True
                    session['user_id']  = usuario['id_usuario']
                    session['username'] = usuario['username']
                    session['nombre']   = usuario['nombre_completo']
                    session['es_admin'] = bool(usuario['es_admin'])
                    session['permisos'] = permisos

                    log_auditoria('LOGIN', 'SEGURIDAD', f'Inicio de sesión: {username}')
                    return redirect(url_for('dashboard.index'))

    return render_template('login.html', error=error)


@auth_bp.route('/logout')
def logout():
    if 'user_id' in session:
        log_auditoria('LOGOUT', 'SEGURIDAD', f'Cierre de sesión: {session.get("username")}')
    session.clear()
    return redirect(url_for('auth.login'))
