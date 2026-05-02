"""
Ejecutar UNA VEZ después de aplicar seguridad_schema.sql en la BD.
Crea el usuario administrador inicial.

Uso:
    venv\Scripts\python crear_admin_db.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import pymysql
import pymysql.cursors
import bcrypt
import getpass
import config


def get_conn():
    return pymysql.connect(
        host=config.DB_HOST, port=config.DB_PORT,
        user=config.DB_USER, password=config.DB_PASSWORD,
        database=config.DB_NAME, charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )


def main():
    print("=" * 50)
    print("  Crear usuario administrador en la base de datos")
    print("=" * 50)

    conn = get_conn()

    with conn.cursor() as cur:
        # Verificar que las tablas de seguridad existen
        cur.execute("SHOW TABLES LIKE 'usuarios'")
        if not cur.fetchone():
            print("\n[ERROR] La tabla 'usuarios' no existe.")
            print("  Aplica primero seguridad_schema.sql en tu base de datos.")
            sys.exit(1)

        # Verificar si ya existe un admin
        cur.execute("SELECT COUNT(*) AS n FROM usuarios")
        total = cur.fetchone()['n']
        if total > 0:
            print(f"\nYa existen {total} usuario(s) en la base de datos.")
            resp = input("¿Crear otro usuario admin de todas formas? (s/N): ").strip().lower()
            if resp != 's':
                print("Cancelado.")
                sys.exit(0)

        # Obtener rol ADMINISTRADOR
        cur.execute("SELECT id_rol FROM roles WHERE nombre='ADMINISTRADOR' LIMIT 1")
        rol = cur.fetchone()
        if not rol:
            print("\n[ERROR] Rol 'ADMINISTRADOR' no encontrado.")
            print("  Verifica que seguridad_schema.sql fue aplicado correctamente.")
            sys.exit(1)
        id_rol = rol['id_rol']

    print()
    username      = input("Nombre de usuario [admin]: ").strip() or 'admin'
    nombre        = input("Nombre completo [Administrador]: ").strip() or 'Administrador'
    email         = input("Email: ").strip()

    while True:
        password = getpass.getpass("Contraseña (mín 8 caracteres): ")
        if len(password) < 8:
            print("  La contraseña debe tener al menos 8 caracteres.")
            continue
        confirm = getpass.getpass("Confirmar contraseña: ")
        if password != confirm:
            print("  Las contraseñas no coinciden.")
            continue
        break

    pw_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO usuarios (id_rol, username, email, password_hash, nombre_completo, estado) "
            "VALUES (%s, %s, %s, %s, %s, 'ACTIVO')",
            (id_rol, username, email or f'{username}@distribuidora.local', pw_hash, nombre)
        )

    print(f"\n✓ Usuario '{username}' creado exitosamente con rol ADMINISTRADOR.")
    print("  Ya puedes iniciar sesión en el sistema.")


if __name__ == '__main__':
    main()
