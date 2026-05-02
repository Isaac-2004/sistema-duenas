from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.auth import login_required
from app.db import query
import config

facturas_bp = Blueprint('facturas', __name__, url_prefix='/facturas')


@facturas_bp.before_request
@login_required
def require_login():
    pass


@facturas_bp.route('/')
def lista():
    estado = request.args.get('estado', '')
    sql = ("SELECT f.id_factura, f.numero_factura, f.fecha_emision, f.total, f.estado, "
           "v.numero_venta, v.tipo_venta, "
           "CONCAT(c.nombres,' ',IFNULL(c.apellidos,'')) AS cliente "
           "FROM facturas f "
           "JOIN ventas v ON f.id_venta=v.id_venta "
           "JOIN clientes c ON v.id_cliente=c.id_cliente WHERE 1=1")
    params = []
    if estado:
        sql += " AND f.estado=%s"
        params.append(estado)
    sql += " ORDER BY f.fecha_emision DESC"
    facturas = query(sql, params)
    return render_template('facturas/lista.html', facturas=facturas, estado_sel=estado)


@facturas_bp.route('/<int:id>')
def detalle(id):
    factura = query(
        "SELECT f.*, v.numero_venta, v.tipo_venta, v.notas AS venta_notas "
        "FROM facturas f JOIN ventas v ON f.id_venta=v.id_venta WHERE f.id_factura=%s",
        (id,), fetchone=True
    )
    if not factura:
        flash('Factura no encontrada.', 'danger')
        return redirect(url_for('facturas.lista'))

    cliente = query(
        "SELECT c.* FROM clientes c "
        "JOIN ventas v ON c.id_cliente=v.id_cliente WHERE v.id_venta=%s",
        (factura['id_venta'],), fetchone=True
    )
    lineas = query(
        "SELECT vd.*, p.nombre AS producto, p.codigo "
        "FROM ventas_detalle vd JOIN productos p ON vd.id_producto=p.id_producto "
        "WHERE vd.id_venta=%s", (factura['id_venta'],)
    )
    cxc = query(
        "SELECT * FROM cuentas_por_cobrar WHERE id_venta=%s",
        (factura['id_venta'],), fetchone=True
    )
    empresa = {
        'nombre':    config.NOMBRE_EMPRESA,
        'ruc':       config.RUC_EMPRESA,
        'telefono':  config.TELEFONO_EMPRESA,
        'direccion': config.DIRECCION_EMPRESA,
    }
    return render_template('facturas/detalle.html',
                           factura=factura, cliente=cliente, lineas=lineas,
                           cxc=cxc, empresa=empresa)
