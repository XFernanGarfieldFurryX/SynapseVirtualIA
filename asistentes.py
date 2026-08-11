# ============================================================
# SYNAPSE VIRTUAL IA - Asistentes Unificados (Versión 9.1)
# Proveedores: Hugging Face | Google Gemini | respuestas locales
# ============================================================

import re
import logging
import datetime
import time
from typing import Optional

import requests
from config import config

logger = logging.getLogger(__name__)

# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def obtener_fecha_hora():
    ahora = datetime.datetime.now()
    fecha = ahora.strftime("%d de %B de %Y")
    hora = ahora.strftime("%I:%M %p")
    return f"Son las {hora} del {fecha}."

# ============================================================
# RESPUESTAS LOCALES UNIFICADAS (FALLBACK)
# ============================================================

RESPUESTAS_LOCALES = {
    # Administrador
    r"asistencia\s*(del\s*personal|presencial)|control\s*de\s*asistencia": 
        "El sistema de asistencia presencial del personal está operativo.",
    r"profesores\s*presentes|docentes\s*en\s*el\s*instituto": 
        "Puede consultar el registro de asistencia presencial de los profesores.",
    r"ocupación\s*de\s*aulas|aulas\s*(disponibles|ocupadas)": 
        "Existen aulas disponibles para actividades académicas presenciales.",
    r"registro\s*(estudiantil|de\s*estudiantes)": 
        "El registro estudiantil presencial está actualizado.",
    r"planificación\s*(académica|de\s*clases)": 
        "La planificación académica presencial está disponible.",
    r"reporte\s*(administrativo|institucional|general)": 
        "Preparando reporte administrativo institucional.",
    r"gestión\s*financiera": 
        "La gestión financiera institucional está operativa.",
    r"estado\s*del\s*sistema": 
        "El sistema Synapse Virtual IA funciona correctamente.",
    r"(fecha\s*y\s*hora|hora\s*actual|qu[eé]\s*hora\s*es)": obtener_fecha_hora,
    r"versi[oó]n\s*del\s*sistema": 
        "Synapse Virtual IA, versión 2.2.",
    r"abre\s*(google|buscador)|busca\s*google": 
        "🌐 Abriendo <a href='https://www.google.com' target='_blank'>Google</a>.",
    r"abre\s*gmail|busca\s*gmail": 
        "🌐 Abriendo <a href='https://mail.google.com' target='_blank'>Gmail</a>.",
    r"abre\s*youtube|busca\s*youtube": 
        "🌐 Abriendo <a href='https://www.youtube.com' target='_blank'>YouTube</a>.",
    r"abre\s*whatsapp|busca\s*whatsapp": 
        "🌐 Abriendo <a href='https://web.whatsapp.com' target='_blank'>WhatsApp Web</a>.",
    r"abre\s*drive|busca\s*drive": 
        "🌐 Abriendo <a href='https://drive.google.com' target='_blank'>Google Drive</a>.",
    r"ayuda|comandos|qu[eé]\s*puedo\s*hacer": 
        """
        📋 Comandos disponibles:
        - asistencia del personal / control de asistencia
        - profesores presentes
        - ocupación de aulas / aulas disponibles
        - registro estudiantil
        - planificación académica
        - reporte administrativo
        - gestión financiera
        - estado del sistema
        - fecha y hora / qué hora es
        - versión del sistema
        - abre google / abre gmail / abre youtube / abre whatsapp / abre drive
        - ayuda / comandos
        """,
    # Docente
    r"nota|calificaci[oó]n|registrar\s*nota": 
        "📝 Puedes registrar calificaciones en el sistema.",
    r"materia|asignatura|clase": 
        "📚 Puedes gestionar las materias asignadas.",
    r"estudiante|alumno": 
        "🎓 Puedes consultar la información de tus estudiantes.",
    r"horario": 
        "📅 Tu horario docente está disponible en el sistema.",
    r"asistencia": 
        "📋 No olvide registrar la asistencia presencial al inicio de cada clase.",
    # Estudiante
    r"nota|calificaci[oó]n|promedio": 
        "📊 Puedes consultar tus calificaciones en el módulo de Lapsos Académicos.",
    r"horario\s*de\s*clases": 
        "📅 Tu horario de clases es de 7:00 a.m. a 1:30 p.m.",
    r"materias\s*disponibles": 
        "📚 Las materias disponibles son: Matemática, Lengua, Ciencias, Historia, Inglés y Educación Física.",
    r"actividad|tarea|ejercicio": 
        "📝 Revisa el módulo de Actividades para ver las tareas publicadas.",
    r"inscripci[oó]n|cupos|nuevo ingreso": 
        "📋 Las inscripciones se realizan en secretaría académica.",
    r"control de estudios|constancia|documentos": 
        "📄 Control de Estudios procesa constancias y certificaciones.",
    # 🔥 RESPUESTAS MEJORADAS PARA PREGUNTAS FRECUENTES
    r"cómo mejorar mi rendimiento|mejorar notas|qué hacer para mejorar|rendimiento académico": 
        """
        Para mejorar tu rendimiento académico, te recomiendo:

        1. Organiza un horario de estudio diario con bloques de 45 minutos y descansos de 10.
        2. Usa técnicas como el método Pomodoro o el estudio activo (preguntas y respuestas).
        3. Practica ejercicios de memoria y repaso espaciado (repasa cada día, luego cada semana).
        4. Duerme al menos 8 horas y mantén una alimentación equilibrada.
        5. Participa activamente en clase y pregunta todas tus dudas a los profesores.
        6. Utiliza herramientas como mapas mentales o resúmenes para organizar la información.
        7. Busca un espacio de estudio tranquilo y sin distracciones (sin teléfono).
        8. Establece metas pequeñas y alcanzables cada semana.

        ¡Recuerda que el esfuerzo constante es la clave del éxito académico! 🚀
        """,
    r"qué son las matemáticas|matemáticas|qué estudia matemáticas": 
        "Las matemáticas son la ciencia que estudia las relaciones entre cantidades, estructuras, espacios y cambios. Es fundamental para el desarrollo del pensamiento lógico y crítico. Se aplica en todas las ciencias y en la vida cotidiana.",
    r"qué es la biología|biología|qué estudia biología": 
        "La biología es la ciencia que estudia los seres vivos, su origen, evolución, estructura, funciones y relaciones con el medio ambiente. Abarca desde la molécula hasta los ecosistemas.",
    r"qué es la física|física|qué estudia física": 
        "La física es la ciencia que estudia las leyes fundamentales de la naturaleza, como el movimiento, la energía, la materia y las fuerzas. Es la base de muchas tecnologías modernas.",
    r"qué es la química|química|qué estudia química": 
        "La química es la ciencia que estudia la composición, estructura, propiedades y transformaciones de la materia. Es esencial para entender la vida y los materiales.",
    r"qué es la historia|historia|qué estudia historia": 
        "La historia es la ciencia que estudia los acontecimientos pasados de la humanidad, analizando sus causas, consecuencias y su impacto en el presente.",
    r"qué es la geografía|geografía|qué estudia geografía": 
        "La geografía es la ciencia que estudia la superficie terrestre, sus características físicas, humanas y la relación entre el ser humano y el medio ambiente.",
    # Soporte
    r"internet|wifi|red": 
        "🌐 Verifica la conexión de red. Reinicia el router.",
    r"impresora": 
        "🖨️ Revisa que haya papel y tinta suficiente.",
    r"computadora|pc|equipo": 
        "💻 Reinicia el equipo. Si el problema persiste, contacta al departamento de TI.",
    r"proyector|pantalla|display": 
        "📽️ Revisa el cable HDMI y la alimentación del proyector.",
    r"ticket|reporte|problema": 
        "🎫 Se ha generado un ticket de soporte.",
}

