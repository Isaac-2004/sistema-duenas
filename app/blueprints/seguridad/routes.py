import bcrypt
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.auth import login_required, requiere_permiso, log_auditoria
from app.db import query, execute

seguridad_bp = Blueprint('seguridad', __name__, url_prefix='/seguridad')


@seguridad_bp.before_request
@login_required
def require_login():
    pass


# ── Usuarios ───────────────────────────────────────────────────────────────────

@seguridad_bp.route('/usuarios')
@requiere_permiso('seguridad.ver_usuarios')
def usuarios_lista():
    usuarios = query(
        "SELECT u.id_usuario, u.username, u.nombre_completo, u.email, "
        "u.estado, u.ultimo_login, u.intentos_fallidos, r.nombre AS rol "
        "FROM usuarios u JOIN roles r ON u.id_rol = r.id_rol "
        "ORDER BY u.nombre_completo"
    )
    roles = query("SELECT id_rol, nombre FROM roles WHERE estado=1 ORDER BY nombre")
    return render_template('seguridad/usuarios_lista.html', usuarios=usuarios, roles=roles)


@seguridad_bp.route('/usuarios/nuevo', methods=['GET', 'POST'])
@requiere_permiso('seguridad.gestionar_usuarios')
def usuario_nuevo():
    roles = query("SELECT id_rol, nombre FROM roles WHERE estado=1 ORDER BY nombre")
    if request.method == 'POST':
        id_usuario = _guardar_usuario(None)
        if id_usuario:
            log_auditoria('CREAR_USUARIO', 'SEGURIDAD',
                          f'Nuevo usuario creado: {request.form.get("username")}',
                          tabla='usuarios', id_registro=id_usuario)
            flash('Usuario creado correctamente.', 'success')
            return redirect(url_for('seguridad.usuarios_lista'))
    return render_template('seguridad/usuario_form.html', roles=roles, usuario=None)


@seguridad_bp.route('/usuarios/<int:id>/editar', methods=['GET', 'POST'])
@requiere_permiso('seguridad.gestionar_usuarios')
def usuario_editar(id):
    usuario = query("SELECT * FROM usuarios WHERE id_usuario=%s", (id,), fetchone=True)
    if not usuario:
        flash('Usuario no encontrado.', 'danger')
        return redirect(url_for('seguridad.usuarios_lista'))

    roles = query("SELECT id_rol, nombre FROM roles WHERE estado=1 ORDER BY nombre")
    if request.method == 'POST':
        ok = _guardar_usuario(id)
        if ok:
            log_auditoria('EDITAR_USUARIO', 'SEGURIDAD',
                          f'Usuario editado: {usuario["username"]}',
                          tabla='usuarios', id_registro=id)
            flash('Usuario actualizado.', 'success')
            return redirect(url_for('seguridad.usuarios_lista'))
    return render_template('seguridad/usuario_form.html', roles=roles, usuario=usuario)


@seguridad_bp.route('/usuarios/<int:id>/estado', methods=['POST'])
@requiere_permiso('seguridad.gestionar_usuarios')
def usuario_estado(id):
    if id == session.get('user_id'):
        flash('No puedes desactivar tu propio usuario.', 'danger')
        return redirect(url_for('seguridad.usuarios_lista'))

    usuario = query("SELECT username, estado FROM usuarios WHERE id_usuario=%s", (id,), fetchone=True)
    if not usuario:
        flash('Usuario no encontrado.', 'danger')
        return redirect(url_for('seguridad.usuarios_lista'))

    nuevo = 'INACTIVO' if usuario['estado'] == 'ACTIVO' else 'ACTIVO'
    execute("UPDATE usuarios SET estado=%s WHERE id_usuario=%s", (nuevo, id))
    log_auditoria('CAMBIAR_ESTADO_USUARIO', 'SEGURIDAD',
                  f'Usuario {usuario["username"]} → {nuevo}',
                  tabla='usuarios', id_registro=id)
    flash(f'Usuario {usuario["username"]} marcado como {nuevo}.', 'success')
    return redirect(url_for('seguridad.usuarios_lista'))


@seguridad_bp.route('/usuarios/<int:id>/desbloquear', methods=['POST'])
@requiere_permiso('seguridad.gestionar_usuarios')
def usuario_desbloquear(id):
    usuario = query("SELECT username FROM usuarios WHERE id_usuario=%s", (id,), fetchone=True)
    if not usuario:
        flash('Usuario no encontrado.', 'danger')
        return redirect(url_for('seguridad.usuarios_lista'))

    execute(
        "UPDATE usuarios SET estado='ACTIVO', intentos_fallidos=0, bloqueado_hasta=NULL "
        "WHERE id_usuario=%s", (id,)
    )
    log_auditoria('DESBLOQUEAR_USUARIO', 'SEGURIDAD',
                  f'Usuario desbloqueado: {usuario["username"]}',
                  tabla='usuarios', id_registro=id)
    flash(f'Usuario {usuario["username"]} desbloqueado.', 'success')
    return redirect(url_for('seguridad.usuarios_lista'))


