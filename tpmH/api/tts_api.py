import os
import logging
from gtts import gTTS

logger = logging.getLogger(__name__)

def get_audio_url(text: str, voice: str = "en-US") -> str:
    """
    Usa la librería oficial gTTS de Google para generar el audio.
    100% Gratis, sin límites de API, rápido y seguro.
    """
    safe_word = "".join(c for c in text if c.isalnum() or c in (' ', '_')).replace(' ', '_').lower()
    filename = f"audio_{voice}_{safe_word}.mp3"
    
    # --- RUTAS ---
    current_working_dir = os.getcwd()
    if os.path.exists(os.path.join(current_working_dir, 'tpmH')):
        upload_dir = os.path.join(current_working_dir, 'tpmH', 'uploads')
    else:
        upload_dir = os.path.join(current_working_dir, 'uploads')
    
    os.makedirs(upload_dir, exist_ok=True)
    filepath = os.path.join(upload_dir, filename)

    # --- SISTEMA DE CACHÉ ---
    if os.path.exists(filepath):
        if os.path.getsize(filepath) > 500:
            logger.info(f"Caché local válida encontrada para: {text}")
            return f"/uploads/{filename}"
        else:
            logger.info(f"Archivo corrupto detectado y eliminado: {text}")
            os.remove(filepath)

    # --- GENERAR AUDIO CON GOOGLE ---
    try:
        # gTTS usa códigos de 2 letras. Si mandas "en-US", usamos "en".
        lang_code = "en" if "en" in voice else "es"
        
        logger.info(f"Generando audio gTTS para la palabra: '{text}' en idioma: '{lang_code}'")
        
        # Generamos el audio
        tts = gTTS(text=text, lang=lang_code, slow=False)
        
        # Lo guardamos directamente en el disco duro
        tts.save(filepath)
        
        return f"/uploads/{filename}"
            
    except Exception as e:
        logger.error(f"Error fatal con gTTS: {e}")
        return None