def buscar_respuesta_local(pregunta: str) -> Optional[str]:
    """Busca en el diccionario unificado de respuestas locales."""
    pregunta = pregunta.lower().strip()
    for patron, respuesta in RESPUESTAS_LOCALES.items():
        if re.search(patron, pregunta):
            return respuesta() if callable(respuesta) else respuesta
    return None

# ============================================================
# PROVEEDOR 1: GOOGLE GEMINI
# ============================================================

def consultar_gemini(prompt: str) -> Optional[str]:
    """Consulta a Google Gemini API."""
    api_key = config.GEMINI_API_KEY
    if not api_key or api_key == "tu_api_key_de_gemini_aqui":
        logger.warning("⚠️ GEMINI_API_KEY no configurada")
        return None

    # Intentar con gemini-2.0-flash (el más reciente)
    modelos = ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-pro"]
    for modelo in modelos:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent?key={api_key}"
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        try:
            response = requests.post(url, json=payload, timeout=30)
            if response.status_code == 200:
                data = response.json()
                respuesta = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text")
                if respuesta:
                    logger.info(f"✅ Gemini funcionó con {modelo}")
                    return respuesta
            elif response.status_code == 429:
                logger.warning(f"⏳ Gemini (429) con {modelo}, probando siguiente...")
                time.sleep(2)
                continue
            else:
                logger.warning(f"⚠️ Gemini falló con {modelo}: {response.status_code}")
        except Exception as e:
            logger.error(f"❌ Error en Gemini ({modelo}): {e}")
    return None

# ============================================================
# PROVEEDOR 2: HUGGING FACE (API)
# ============================================================

