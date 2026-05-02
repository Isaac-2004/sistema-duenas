import os

# Base de datos
DB_HOST     = os.environ.get('DB_HOST',     'db50371.public.databaseasp.net')
DB_PORT     = int(os.environ.get('DB_PORT', 3306))
DB_USER     = os.environ.get('DB_USER',     'db50371')
DB_PASSWORD = os.environ.get('DB_PASSWORD', 'Ks2-7%kQ_gP9')
DB_NAME     = os.environ.get('DB_NAME',     'db50371')

# Flask
SECRET_KEY = os.environ.get('SECRET_KEY', 'cambiar-esta-clave-en-produccion-xyz987')

# Negocio
IVA_RATE          = 0.15
NOMBRE_EMPRESA    = 'Distribuidora Dueñas'
RUC_EMPRESA       = ''
TELEFONO_EMPRESA  = ''
DIRECCION_EMPRESA = ''

# Acceso al sistema (usuario único)
# Contraseña por defecto: admin123
# Para generar un hash seguro, ejecutar en el servidor cPanel:
#   python generar_clave.py
# y copiar el resultado en ADMIN_PASSWORD_HASH
ADMIN_USERNAME     = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD     = os.environ.get('ADMIN_PASSWORD', 'Distribuidora123')   # solo si no hay hash
ADMIN_PASSWORD_HASH = os.environ.get('ADMIN_PASSWORD_HASH', '')     # vacío = usa ADMIN_PASSWORD
