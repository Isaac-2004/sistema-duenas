from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.auth import login_required
from app.db import query, execute

proveedores_bp = Blueprint('proveedores', __name__, url_prefix='/proveedores')


@proveedores_bp.before_request
@login_required
def require_login():
    pass


@proveedores_bp.route('/')
def lista():
    busqueda = request.args.get('q', '').strip()
    params, sql = [], ("SELECT id_proveedor, razon_social, nombre_contacto, "
                       "celular, ciudad, estado FROM proveedores WHERE 1=1")
    if busqueda:
        sql += " AND (razon_social LIKE %s OR nombre_contacto LIKE %s)"
        like = f'%{busqueda}%'
        params += [like, like]
    sql += " ORDER BY razon_social"
    proveedores = query(sql, params)
    return render_template('proveedores/lista.html', proveedores=proveedores, q=busqueda)


@proveedores_bp.route('/nuevo', methods=['GET', 'POST'])
def nuevo():
    if request.method == 'POST':
        _guardar(None)
        return redirect(url_for('proveedores.lista'))
    return render_template('proveedores/form.html', proveedor=None, titulo='Nuevo Proveedor')


@proveedores_bp.route('/<int:id>/editar', methods=['GET', 'POST'])
def editar(id):
    prov = query("SELECT * FROM proveedores WHERE id_proveedor=%s", (id,), fetchone=True)
    if not prov:
        flash('Proveedor no encontrado.', 'danger')
        return redirect(url_for('proveedores.lista'))
    if request.method == 'POST':
        _guardar(id)
        return redirect(url_for('proveedores.lista'))
    return render_template('proveedores/form.html', proveedor=prov, titulo='Editar Proveedor')


@proveedores_bp.route('/<int:id>/desactivar', methods=['POST'])
def desactivar(id):
    execute("UPDATE proveedores SET estado=0 WHERE id_proveedor=%s", (id,))
    flash('Proveedor desactivado.', 'success')
    return redirect(url_for('proveedores.lista'))


def _guardar(id):
    f = request.form
    datos = (
        f.get('razon_social', '').strip(),
        f.get('ruc_cedula', '').strip() or None,
        f.get('nombre_contacto', '').strip() or None,
        f.get('telefono', '').strip() or None,
        f.get('celular', '').strip() or None,
        f.get('email', '').strip() or None,
        f.get('direccion', '').strip() or None,
        f.get('ciudad', '').strip() or None,
        int(f.get('estado', 1)),
        f.get('notas', '').strip() or None,
    )
    if id is None:
        execute(
            "INSERT INTO proveedores (razon_social,ruc_cedula,nombre_contacto,telefono,"
            "celular,email,direccion,ciudad,estado,notas) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            datos
        )
        flash('Proveedor creado.', 'success')
    else:
        execute(
            "UPDATE proveedores SET razon_social=%s,ruc_cedula=%s,nombre_contacto=%s,"
            "telefono=%s,celular=%s,email=%s,direccion=%s,ciudad=%s,estado=%s,notas=%s "
            "WHERE id_proveedor=%s",
            datos + (id,)
        )
        flash('Proveedor actualizado.', 'success')
