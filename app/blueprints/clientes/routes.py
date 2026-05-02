from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.auth import login_required
from app.db import query, execute

clientes_bp = Blueprint('clientes', __name__, url_prefix='/clientes')


@clientes_bp.before_request
@login_required
def require_login():
    pass


@clientes_bp.route('/')
def lista():
    busqueda = request.args.get('q', '').strip()
    estado   = request.args.get('estado', '1')
    params   = []
    sql      = ("SELECT id_cliente, tipo_cliente, nombres, apellidos, razon_social, "
                "cedula_ruc, celular, limite_credito, estado FROM clientes WHERE 1=1")
    if busqueda:
        sql += " AND (nombres LIKE %s OR apellidos LIKE %s OR cedula_ruc LIKE %s OR celular LIKE %s)"
        like = f'%{busqueda}%'
        params += [like, like, like, like]
    if estado in ('0', '1'):
        sql += " AND estado=%s"
        params.append(int(estado))
    sql += " ORDER BY nombres"
    clientes = query(sql, params)
    return render_template('clientes/lista.html', clientes=clientes, q=busqueda, estado=estado)


@clientes_bp.route('/nuevo', methods=['GET', 'POST'])
def nuevo():
    if request.method == 'POST':
        _guardar(None)
        return redirect(url_for('clientes.lista'))
    return render_template('clientes/form.html', cliente=None, titulo='Nuevo Cliente')


@clientes_bp.route('/<int:id>/editar', methods=['GET', 'POST'])
def editar(id):
    cliente = query("SELECT * FROM clientes WHERE id_cliente=%s", (id,), fetchone=True)
    if not cliente:
        flash('Cliente no encontrado.', 'danger')
        return redirect(url_for('clientes.lista'))
    if request.method == 'POST':
        _guardar(id)
        return redirect(url_for('clientes.detalle', id=id))
    return render_template('clientes/form.html', cliente=cliente, titulo='Editar Cliente')


@clientes_bp.route('/<int:id>/desactivar', methods=['POST'])
def desactivar(id):
    execute("UPDATE clientes SET estado=0 WHERE id_cliente=%s", (id,))
    flash('Cliente desactivado.', 'success')
    return redirect(url_for('clientes.lista'))


@clientes_bp.route('/<int:id>/detalle')
def detalle(id):
    cliente = query("SELECT * FROM clientes WHERE id_cliente=%s", (id,), fetchone=True)
    if not cliente:
        flash('Cliente no encontrado.', 'danger')
        return redirect(url_for('clientes.lista'))

    deudas = query(
        "SELECT cxc.id_cuenta, cxc.monto_total, cxc.monto_pagado, cxc.saldo_pendiente, "
        "cxc.fecha_vencimiento, cxc.estado, v.numero_venta "
        "FROM cuentas_por_cobrar cxc JOIN ventas v ON cxc.id_venta=v.id_venta "
        "WHERE cxc.id_cliente=%s ORDER BY cxc.fecha_vencimiento DESC",
        (id,)
    )
    abonos = query(
        "SELECT a.fecha_abono, a.monto_abono, a.forma_pago, v.numero_venta "
        "FROM abonos a "
        "JOIN cuentas_por_cobrar cxc ON a.id_cuenta=cxc.id_cuenta "
        "JOIN ventas v ON cxc.id_venta=v.id_venta "
        "WHERE a.id_cliente=%s ORDER BY a.fecha_abono DESC LIMIT 20",
        (id,)
    )
    ultimos_pedidos = query(
        "SELECT id_pedido, fecha_pedido, estado FROM pedidos "
        "WHERE id_cliente=%s ORDER BY fecha_pedido DESC LIMIT 10",
        (id,)
    )
    return render_template('clientes/detalle.html', cliente=cliente,
                           deudas=deudas, abonos=abonos, ultimos_pedidos=ultimos_pedidos)


def _guardar(id):
    f = request.form
    datos = (
        f.get('tipo_cliente', 'NATURAL'),
        f.get('nombres', '').strip(),
        f.get('apellidos', '').strip() or None,
        f.get('razon_social', '').strip() or None,
        f.get('cedula_ruc', '').strip() or None,
        f.get('telefono', '').strip() or None,
        f.get('celular', '').strip() or None,
        f.get('email', '').strip() or None,
        f.get('direccion', '').strip() or None,
        f.get('ciudad', '').strip() or None,
        float(f.get('limite_credito', 0) or 0),
        int(f.get('estado', 1)),
        f.get('notas', '').strip() or None,
    )
    if id is None:
        execute(
            "INSERT INTO clientes (tipo_cliente,nombres,apellidos,razon_social,cedula_ruc,"
            "telefono,celular,email,direccion,ciudad,limite_credito,estado,notas) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            datos
        )
        flash('Cliente creado correctamente.', 'success')
    else:
        execute(
            "UPDATE clientes SET tipo_cliente=%s,nombres=%s,apellidos=%s,razon_social=%s,"
            "cedula_ruc=%s,telefono=%s,celular=%s,email=%s,direccion=%s,ciudad=%s,"
            "limite_credito=%s,estado=%s,notas=%s WHERE id_cliente=%s",
            datos + (id,)
        )
        flash('Cliente actualizado.', 'success')
