# ============================================================
# SYNAPSE VIRTUAL IA - Configuración Central
# Versión 2.4 (CON VERIFICACIÓN EXPLÍCITA DE .ENV)
# ============================================================

import os
import sys
from datetime import timedelta
from dotenv import load_dotenv

# ============================================================
# 1. LOCALIZAR Y CARGAR .env
# ============================================================
# En desarrollo local se carga .env si existe.
# En Render se utilizan las Environment Variables configuradas
# directamente en el servicio.

dotenv_path = os.path.join(os.path.dirname(__file__), '.env')

if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
    print(f"✅ .env cargado desde: {dotenv_path}")
else:
    print("ℹ️ .env no encontrado; usando variables de entorno del sistema.")

# ============================================================
# 2. CONFIGURACIÓN BASE
# ============================================================
class Config:
    """Configuración base para la aplicación."""
    
    # SECRETOS
    SECRET_KEY = os.getenv("SECRET_KEY", "clave_por_defecto_cambiar_en_produccion")
      
    # MYSQL
    MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
    MYSQL_PORT = int(os.getenv("MYSQL_PORT", 3306))
    MYSQL_USER = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
    MYSQL_DB = os.getenv("MYSQL_DB", "synapse_virtual_ia")
    MYSQL_CHARSET = os.getenv("MYSQL_CHARSET", "utf8mb4")
    
    # SESIONES
    PERMANENT_SESSION_LIFETIME = int(os.getenv("PERMANENT_SESSION_LIFETIME", 30))
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "False").lower() == "true"
    SESSION_REFRESH_EACH_REQUEST = True
    
    # CORREO
    MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.getenv("MAIL_PORT", 587))
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "True").lower() == "true"
    MAIL_USE_SSL = os.getenv("MAIL_USE_SSL", "False").lower() == "true"
    MAIL_USERNAME = os.getenv("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", "noreply@synapse.edu")
    
    # IA
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
    HUGGINGFACE_TOKEN = os.getenv("HUGGINGFACE_TOKEN", "")
    IA_PROVIDER = os.getenv("IA_PROVIDER", "gemini") 

# ============================================================
# 3. CONFIGURACIONES POR ENTORNO
# ============================================================
class DevelopmentConfig(Config):
    DEBUG = True
    SESSION_COOKIE_SECURE = False

class TestingConfig(Config):
    TESTING = True
    DEBUG = False
    SESSION_COOKIE_SECURE = False
    MYSQL_DB = os.getenv("TEST_MYSQL_DB", "synapse_ia_test")

class ProductionConfig(Config):
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_SAMESITE = "Strict"

# ============================================================
# 4. SELECTOR DE CONFIGURACIÓN
# ============================================================
config_by_env = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig
}

def get_config(env=None):
    if env is None:
        env = os.getenv("FLASK_ENV", "development")
    return config_by_env.get(env, DevelopmentConfig)

# ============================================================
# 5. INSTANCIA PREDETERMINADA
# ============================================================
config = get_config()

# ============================================================
# 6. VERIFICACIÓN FINAL DE VARIABLES CRÍTICAS
# ============================================================
if __name__ == "__main__":
    print("\n" + "="*50)
    print("🔍 VERIFICACIÓN DE CONFIGURACIÓN")
    print("="*50)
    print(f"📁 .env cargado: {'✅ Sí' if os.path.exists(dotenv_path) else '❌ No'}")
    print(f"🔑 SECRET_KEY: {config.SECRET_KEY[:10]}...")
    print(f"🗄️ MYSQL_HOST: {config.MYSQL_HOST}")
    print(f"📧 MAIL_USERNAME: {config.MAIL_USERNAME or '(vacío)'}")
    print(f"🤖 GEMINI_API_KEY: {'✅ Cargada' if config.GEMINI_API_KEY else '❌ NO CARGADA'}")
    print(f"   (primeros 10 caracteres: {config.GEMINI_API_KEY[:10] if config.GEMINI_API_KEY else 'N/A'}...)")
    print(f"🔄 IA_PROVIDER: {config.IA_PROVIDER}")
    print("="*50 + "\n")