def consultar_huggingface(prompt: str) -> Optional[str]:
    """Usa la API de Hugging Face con google/flan-t5-large."""
    token = config.HUGGINGFACE_TOKEN
    if not token:
        logger.info("ℹ️ HUGGINGFACE_TOKEN no configurado.")
        return None

    API_URL = "https://api-inference.huggingface.co/models/google/flan-t5-large"
    headers = {"Authorization": f"Bearer {token}"}
    prompt_estructurado = f"""
Eres un asistente educativo del Colegio Latinoamericano II. 
Responde en español a la siguiente pregunta de forma clara, útil y detallada.
Pregunta: {prompt}
Respuesta (en español):
"""
    payload = {
        "inputs": prompt_estructurado,
        "parameters": {
            "max_new_tokens": 400,
            "temperature": 0.7,
            "do_sample": True,
            "top_p": 0.9,
        }
    }

    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=60)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and len(data) > 0:
                respuesta = data[0].get('generated_text', '')
                respuesta = respuesta.replace("Respuesta (en español):", "").replace("Respuesta:", "").strip()
                if respuesta and len(respuesta) > 10:
                    logger.info("✅ Hugging Face funcionó")
                    return respuesta
        elif response.status_code == 503:
            logger.warning("⏳ Hugging Face: modelo cargándose (503)")
        else:
            logger.error(f"❌ Error en Hugging Face: {response.status_code}")
    except Exception as e:
        logger.error(f"❌ Excepción en Hugging Face: {e}")
    return None

# ============================================================
# SELECTOR DE PROVEEDOR (CON FALLBACK LOCAL)
# ============================================================

def consultar_ia(prompt: str) -> Optional[str]:
    provider = config.IA_PROVIDER

    if provider == "gemini":
        # 1. Gemini
        respuesta = consultar_gemini(prompt)
        if respuesta:
            return respuesta
        # 2. Fallback a Hugging Face
        logger.info("ℹ️ Gemini falló, probando Hugging Face...")
        respuesta = consultar_huggingface(prompt)
        if respuesta:
            return respuesta
        # 3. Fallback a respuestas locales
        logger.info("ℹ️ Hugging Face falló, usando respuestas locales.")
        return buscar_respuesta_local(prompt)

    elif provider == "huggingface":
        # 1. Hugging Face
        respuesta = consultar_huggingface(prompt)
        if respuesta:
            return respuesta
        # 2. Fallback a Gemini
        logger.info("ℹ️ Hugging Face falló, probando Gemini...")
        respuesta = consultar_gemini(prompt)
        if respuesta:
            return respuesta
        # 3. Fallback a respuestas locales
        logger.info("ℹ️ Gemini falló, usando respuestas locales.")
        return buscar_respuesta_local(prompt)

    else:
        logger.warning(f"⚠️ Proveedor no soportado: {provider}. Usando respuestas locales.")
        return buscar_respuesta_local(prompt)

# ============================================================
# FUNCIONES PRINCIPALES (EXPORTADAS)
# ============================================================

def _responder_con_ia(pregunta: str, prompt_template: str, mensaje_defecto: str) -> str:
    if not pregunta or not pregunta.strip():
        return "Por favor, escribe una consulta válida."
    prompt = prompt_template.format(consulta=pregunta)
    respuesta_ia = consultar_ia(prompt)
    if respuesta_ia:
        return respuesta_ia
    # Último recurso: mensaje por defecto
    return mensaje_defecto

def consultar_asistente_admin(pregunta: str) -> str:
    prompt = """
Eres un asistente administrativo experto en gestión educativa.

Responde a la siguiente consulta de manera profesional y útil:

Consulta: {consulta}

Instrucciones:
- Responde en español.
- Sé claro y estructurado.
- Si no sabes algo, sugiere consultar la documentación.
- Mantén un tono profesional y útil.
"""
    return _responder_con_ia(pregunta, prompt, "No entendí ese comando. Escribe 'ayuda'.")

def responder_docente(pregunta: str) -> str:
    prompt = """
Eres un asistente educativo especializado en pedagogía y didáctica.

Responde a la siguiente consulta de un docente de manera práctica y pedagógica:

Consulta: {consulta}

Instrucciones:
- Responde en español.
- Ofrece ejemplos concretos.
- Sugiere estrategias pedagógicas aplicables.
- Tono cálido pero profesional.
"""
    return _responder_con_ia(pregunta, prompt, "👨‍🏫 No comprendí tu consulta.")

def responder_estudiante(pregunta: str) -> str:
    prompt = """
Eres un tutor académico paciente y motivador.

Responde a la siguiente consulta de un estudiante de manera clara y educativa:

Consulta: {consulta}

Instrucciones:
- Responde en español.
- Explica de manera simple y clara.
- Da ejemplos cuando sea necesario.
- Motiva al estudiante a seguir aprendiendo.
- Tono amable y accesible.
"""
    return _responder_con_ia(pregunta, prompt, "🎓 No comprendí tu consulta.")

def responder_soporte(pregunta: str) -> str:
    prompt = """
Eres un agente de soporte técnico especializado en sistemas educativos.

Responde a la siguiente consulta de soporte de manera clara y resolutiva:

Consulta: {consulta}

Instrucciones:
- Responde en español.
- Da pasos concretos para resolver el problema.
- Sé claro y directo.
- Si no puedes resolver, indica cómo contactar soporte humano.
- Tono profesional y amable.
"""
    return _responder_con_ia(pregunta, prompt, "🛠 No comprendí tu problema.")

def crear_ticket(usuario_id: int, descripcion: str, asunto: str = "Soporte técnico") -> dict:
    return {"id": 1, "mensaje": "Ticket creado correctamente"}
