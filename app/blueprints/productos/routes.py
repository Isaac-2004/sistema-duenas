from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app.auth import login_required
from app.db import query, execute, get_db

productos_bp = Blueprint('productos', __name__, url_prefix='/productos')


@productos_bp.before_request
@login_required
def require_login():
    pass


@productos_bp.route('/')
def lista():
    busqueda   = request.args.get('q', '').strip()
    categoria  = request.args.get('categoria', '')
    solo_stock = request.args.get('bajo_stock', '')
    params, sql = [], (
        "SELECT p.id_producto, p.codigo, p.nombre, c.nombre AS categoria, "
        "u.abreviatura AS unidad, p.precio_venta, p.stock_actual, p.stock_minimo, "
        "p.estado FROM productos p "
        "JOIN categorias c ON p.id_categoria=c.id_categoria "
        "JOIN unidades_medida u ON p.id_unidad=u.id_unidad WHERE p.estado=1"
    )
    if busqueda:
        sql += " AND (p.nombre LIKE %s OR p.codigo LIKE %s)"
        like = f'%{busqueda}%'
        params += [like, like]
    if categoria:
        sql += " AND p.id_categoria=%s"
        params.append(int(categoria))
    if solo_stock:
        sql += " AND p.stock_actual <= p.stock_minimo"
    sql += " ORDER BY p.nombre"
    productos = query(sql, params)
    categorias = query("SELECT id_categoria, nombre FROM categorias WHERE estado=1 ORDER BY nombre")
    return render_template('productos/lista.html', productos=productos,
                           categorias=categorias, q=busqueda,
                           cat_sel=categoria, bajo_stock=solo_stock)


@productos_bp.route('/nuevo', methods=['GET', 'POST'])
def nuevo():
    categorias = query("SELECT id_categoria, nombre FROM categorias WHERE estado=1 ORDER BY nombre")
    unidades   = query("SELECT id_unidad, nombre, abreviatura FROM unidades_medida ORDER BY nombre")
    if request.method == 'POST':
        _guardar(None)
        return redirect(url_for('productos.lista'))
    return render_template('productos/form.html', producto=None, titulo='Nuevo Producto',
                           categorias=categorias, unidades=unidades)


@productos_bp.route('/<int:id>/editar', methods=['GET', 'POST'])
def editar(id):
    producto   = query("SELECT * FROM productos WHERE id_producto=%s", (id,), fetchone=True)
    categorias = query("SELECT id_categoria, nombre FROM categorias WHERE estado=1 ORDER BY nombre")
    unidades   = query("SELECT id_unidad, nombre, abreviatura FROM unidades_medida ORDER BY nombre")
    if not producto:
        flash('Producto no encontrado.', 'danger')
        return redirect(url_for('productos.lista'))
    if request.method == 'POST':
        _guardar(id)
        return redirect(url_for('productos.lista'))
    return render_template('productos/form.html', producto=producto, titulo='Editar Producto',
                           categorias=categorias, unidades=unidades)


@productos_bp.route('/<int:id>/ajustar-stock', methods=['GET', 'POST'])
def ajustar_stock(id):
    producto = query("SELECT * FROM productos WHERE id_producto=%s", (id,), fetchone=True)
    if not producto:
        flash('Producto no encontrado.', 'danger')
        return redirect(url_for('productos.lista'))
    if request.method == 'POST':
        cantidad  = float(request.form.get('cantidad', 0))
        tipo      = request.form.get('tipo', 'AJUSTE_POSITIVO')
        notas     = request.form.get('notas', '').strip()
        stock_ant = float(producto['stock_actual'])
        if tipo == 'AJUSTE_POSITIVO':
            stock_nuevo = stock_ant + cantidad
        else:
            stock_nuevo = max(0, stock_ant - cantidad)
            tipo = 'AJUSTE_NEGATIVO'
        conn = get_db()
        conn.begin()
        try:
            execute("UPDATE productos SET stock_actual=%s WHERE id_producto=%s", (stock_nuevo, id))
            execute(
                "INSERT INTO movimientos_inventario (id_producto,tipo_movimiento,origen,"
                "cantidad,stock_anterior,stock_posterior,notas) VALUES (%s,%s,'AJUSTE_MANUAL',%s,%s,%s,%s)",
                (id, tipo, cantidad, stock_ant, stock_nuevo, notas or None)
            )
            conn.commit()
            flash(f'Stock ajustado a {stock_nuevo:.3f}.', 'success')
        except Exception:
            conn.rollback()
            flash('Error al ajustar stock.', 'danger')
        return redirect(url_for('productos.lista'))
    return render_template('productos/ajuste_stock.html', producto=producto)


@productos_bp.route('/api/buscar')
def api_buscar():
    q = request.args.get('q', '').strip()
    if len(q) < 2:
        return jsonify([])
    productos = query(
        "SELECT id_producto, codigo, nombre, precio_venta, stock_actual, "
        "aplica_iva, porcentaje_iva FROM productos "
        "WHERE estado=1 AND (nombre LIKE %s OR codigo LIKE %s) LIMIT 10",
        (f'%{q}%', f'%{q}%')
    )
    return jsonify([dict(p) for p in productos])


def _guardar(id):
    f = request.form
    datos = (
        int(f.get('id_categoria')),
        int(f.get('id_unidad')),
        f.get('codigo', '').strip(),
        f.get('nombre', '').strip(),
        f.get('descripcion', '').strip() or None,
        float(f.get('precio_compra', 0) or 0),
        float(f.get('precio_venta', 0) or 0),
        float(f.get('stock_minimo', 0) or 0),
        int(f.get('aplica_iva', 0)),
        float(f.get('porcentaje_iva', 15) or 15),
        int(f.get('estado', 1)),
    )
    if id is None:
        execute(
            "INSERT INTO productos (id_categoria,id_unidad,codigo,nombre,descripcion,"
            "precio_compra,precio_venta,stock_minimo,aplica_iva,porcentaje_iva,estado) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            datos
        )
        flash('Producto creado.', 'success')
    else:
        execute(
            "UPDATE productos SET id_categoria=%s,id_unidad=%s,codigo=%s,nombre=%s,"
            "descripcion=%s,precio_compra=%s,precio_venta=%s,stock_minimo=%s,"
            "aplica_iva=%s,porcentaje_iva=%s,estado=%s WHERE id_producto=%s",
            datos + (id,)
        )
        flash('Producto actualizado.', 'success')
