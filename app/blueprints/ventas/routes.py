from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.auth import login_required, requiere_permiso, log_auditoria
from app.db import query, execute, get_db
import config

ventas_bp = Blueprint('ventas', __name__, url_prefix='/ventas')


@ventas_bp.before_request
@login_required
def require_login():
    pass


@ventas_bp.route('/')
def lista():
    tipo = request.args.get('tipo', '')
    sql = ("SELECT v.id_venta, v.numero_venta, v.fecha_venta, v.tipo_venta, v.total, v.estado, "
           "CONCAT(c.nombres,' ',IFNULL(c.apellidos,'')) AS cliente "
           "FROM ventas v JOIN clientes c ON v.id_cliente=c.id_cliente WHERE 1=1")
    params = []
    if tipo:
        sql += " AND v.tipo_venta=%s"
        params.append(tipo)
    sql += " ORDER BY v.fecha_venta DESC"
    ventas = query(sql, params)
    return render_template('ventas/lista.html', ventas=ventas, tipo_sel=tipo)


@ventas_bp.route('/nueva', methods=['GET', 'POST'])
@requiere_permiso('ventas.crear')
def nueva():
    clientes  = query("SELECT id_cliente, nombres, apellidos FROM clientes WHERE estado=1 ORDER BY nombres")
    pedido_id = request.args.get('pedido_id', type=int)
    pedido    = None
    pedido_items = []

    if pedido_id:
        pedido = query(
            "SELECT p.*, CONCAT(c.nombres,' ',IFNULL(c.apellidos,'')) AS cliente_nombre, c.id_cliente "
            "FROM pedidos p JOIN clientes c ON p.id_cliente=c.id_cliente WHERE p.id_pedido=%s",
            (pedido_id,), fetchone=True
        )
        if pedido:
            pedido_items = query(
                "SELECT pd.id_producto, pd.cantidad, pd.precio_unitario, pr.nombre, "
                "pr.aplica_iva, pr.porcentaje_iva "
                "FROM pedidos_detalle pd JOIN productos pr ON pd.id_producto=pr.id_producto "
                "WHERE pd.id_pedido=%s", (pedido_id,)
            )

    if request.method == 'POST':
        id_venta = _crear_venta()
        if id_venta:
            flash('Venta registrada y factura generada.', 'success')
            factura = query("SELECT id_factura FROM facturas WHERE id_venta=%s", (id_venta,), fetchone=True)
            if factura:
                return redirect(url_for('facturas.detalle', id=factura['id_factura']))
            return redirect(url_for('ventas.lista'))

    return render_template('ventas/form.html', clientes=clientes,
                           pedido=pedido, pedido_items=pedido_items,
                           pedido_id=pedido_id)


@ventas_bp.route('/<int:id>/detalle')
def detalle(id):
    venta = query(
        "SELECT v.*, CONCAT(c.nombres,' ',IFNULL(c.apellidos,'')) AS cliente, c.celular "
        "FROM ventas v JOIN clientes c ON v.id_cliente=c.id_cliente WHERE v.id_venta=%s",
        (id,), fetchone=True
    )
    if not venta:
        flash('Venta no encontrada.', 'danger')
        return redirect(url_for('ventas.lista'))
    detalle = query(
        "SELECT vd.*, p.nombre AS producto "
        "FROM ventas_detalle vd JOIN productos p ON vd.id_producto=p.id_producto "
        "WHERE vd.id_venta=%s", (id,)
    )
    factura = query("SELECT * FROM facturas WHERE id_venta=%s", (id,), fetchone=True)
    return render_template('ventas/detalle.html', venta=venta, detalle=detalle, factura=factura)


