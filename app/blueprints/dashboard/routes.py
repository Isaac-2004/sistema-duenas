from flask import Blueprint, render_template
from app.auth import login_required
from app.db import query

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
@login_required
def index():
    ventas_hoy = query(
        "SELECT COALESCE(SUM(total),0) AS total FROM ventas "
        "WHERE DATE(fecha_venta)=CURDATE() AND estado='ACTIVA'",
        fetchone=True
    )['total']

    pedidos_pendientes = query(
        "SELECT COUNT(*) AS cnt FROM pedidos WHERE estado IN ('PENDIENTE','CONFIRMADO','EN_PROCESO')",
        fetchone=True
    )['cnt']

    bajo_stock = query(
        "SELECT COUNT(*) AS cnt FROM v_productos_bajo_stock",
        fetchone=True
    )['cnt']

    por_cobrar = query(
        "SELECT COALESCE(SUM(saldo_pendiente),0) AS total FROM cuentas_por_cobrar "
        "WHERE estado IN ('PENDIENTE','PAGADA_PARCIAL','VENCIDA')",
        fetchone=True
    )['total']

    vencidas = query(
        "SELECT COUNT(*) AS cnt FROM cuentas_por_cobrar "
        "WHERE estado IN ('PENDIENTE','PAGADA_PARCIAL') AND fecha_vencimiento < CURDATE()",
        fetchone=True
    )['cnt']

    ultimos_pedidos = query(
        "SELECT p.id_pedido, p.fecha_pedido, p.estado, "
        "CONCAT(c.nombres,' ',IFNULL(c.apellidos,'')) AS cliente "
        "FROM pedidos p JOIN clientes c ON p.id_cliente=c.id_cliente "
        "ORDER BY p.fecha_pedido DESC LIMIT 5"
    )

    return render_template('dashboard/index.html',
                           ventas_hoy=ventas_hoy,
                           pedidos_pendientes=pedidos_pendientes,
                           bajo_stock=bajo_stock,
                           por_cobrar=por_cobrar,
                           vencidas=vencidas,
                           ultimos_pedidos=ultimos_pedidos)
