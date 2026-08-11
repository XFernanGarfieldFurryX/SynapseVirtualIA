from transformers import pipeline

# Cargar modelo pequeño (descarga ~1 GB la primera vez)
generador = pipeline("text2text-generation", model="google/flan-t5-large")

# Probar
respuesta = generador("Responde solo OK:", max_new_tokens=5)[0]['generated_text']
print("🤖 Respuesta:", respuesta)