# ── Audit logs ─────────────────────────────────────────────────────────────────

@seguridad_bp.route('/logs')
@requiere_permiso('seguridad.ver_logs')
def logs():
    modulo  = request.args.get('modulo', '')
    accion  = request.args.get('accion', '')
    usuario = request.args.get('usuario', '')
    fecha   = request.args.get('fecha', '')

    sql = (
        "SELECT al.id_log, IFNULL(u.username,'SISTEMA') AS usuario, "
        "al.accion, al.modulo, al.tabla_afectada, al.id_registro, "
        "al.descripcion, al.resultado, al.ip_address, al.created_at "
        "FROM audit_logs al LEFT JOIN usuarios u ON al.id_usuario=u.id_usuario "
        "WHERE 1=1"
    )
    params = []
    if modulo:
        sql += " AND al.modulo=%s"; params.append(modulo)
    if accion:
        sql += " AND al.accion LIKE %s"; params.append(f'%{accion}%')
    if usuario:
        sql += " AND u.username LIKE %s"; params.append(f'%{usuario}%')
    if fecha:
        sql += " AND DATE(al.created_at)=%s"; params.append(fecha)
    sql += " ORDER BY al.created_at DESC LIMIT 500"

    logs_data = query(sql, params)
    modulos   = query("SELECT DISTINCT modulo FROM audit_logs ORDER BY modulo")
    return render_template('seguridad/logs.html',
                           logs=logs_data, modulos=modulos,
                           filtros={'modulo': modulo, 'accion': accion,
                                    'usuario': usuario, 'fecha': fecha})


# ── Helpers internos ───────────────────────────────────────────────────────────

def _guardar_usuario(id_existente):
    f = request.form
    id_rol         = f.get('id_rol', type=int)
    username       = f.get('username', '').strip()
    email          = f.get('email', '').strip()
    nombre_completo= f.get('nombre_completo', '').strip()
    password       = f.get('password', '')
    estado         = f.get('estado', 'ACTIVO')

    if not all([id_rol, username, nombre_completo]):
        flash('Completa todos los campos obligatorios.', 'danger')
        return None

    # Validar duplicado de username / email
    if id_existente:
        dup_u = query("SELECT id_usuario FROM usuarios WHERE username=%s AND id_usuario!=%s",
                      (username, id_existente), fetchone=True)
        dup_e = query("SELECT id_usuario FROM usuarios WHERE email=%s AND id_usuario!=%s",
                      (email, id_existente), fetchone=True) if email else None
    else:
        dup_u = query("SELECT id_usuario FROM usuarios WHERE username=%s", (username,), fetchone=True)
        dup_e = query("SELECT id_usuario FROM usuarios WHERE email=%s", (email,), fetchone=True) if email else None

    if dup_u:
        flash(f'El nombre de usuario "{username}" ya está en uso.', 'danger')
        return None
    if dup_e:
        flash(f'El email "{email}" ya está en uso.', 'danger')
        return None

    if id_existente:
        if password:
            if len(password) < 8:
                flash('La contraseña debe tener al menos 8 caracteres.', 'danger')
                return None
            pw_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            execute(
                "UPDATE usuarios SET id_rol=%s, username=%s, email=%s, nombre_completo=%s, "
                "password_hash=%s, estado=%s WHERE id_usuario=%s",
                (id_rol, username, email, nombre_completo, pw_hash, estado, id_existente)
            )
        else:
            execute(
                "UPDATE usuarios SET id_rol=%s, username=%s, email=%s, nombre_completo=%s, "
                "estado=%s WHERE id_usuario=%s",
                (id_rol, username, email, nombre_completo, estado, id_existente)
            )
        return id_existente
    else:
        if not password or len(password) < 8:
            flash('La contraseña es obligatoria y debe tener al menos 8 caracteres.', 'danger')
            return None
        pw_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        new_id = execute(
            "INSERT INTO usuarios (id_rol, username, email, password_hash, nombre_completo, estado) "
            "VALUES (%s,%s,%s,%s,%s,%s)",
            (id_rol, username, email or f'{username}@distribuidora.local', pw_hash, nombre_completo, estado)
        )
        return new_id
