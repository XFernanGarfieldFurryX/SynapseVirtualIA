import pymysql
from config import config

# Tus credenciales de la base de datos (las tienes en .env)
conexion = pymysql.connect(
    host=config.MYSQL_HOST,
    user=config.MYSQL_USER,
    password=config.MYSQL_PASSWORD,
    database=config.MYSQL_DB,
    charset='utf8mb4',
    cursorclass=pymysql.cursors.DictCursor
)

# Lista de usuarios (de los datos que me diste)
usuarios = [
    ('admin@synapse.edu', 'Admin1234*', 'Administrador', 'admin'),
    ('docente@synapse.edu', 'Docente1234*', 'Docente', 'profesor'),
    ('estudiante@synapse.edu', 'Estudiante1234*', 'Estudiante', 'estudiante'),
    ('soporte@synapse.edu', 'Soporte1234*', 'Soporte Técnico', 'soporte'),
    ('sandra@synapse.edu', '123456', 'Sandra - Docente', 'profesor'),
    ('maylin@synapse.edu', '123456', 'Maylin - Docente', 'profesor'),
    ('evita@synapse.edu', '123456', 'Evita - Administradora', 'admin'),
    ('evita-soporte@synapse.edu', '123456', 'Evita - Soporte SOS', 'soporte'),
    ('isabel@synapse.edu', '123456', 'Isabel - Docente', 'profesor'),
    ('marian@synapse.edu', '123456', 'Marian - Docente', 'profesor'),
    ('marian-soporte@synapse.edu', '123456', 'Marian - Soporte SOS', 'soporte'),
]

try:
    with conexion.cursor() as cursor:
        # Asegurar que la tabla usuarios existe (con los campos que usa el login)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INT AUTO_INCREMENT PRIMARY KEY,
                nombre VARCHAR(100) NOT NULL,
                correo VARCHAR(100) UNIQUE NOT NULL,
                usuario VARCHAR(50) UNIQUE,
                password VARCHAR(255) NOT NULL,
                rol ENUM('admin','profesor','estudiante','soporte') NOT NULL,
                activo BOOLEAN DEFAULT TRUE,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Insertar o actualizar cada usuario
        for correo, password, nombre, rol in usuarios:
            # Generar nombre de usuario a partir del correo
            usuario = correo.split('@')[0]
            
            # Verificar si ya existe
            cursor.execute("SELECT id FROM usuarios WHERE correo = %s", (correo,))
            existe = cursor.fetchone()
            
            if existe:
                # Actualizar
                cursor.execute("""
                    UPDATE usuarios 
                    SET password = %s, nombre = %s, rol = %s, activo = 1
                    WHERE correo = %s
                """, (password, nombre, rol, correo))
                print(f"🔄 Actualizado: {correo}")
            else:
                # Insertar
                cursor.execute("""
                    INSERT INTO usuarios (nombre, correo, usuario, password, rol, activo)
                    VALUES (%s, %s, %s, %s, %s, 1)
                """, (nombre, correo, usuario, password, rol))
                print(f"✅ Insertado: {correo}")
        
        conexion.commit()
        print("\n🎉 ¡Todos los usuarios han sido cargados exitosamente!")
        print("📋 Prueba con: admin@synapse.edu / Admin1234*")
        
except Exception as e:
    print(f"❌ Error: {e}")
    conexion.rollback()
finally:
    conexion.close()
