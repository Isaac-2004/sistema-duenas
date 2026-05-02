from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.auth import login_required, requiere_permiso, log_auditoria
from app.db import query, execute, get_db

cobros_bp = Blueprint('cobros', __name__, url_prefix='/cobros')


@cobros_bp.before_request
@login_required
def require_login():
    pass


@cobros_bp.route('/')
def lista():
    cuentas = query(
        "SELECT cxc.id_cuenta, cxc.monto_total, cxc.monto_pagado, cxc.saldo_pendiente, "
        "cxc.fecha_vencimiento, cxc.estado, "
        "CONCAT(c.nombres,' ',IFNULL(c.apellidos,'')) AS cliente, c.celular, "
        "v.numero_venta "
        "FROM cuentas_por_cobrar cxc "
        "JOIN clientes c ON cxc.id_cliente=c.id_cliente "
        "JOIN ventas v ON cxc.id_venta=v.id_venta "
        "WHERE cxc.estado IN ('PENDIENTE','PAGADA_PARCIAL','VENCIDA') "
        "ORDER BY cxc.fecha_vencimiento ASC, cxc.saldo_pendiente DESC"
    )
    total_pendiente = sum(float(c['saldo_pendiente']) for c in cuentas)
    return render_template('cobros/lista_cxc.html', cuentas=cuentas,
                           total_pendiente=total_pendiente)


@cobros_bp.route('/cliente/<int:id_cliente>')
def lista_cliente(id_cliente):
    cuentas = query(
        "SELECT cxc.*, v.numero_venta "
        "FROM cuentas_por_cobrar cxc "
        "JOIN ventas v ON cxc.id_venta=v.id_venta "
        "WHERE cxc.id_cliente=%s AND cxc.estado != 'PAGADA' "
        "ORDER BY cxc.fecha_vencimiento",
        (id_cliente,)
    )
    if cuentas:
        return redirect(url_for('cobros.detalle_cuenta', id_cuenta=cuentas[0]['id_cuenta']))
    flash('No hay cuentas pendientes para este cliente.', 'success')
    return redirect(url_for('clientes.detalle', id=id_cliente))


@cobros_bp.route('/<int:id_cuenta>')
def detalle_cuenta(id_cuenta):
    cuenta = query(
        "SELECT cxc.*, CONCAT(c.nombres,' ',IFNULL(c.apellidos,'')) AS cliente, "
        "c.celular, c.id_cliente, v.numero_venta "
        "FROM cuentas_por_cobrar cxc "
        "JOIN clientes c ON cxc.id_cliente=c.id_cliente "
        "JOIN ventas v ON cxc.id_venta=v.id_venta "
        "WHERE cxc.id_cuenta=%s", (id_cuenta,), fetchone=True
    )
    if not cuenta:
        flash('Cuenta no encontrada.', 'danger')
        return redirect(url_for('cobros.lista'))

    abonos = query(
        "SELECT * FROM abonos WHERE id_cuenta=%s ORDER BY fecha_abono DESC",
        (id_cuenta,)
    )
    return render_template('cobros/detalle_cuenta.html', cuenta=cuenta, abonos=abonos)


@cobros_bp.route('/<int:id_cuenta>/abonar', methods=['GET', 'POST'])
@requiere_permiso('cxc.registrar_abono')
def abonar(id_cuenta):
    cuenta = query(
        "SELECT cxc.*, CONCAT(c.nombres,' ',IFNULL(c.apellidos,'')) AS cliente "
        "FROM cuentas_por_cobrar cxc JOIN clientes c ON cxc.id_cliente=c.id_cliente "
        "WHERE cxc.id_cuenta=%s", (id_cuenta,), fetchone=True
    )
    if not cuenta:
        flash('Cuenta no encontrada.', 'danger')
        return redirect(url_for('cobros.lista'))

    if cuenta['estado'] == 'PAGADA':
        flash('Esta cuenta ya está pagada completamente.', 'success')
        return redirect(url_for('cobros.detalle_cuenta', id_cuenta=id_cuenta))

    if request.method == 'POST':
        monto      = float(request.form.get('monto_abono', 0) or 0)
        forma      = request.form.get('forma_pago', 'EFECTIVO')
        referencia = request.form.get('referencia', '').strip() or None
        notas      = request.form.get('notas', '').strip() or None

        saldo = float(cuenta['saldo_pendiente'])
        if monto <= 0:
            flash('El monto del abono debe ser mayor a cero.', 'danger')
        elif monto > saldo:
            flash(f'El abono no puede superar el saldo pendiente (${saldo:.2f}).', 'danger')
        else:
            conn = get_db()
            conn.begin()
            try:
                execute(
                    "INSERT INTO abonos (id_cuenta,id_cliente,monto_abono,forma_pago,referencia,notas) "
                    "VALUES (%s,%s,%s,%s,%s,%s)",
                    (id_cuenta, cuenta['id_cliente'], monto, forma, referencia, notas)
                )
                # El trigger actualiza cuentas_por_cobrar automáticamente
                # Si queda saldo 0, actualizar la factura a PAGADA
                cuenta_actualizada = query(
                    "SELECT estado FROM cuentas_por_cobrar WHERE id_cuenta=%s",
                    (id_cuenta,), fetchone=True
                )
                if cuenta_actualizada and cuenta_actualizada['estado'] == 'PAGADA':
                    execute(
                        "UPDATE facturas SET estado='PAGADA' WHERE id_venta=%s",
                        (cuenta['id_venta'],)
                    )
                conn.commit()
                log_auditoria('REGISTRAR_ABONO', 'CXC',
                              f'Abono ${monto:.2f} en cuenta {id_cuenta} '
                              f'— cliente {cuenta["cliente"]}',
                              tabla='abonos', id_registro=id_cuenta)
                flash(f'Abono de ${monto:.2f} registrado correctamente. '
                      f'Saldo restante: ${max(0, saldo - monto):.2f}', 'success')
                return redirect(url_for('cobros.detalle_cuenta', id_cuenta=id_cuenta))
            except Exception as e:
                conn.rollback()
                flash(f'Error al registrar el abono: {e}', 'danger')

    return render_template('cobros/form_abono.html', cuenta=cuenta)
