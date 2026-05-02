from flask import Blueprint, render_template, request
from app.auth import login_required
from app.db import query

reportes_bp = Blueprint('reportes', __name__, url_prefix='/reportes')


@reportes_bp.before_request
@login_required
def require_login():
    pass


@reportes_bp.route('/deudas-clientes')
def deudas_clientes():
    datos = query(
        "SELECT * FROM v_deudas_clientes ORDER BY saldo_total_pendiente DESC"
    )
    total = sum(float(d['saldo_total_pendiente']) for d in datos)
    return render_template('reportes/deudas_clientes.html', datos=datos, total=total)


@reportes_bp.route('/bajo-stock')
def bajo_stock():
    datos = query("SELECT * FROM v_productos_bajo_stock ORDER BY unidades_faltantes DESC")
    return render_template('reportes/bajo_stock.html', datos=datos)


@reportes_bp.route('/historial-abonos')
def historial_abonos():
    fecha_desde  = request.args.get('fecha_desde', '')
    fecha_hasta  = request.args.get('fecha_hasta', '')
    cliente_id   = request.args.get('cliente_id', '')

    sql = "SELECT * FROM v_historial_abonos WHERE 1=1"
    params = []
    if fecha_desde:
        sql += " AND DATE(fecha_abono) >= %s"
        params.append(fecha_desde)
    if fecha_hasta:
        sql += " AND DATE(fecha_abono) <= %s"
        params.append(fecha_hasta)
    sql += " ORDER BY fecha_abono DESC"

    datos = query(sql, params)
    total = sum(float(d['monto_abono']) for d in datos)
    clientes = query("SELECT id_cliente, nombres, apellidos FROM clientes WHERE estado=1 ORDER BY nombres")
    return render_template('reportes/historial_abonos.html', datos=datos, total=total,
                           clientes=clientes, fecha_desde=fecha_desde, fecha_hasta=fecha_hasta)


@reportes_bp.route('/cierre-dia')
def cierre_dia():
    fecha = request.args.get('fecha', '')
    if not fecha:
        from datetime import datetime, timezone, timedelta
        ecuador_tz = timezone(timedelta(hours=-5))
        fecha = datetime.now(ecuador_tz).strftime('%Y-%m-%d')

    ventas_contado = query(
        "SELECT COALESCE(SUM(total),0) AS total, COUNT(*) AS cnt FROM ventas "
        "WHERE DATE(fecha_venta)=%s AND tipo_venta='CONTADO' AND estado='ACTIVA'",
        (fecha,), fetchone=True
    )
    ventas_credito = query(
        "SELECT COALESCE(SUM(total),0) AS total, COUNT(*) AS cnt FROM ventas "
        "WHERE DATE(fecha_venta)=%s AND tipo_venta='CREDITO' AND estado='ACTIVA'",
        (fecha,), fetchone=True
    )
    abonos_dia = query(
        "SELECT a.*, CONCAT(c.nombres,' ',IFNULL(c.apellidos,'')) AS cliente, "
        "v.numero_venta "
        "FROM abonos a "
        "JOIN cuentas_por_cobrar cxc ON a.id_cuenta=cxc.id_cuenta "
        "JOIN clientes c ON a.id_cliente=c.id_cliente "
        "JOIN ventas v ON cxc.id_venta=v.id_venta "
        "WHERE DATE(a.fecha_abono)=%s ORDER BY a.fecha_abono",
        (fecha,)
    )
    total_abonos = sum(float(a['monto_abono']) for a in abonos_dia)
    total_contado = float(ventas_contado['total'])
    total_credito = float(ventas_credito['total'])

    return render_template('reportes/cierre_dia.html',
                           fecha=fecha,
                           ventas_contado=ventas_contado,
                           ventas_credito=ventas_credito,
                           abonos_dia=abonos_dia,
                           total_abonos=total_abonos,
                           total_contado=total_contado,
                           total_credito=total_credito)