@ventas_bp.route('/<int:id>/anular', methods=['POST'])
@requiere_permiso('ventas.anular')
def anular(id):
    venta = query("SELECT * FROM ventas WHERE id_venta=%s", (id,), fetchone=True)
    if not venta or venta['estado'] == 'ANULADA':
        flash('Venta no válida para anular.', 'danger')
        return redirect(url_for('ventas.lista'))

    conn = get_db()
    conn.begin()
    try:
        # Revertir stock por cada línea
        lineas = query("SELECT * FROM ventas_detalle WHERE id_venta=%s", (id,))
        for l in lineas:
            prod = query("SELECT stock_actual FROM productos WHERE id_producto=%s",
                         (l['id_producto'],), fetchone=True)
            stock_ant = float(prod['stock_actual'])
            stock_nuevo = stock_ant + float(l['cantidad'])
            execute("UPDATE productos SET stock_actual=%s WHERE id_producto=%s",
                    (stock_nuevo, l['id_producto']))
            execute(
                "INSERT INTO movimientos_inventario (id_producto,tipo_movimiento,origen,"
                "id_referencia,cantidad,stock_anterior,stock_posterior,notas) "
                "VALUES (%s,'AJUSTE_POSITIVO','DEVOLUCION',%s,%s,%s,%s,'Anulación de venta')",
                (l['id_producto'], id, l['cantidad'], stock_ant, stock_nuevo)
            )
        execute("UPDATE ventas SET estado='ANULADA' WHERE id_venta=%s", (id,))
        execute("UPDATE facturas SET estado='ANULADA' WHERE id_venta=%s", (id,))
        conn.commit()
        log_auditoria('ANULAR_VENTA', 'VENTAS',
                      f'Venta id={id} anulada y stock revertido',
                      tabla='ventas', id_registro=id)
        flash('Venta anulada y stock revertido.', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Error al anular la venta: {e}', 'danger')
    return redirect(url_for('ventas.detalle', id=id))


def _crear_venta():
    f = request.form
    id_cliente     = int(f.get('id_cliente'))
    tipo_venta     = f.get('tipo_venta', 'CONTADO')
    descuento      = float(f.get('descuento', 0) or 0)
    fecha_venc     = f.get('fecha_vencimiento') or None
    notas          = f.get('notas', '').strip() or None
    pedido_id      = f.get('pedido_id', type=int)

    items = _parse_items(f)
    if not items:
        flash('Debe agregar al menos un producto.', 'danger')
        return None

    # Validar stock antes de insertar
    for item in items:
        prod = query("SELECT stock_actual, nombre FROM productos WHERE id_producto=%s",
                     (item['id_producto'],), fetchone=True)
        if not prod:
            flash(f'Producto con id {item["id_producto"]} no existe.', 'danger')
            return None
        if float(prod['stock_actual']) < float(item['cantidad']):
            flash(f'Stock insuficiente para "{prod["nombre"]}". '
                  f'Disponible: {prod["stock_actual"]}.', 'danger')
            return None

    # Calcular totales
    subtotal_sin_iva = 0.0
    total_iva        = 0.0
    for item in items:
        sub = float(item['cantidad']) * float(item['precio_unitario'])
        subtotal_sin_iva += sub
        if item.get('aplica_iva'):
            total_iva += sub * config.IVA_RATE
    total = subtotal_sin_iva - descuento + total_iva

    # Número correlativo
    ultimo = query("SELECT numero_venta FROM ventas ORDER BY id_venta DESC LIMIT 1", fetchone=True)
    if ultimo:
        try:
            num = int(ultimo['numero_venta'].split('-')[-1]) + 1
        except Exception:
            num = 1
    else:
        num = 1
    numero_venta = f'VTA-{num:06d}'

    conn = get_db()
    conn.begin()
    try:
        id_venta = execute(
            "INSERT INTO ventas (id_cliente,id_pedido,numero_venta,tipo_venta,"
            "subtotal,descuento,total_iva,total,notas) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (id_cliente, pedido_id, numero_venta, tipo_venta,
             subtotal_sin_iva, descuento, total_iva, total, notas)
        )

        for item in items:
            sub = float(item['cantidad']) * float(item['precio_unitario'])
            iva_linea = sub * config.IVA_RATE if item.get('aplica_iva') else 0
            execute(
                "INSERT INTO ventas_detalle (id_venta,id_producto,cantidad,precio_unitario,"
                "subtotal,aplica_iva,valor_iva) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                (id_venta, item['id_producto'], item['cantidad'],
                 item['precio_unitario'], sub, 1 if item.get('aplica_iva') else 0, iva_linea)
            )

        # Generar número de factura
        ultima_fac = query("SELECT numero_factura FROM facturas ORDER BY id_factura DESC LIMIT 1", fetchone=True)
        if ultima_fac:
            try:
                num_f = int(ultima_fac['numero_factura'].split('-')[-1]) + 1
            except Exception:
                num_f = config.FACTURA_INICIO + 1
        else:
            num_f = config.FACTURA_INICIO + 1
        numero_factura = f'FAC-{num_f:06d}'

        execute(
            "INSERT INTO facturas (id_venta,numero_factura,subtotal,descuento,total_iva,total,"
            "fecha_vencimiento) VALUES (%s,%s,%s,%s,%s,%s,%s)",
            (id_venta, numero_factura, subtotal_sin_iva, descuento, total_iva, total, fecha_venc)
        )

        if tipo_venta == 'CREDITO':
            execute(
                "INSERT INTO cuentas_por_cobrar (id_venta,id_cliente,monto_total,monto_pagado,"
                "saldo_pendiente,fecha_vencimiento,estado) VALUES (%s,%s,%s,0,%s,%s,'PENDIENTE')",
                (id_venta, id_cliente, total, total, fecha_venc)
            )

        if pedido_id:
            execute("UPDATE pedidos SET estado='ENTREGADO' WHERE id_pedido=%s", (pedido_id,))

        conn.commit()
        log_auditoria('CREAR_VENTA', 'VENTAS',
                      f'Venta {numero_venta} creada — total ${total:.2f}',
                      tabla='ventas', id_registro=id_venta)
        return id_venta
    except Exception as e:
        conn.rollback()
        flash(f'Error al crear la venta: {e}', 'danger')
        return None


def _parse_items(form):
    items = []
    i = 0
    while True:
        id_prod = form.get(f'productos[{i}][id_producto]')
        if id_prod is None:
            break
        cantidad = form.get(f'productos[{i}][cantidad]', '0')
        precio   = form.get(f'productos[{i}][precio_unitario]', '0')
        # aplica_iva se consulta desde la BD para evitar manipulación
        if id_prod and float(cantidad) > 0:
            prod = query("SELECT aplica_iva FROM productos WHERE id_producto=%s",
                         (int(id_prod),), fetchone=True)
            items.append({
                'id_producto':     int(id_prod),
                'cantidad':        float(cantidad),
                'precio_unitario': float(precio),
                'aplica_iva':      bool(prod['aplica_iva']) if prod else False,
            })
        i += 1
    return items
