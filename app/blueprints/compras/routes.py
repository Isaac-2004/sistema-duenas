from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.auth import login_required, requiere_permiso, log_auditoria
from app.db import query, execute, get_db

compras_bp = Blueprint('compras', __name__, url_prefix='/compras')


@compras_bp.before_request
@login_required
def require_login():
    pass


@compras_bp.route('/')
def lista():
    compras = query(
        "SELECT c.id_compra, c.numero_factura, c.fecha_compra, c.total, c.estado, "
        "p.razon_social AS proveedor "
        "FROM compras c JOIN proveedores p ON c.id_proveedor=p.id_proveedor "
        "ORDER BY c.fecha_compra DESC"
    )
    return render_template('compras/lista.html', compras=compras)


@compras_bp.route('/nueva', methods=['GET', 'POST'])
@requiere_permiso('compras.crear')
def nueva():
    proveedores = query("SELECT id_proveedor, razon_social FROM proveedores WHERE estado=1 ORDER BY razon_social")
    if request.method == 'POST':
        id_compra = _guardar_compra()
        if id_compra:
            flash('Compra registrada. Inventario actualizado automáticamente.', 'success')
            return redirect(url_for('compras.detalle', id=id_compra))
    return render_template('compras/form.html', proveedores=proveedores)


@compras_bp.route('/<int:id>/detalle')
def detalle(id):
    compra = query(
        "SELECT c.*, p.razon_social AS proveedor "
        "FROM compras c JOIN proveedores p ON c.id_proveedor=p.id_proveedor "
        "WHERE c.id_compra=%s", (id,), fetchone=True
    )
    if not compra:
        flash('Compra no encontrada.', 'danger')
        return redirect(url_for('compras.lista'))
    detalle = query(
        "SELECT cd.*, pr.nombre AS producto, pr.codigo "
        "FROM compras_detalle cd JOIN productos pr ON cd.id_producto=pr.id_producto "
        "WHERE cd.id_compra=%s", (id,)
    )
    return render_template('compras/detalle.html', compra=compra, detalle=detalle)


def _guardar_compra():
    f = request.form
    id_proveedor   = int(f.get('id_proveedor'))
    fecha_compra   = f.get('fecha_compra')
    num_factura    = f.get('numero_factura', '').strip() or None
    notas          = f.get('notas', '').strip() or None

    items = _parse_items(f)
    if not items:
        flash('Debe agregar al menos un producto.', 'danger')
        return None

    subtotal  = sum(float(i['cantidad']) * float(i['precio_unitario']) for i in items)
    total_iva = 0.0  # compras generalmente sin IVA al distribuidor
    total     = subtotal + total_iva

    conn = get_db()
    conn.begin()
    try:
        id_compra = execute(
            "INSERT INTO compras (id_proveedor,numero_factura,fecha_compra,subtotal,total_iva,total,estado,notas) "
            "VALUES (%s,%s,%s,%s,%s,%s,'RECIBIDA',%s)",
            (id_proveedor, num_factura, fecha_compra, subtotal, total_iva, total, notas)
        )
        for item in items:
            sub_linea = float(item['cantidad']) * float(item['precio_unitario'])
            execute(
                "INSERT INTO compras_detalle (id_compra,id_producto,cantidad,precio_unitario,subtotal) "
                "VALUES (%s,%s,%s,%s,%s)",
                (id_compra, item['id_producto'], item['cantidad'], item['precio_unitario'], sub_linea)
            )
            # El trigger trg_after_insert_compras_detalle actualiza el stock automáticamente
        conn.commit()
        log_auditoria('CREAR_COMPRA', 'COMPRAS',
                      f'Compra id={id_compra} registrada — total ${total:.2f}',
                      tabla='compras', id_registro=id_compra)
        return id_compra
    except Exception as e:
        conn.rollback()
        flash(f'Error al registrar la compra: {e}', 'danger')
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
