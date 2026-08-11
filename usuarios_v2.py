import pymysql
from werkzeug.security import generate_password_hash

DB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "",
    "database": "synapse_virtual_ia",
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor
}

USUARIOS_LISTA = [
    {"id": 1, "nombre": "Administrador Base", "usuario": "admin", "pass_plana": "Admin1234*", "rol": "admin", "correo": "admin@synapse.edu"},
    {"id": 2, "nombre": "Docente Base", "usuario": "docente", "pass_plana": "Docente1234*", "rol": "docente", "correo": "docente@synapse.edu"},
    {"id": 3, "nombre": "Estudiante Base", "usuario": "estudiante", "pass_plana": "Estudiante1234*", "rol": "estudiante", "correo": "estudiante@synapse.edu"},
    {"id": 4, "nombre": "Soporte Base", "usuario": "soporte", "pass_plana": "Soporte1234*", "rol": "soporte", "correo": "soporte@synapse.edu"},
    {"id": 5, "nombre": "Sandra", "usuario": "sandra", "pass_plana": "123456", "rol": "docente", "correo": "sandra@synapse.edu"},
    {"id": 6, "nombre": "Maylin", "usuario": "maylin", "pass_plana": "123456", "rol": "docente", "correo": "maylin@synapse.edu"},
    {"id": 7, "nombre": "Evita Admin", "usuario": "evita_admin", "pass_plana": "123456", "rol": "admin", "correo": "evita.admin@synapse.edu"},
    {"id": 8, "nombre": "Evita Soporte", "usuario": "evita_soporte", "pass_plana": "123456", "rol": "soporte", "correo": "evita.soporte@synapse.edu"},
    {"id": 9, "nombre": "Isabel", "usuario": "isabel", "pass_plana": "123456", "rol": "docente", "correo": "isabel@synapse.edu"},
    {"id": 10, "nombre": "Marian", "usuario": "marian", "pass_plana": "123456", "rol": "docente", "correo": "marian.docente@synapse.edu"},
    {"id": 11, "nombre": "Marian Soporte", "usuario": "marian_soporte", "pass_plana": "123456", "rol": "soporte", "correo": "marian.soporte@synapse.edu"}
]

def restaurar():
    conexion = pymysql.connect(**DB_CONFIG)
    with conexion.cursor() as cursor:
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
        cursor.execute("DROP TABLE IF EXISTS usuarios_final;")
        
        # Creamos la tabla definitiva
        cursor.execute("""
            CREATE TABLE usuarios_final (
                id INT AUTO_INCREMENT PRIMARY KEY,
                nombre VARCHAR(100) NOT NULL,
                usuario VARCHAR(50) NOT NULL UNIQUE,
                clave VARCHAR(255) NOT NULL,
                password VARCHAR(255) NOT NULL,
                rol VARCHAR(20) NOT NULL,
                correo VARCHAR(100) DEFAULT NULL,
                fecha_registro DATETIME DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)
        
        for u in USUARIOS_LISTA:
            # Forzamos el hash nativo de tu entorno Python 3.8
            hash_seguro = generate_password_hash(u["pass_plana"])
            cursor.execute("""
                INSERT INTO usuarios_final (id, nombre, usuario, clave, password, rol, correo)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (u["id"], u["nombre"], u["usuario"], hash_seguro, hash_seguro, u["rol"], u["correo"]))
            
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
        conexion.commit()
        print("====== ✅ TABLA USUARIOS_FINAL CREADA CON LOS 11 USUARIOS REALES ======")

if __name__ == "__main__":
    restaurar()
