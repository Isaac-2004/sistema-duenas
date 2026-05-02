"""
Ejecutar este script en el servidor para generar el hash de la contraseña:
    python generar_clave.py

Luego copiar el hash en config.py -> ADMIN_PASSWORD_HASH
"""
import getpass
import bcrypt

password = getpass.getpass("Nueva contraseña: ")
confirm  = getpass.getpass("Confirmar contraseña: ")

if password != confirm:
    print("Las contraseñas no coinciden.")
else:
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt(12)).decode()
    print(f"\nCopiar esta línea en config.py:\n")
    print(f"ADMIN_PASSWORD_HASH = '{hashed}'")
