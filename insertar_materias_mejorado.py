import pymysql
from config import config

# Conexión a la base de datos
conexion = pymysql.connect(
    host=config.MYSQL_HOST,
    user=config.MYSQL_USER,
    password=config.MYSQL_PASSWORD,
    database=config.MYSQL_DB,
    charset='utf8mb4',
    cursorclass=pymysql.cursors.DictCursor
)

# Lista de materias con su descripción (año) - VERSIÓN ÚNICA Y COMPLETA
materias = [
    # 1° Año
    {"nombre": "Castellano", "descripcion": "1° Año"},
    {"nombre": "Matemáticas", "descripcion": "1° Año"},
    {"nombre": "Inglés y Otras Lenguas Extranjeras", "descripcion": "1° Año"},
    {"nombre": "Geografía, Historia y Ciudadanía (GHC)", "descripcion": "1° Año"},
    {"nombre": "Ciencias Naturales", "descripcion": "1° Año"},
    {"nombre": "Arte y Patrimonio", "descripcion": "1° Año"},
    {"nombre": "Educación Física", "descripcion": "1° Año"},
    {"nombre": "Orientación y Convivencia", "descripcion": "1° Año"},
    {"nombre": "Grupos de Participación, Recreación y Producción", "descripcion": "1° Año"},

    # 2° Año (igual que 1° pero con descripción diferente)
    {"nombre": "Castellano", "descripcion": "2° Año"},
    {"nombre": "Matemáticas", "descripcion": "2° Año"},
    {"nombre": "Inglés y Otras Lenguas Extranjeras", "descripcion": "2° Año"},
    {"nombre": "Geografía, Historia y Ciudadanía (GHC)", "descripcion": "2° Año"},
    {"nombre": "Ciencias Naturales", "descripcion": "2° Año"},
    {"nombre": "Arte y Patrimonio", "descripcion": "2° Año"},
    {"nombre": "Educación Física", "descripcion": "2° Año"},
    {"nombre": "Orientación y Convivencia", "descripcion": "2° Año"},
    {"nombre": "Grupos de Participación, Recreación y Producción", "descripcion": "2° Año"},

    # 3° Año
    {"nombre": "Castellano", "descripcion": "3° Año"},
    {"nombre": "Matemáticas", "descripcion": "3° Año"},
    {"nombre": "Inglés y Otras Lenguas Extranjeras", "descripcion": "3° Año"},
    {"nombre": "Geografía, Historia y Ciudadanía (GHC)", "descripcion": "3° Año"},
    {"nombre": "Ciencias Naturales (Física, Química, Biología)", "descripcion": "3° Año"},
    {"nombre": "Educación Física", "descripcion": "3° Año"},
    {"nombre": "Orientación y Convivencia", "descripcion": "3° Año"},
    {"nombre": "Grupos de Participación, Recreación y Producción", "descripcion": "3° Año"},

    # 4° Año
    {"nombre": "Castellano", "descripcion": "4° Año"},
    {"nombre": "Matemáticas", "descripcion": "4° Año"},
    {"nombre": "Inglés y Otras Lenguas Extranjeras", "descripcion": "4° Año"},
    {"nombre": "Geografía, Historia y Ciudadanía (GHC)", "descripcion": "4° Año"},
    {"nombre": "Física", "descripcion": "4° Año"},
    {"nombre": "Química", "descripcion": "4° Año"},
    {"nombre": "Biología", "descripcion": "4° Año"},
    {"nombre": "Ciencias de la Tierra", "descripcion": "4° Año"},
    {"nombre": "Educación Física", "descripcion": "4° Año"},
    {"nombre": "Orientación y Convivencia", "descripcion": "4° Año"},
    {"nombre": "Grupos de Participación, Recreación y Producción", "descripcion": "4° Año"},

    # 5° Año
    {"nombre": "Castellano", "descripcion": "5° Año"},
    {"nombre": "Matemáticas", "descripcion": "5° Año"},
    {"nombre": "Inglés y Otras Lenguas Extranjeras", "descripcion": "5° Año"},
    {"nombre": "Geografía, Historia y Ciudadanía (GHC)", "descripcion": "5° Año"},
    {"nombre": "Física", "descripcion": "5° Año"},
    {"nombre": "Química", "descripcion": "5° Año"},
    {"nombre": "Biología", "descripcion": "5° Año"},
    {"nombre": "Ciencias de la Tierra / Formación para la Soberanía Nacional", "descripcion": "5° Año"},
    {"nombre": "Educación Física", "descripcion": "5° Año"},
    {"nombre": "Orientación y Convivencia", "descripcion": "5° Año"},
    {"nombre": "Grupos de Participación, Recreación y Producción", "descripcion": "5° Año"},
    {"nombre": "Proyecto de Investigación (requisito indispensable para optar al título de Bachiller)", "descripcion": "5° Año"},
]

try:
    with conexion.cursor() as cursor:
        # 1. Eliminar TODAS las materias existentes (para evitar duplicados)
        cursor.execute("DELETE FROM materias")
        conexion.commit()
        print("🧹 Tabla 'materias' limpiada completamente.")

        # 2. Insertar cada materia con su descripción
        for materia in materias:
            cursor.execute(
                "INSERT INTO materias (nombre, descripcion) VALUES (%s, %s)",
                (materia["nombre"], materia["descripcion"])
            )
            print(f"✅ Insertada: {materia['nombre']} - Descripción: {materia['descripcion']}")

        conexion.commit()
        print("\n" + "="*50)
        print("📚 RESUMEN DE CARGA DE MATERIAS (VERSIÓN MEJORADA)")
        print("="*50)
        print(f"✅ Total de materias insertadas: {len(materias)}")
        print("\n🎯 ¡Ahora todas las materias tienen su descripción correcta y sin duplicados!")

except Exception as e:
    print(f"❌ Error: {e}")
    conexion.rollback()
finally:
    conexion.close()
