from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app.auth import login_required
from app.db import query, execute, get_db

pedidos_bp = Blueprint('pedidos', __name__, url_prefix='/pedidos')


@pedidos_bp.before_request
@login_required
def require_login():
    pass


@pedidos_bp.route('/')
def lista():
    estado = request.args.get('estado', '')
    sql = ("SELECT p.id_pedido, p.fecha_pedido, p.fecha_entrega, p.estado, p.canal_origen, "
           "CONCAT(c.nombres,' ',IFNULL(c.apellidos,'')) AS cliente, c.celular "
           "FROM pedidos p JOIN clientes c ON p.id_cliente=c.id_cliente WHERE 1=1")
    params = []
    if estado:
        sql += " AND p.estado=%s"
        params.append(estado)
    sql += " ORDER BY p.fecha_pedido DESC"
    pedidos = query(sql, params)
    return render_template('pedidos/lista.html', pedidos=pedidos, estado_sel=estado)


@pedidos_bp.route('/nuevo', methods=['GET', 'POST'])
def nuevo():
    clientes = query("SELECT id_cliente, nombres, apellidos FROM clientes WHERE estado=1 ORDER BY nombres")
    cliente_id = request.args.get('cliente_id', '')
    if request.method == 'POST':
        id_pedido = _guardar_pedido()
        if id_pedido:
            flash('Pedido registrado correctamente.', 'success')
            return redirect(url_for('pedidos.detalle', id=id_pedido))
    return render_template('pedidos/form.html', clientes=clientes, cliente_id=cliente_id)


@pedidos_bp.route('/<int:id>/detalle')
def detalle(id):
    pedido = query(
        "SELECT p.*, CONCAT(c.nombres,' ',IFNULL(c.apellidos,'')) AS cliente, "
        "c.celular, c.id_cliente "
        "FROM pedidos p JOIN clientes c ON p.id_cliente=c.id_cliente "
        "WHERE p.id_pedido=%s", (id,), fetchone=True
    )
    if not pedido:
        flash('Pedido no encontrado.', 'danger')
        return redirect(url_for('pedidos.lista'))
    detalle = query(
        "SELECT pd.*, pr.nombre AS producto, pr.codigo "
        "FROM pedidos_detalle pd JOIN productos pr ON pd.id_producto=pr.id_producto "
        "WHERE pd.id_pedido=%s", (id,)
    )
    return render_template('pedidos/detalle.html', pedido=pedido, detalle=detalle)


@pedidos_bp.route('/<int:id>/estado', methods=['POST'])
def cambiar_estado(id):
    nuevo_estado = request.form.get('estado')
    estados_validos = ('PENDIENTE', 'CONFIRMADO', 'EN_PROCESO', 'ENTREGADO', 'CANCELADO')
    if nuevo_estado in estados_validos:
        execute("UPDATE pedidos SET estado=%s WHERE id_pedido=%s", (nuevo_estado, id))
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'ok': True, 'estado': nuevo_estado})
        flash(f'Estado actualizado a {nuevo_estado}.', 'success')
    return redirect(url_for('pedidos.detalle', id=id))


@pedidos_bp.route('/<int:id>/convertir-venta')
def convertir_venta(id):
    return redirect(url_for('ventas.nueva', pedido_id=id))


def _guardar_pedido():
    f = request.form
    id_cliente    = int(f.get('id_cliente'))
    fecha_entrega = f.get('fecha_entrega') or None
    canal         = f.get('canal_origen', 'WHATSAPP')
    notas         = f.get('notas', '').strip() or None

    # Procesar líneas de productos
    items = _parse_items(f)
    if not items:
        flash('Debe agregar al menos un producto.', 'danger')
        return None

    conn = get_db()
    conn.begin()
    try:
        id_pedido = execute(
            "INSERT INTO pedidos (id_cliente,fecha_entrega,canal_origen,notas) VALUES (%s,%s,%s,%s)",
            (id_cliente, fecha_entrega, canal, notas)
        )
        for item in items:
            subtotal = float(item['cantidad']) * float(item['precio_unitario'])
            execute(
                "INSERT INTO pedidos_detalle (id_pedido,id_producto,cantidad,precio_unitario,subtotal) "
                "VALUES (%s,%s,%s,%s,%s)",
                (id_pedido, item['id_producto'], item['cantidad'], item['precio_unitario'], subtotal)
            )
        conn.commit()
        return id_pedido
    except Exception as e:
        conn.rollback()
        flash(f'Error al guardar el pedido: {e}', 'danger')
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
        if id_prod and float(cantidad) > 0:
            items.append({'id_producto': int(id_prod),
                          'cantidad': float(cantidad),
                          'precio_unitario': float(precio)})
        i += 1
    return items
