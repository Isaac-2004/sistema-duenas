from datetime import datetime
from flask import Flask
import config


def create_app():
    app = Flask(__name__, template_folder='../templates', static_folder='../static')

    app.secret_key = config.SECRET_KEY
    app.config.update(
        DB_HOST=config.DB_HOST,
        DB_PORT=config.DB_PORT,
        DB_USER=config.DB_USER,
        DB_PASSWORD=config.DB_PASSWORD,
        DB_NAME=config.DB_NAME,
        IVA_RATE=config.IVA_RATE,
        NOMBRE_EMPRESA=config.NOMBRE_EMPRESA,
    )

    from app.db import close_db
    app.teardown_appcontext(close_db)

    @app.context_processor
    def inject_globals():
        from flask import session
        from app.auth import tiene_permiso, current_user
        return {
            'nombre_empresa': config.NOMBRE_EMPRESA,
            'iva_rate': config.IVA_RATE,
            'now': datetime.now,
            'tiene_permiso': tiene_permiso,
            'current_user': current_user(),
        }

    from app.auth import auth_bp
    app.register_blueprint(auth_bp)

    from app.blueprints.dashboard.routes import dashboard_bp
    app.register_blueprint(dashboard_bp)

    from app.blueprints.clientes.routes import clientes_bp
    app.register_blueprint(clientes_bp)

    from app.blueprints.proveedores.routes import proveedores_bp
    app.register_blueprint(proveedores_bp)

    from app.blueprints.productos.routes import productos_bp
    app.register_blueprint(productos_bp)

    from app.blueprints.catalogos.routes import catalogos_bp
    app.register_blueprint(catalogos_bp)

    from app.blueprints.pedidos.routes import pedidos_bp
    app.register_blueprint(pedidos_bp)

    from app.blueprints.compras.routes import compras_bp
    app.register_blueprint(compras_bp)

    from app.blueprints.ventas.routes import ventas_bp
    app.register_blueprint(ventas_bp)

    from app.blueprints.facturas.routes import facturas_bp
    app.register_blueprint(facturas_bp)

    from app.blueprints.cobros.routes import cobros_bp
    app.register_blueprint(cobros_bp)

    from app.blueprints.reportes.routes import reportes_bp
    app.register_blueprint(reportes_bp)

    from app.blueprints.seguridad.routes import seguridad_bp
    app.register_blueprint(seguridad_bp)

    @app.errorhandler(404)
    def not_found(_):
        from flask import render_template
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def server_error(_):
        from flask import render_template
        return render_template('500.html'), 500

    return app
