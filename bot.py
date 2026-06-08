import os
import re
import feedparser
import threading
from telegram.ext import Application, ContextTypes
from flask import Flask

# =========================================================================
# CONFIGURACIÓN
# =========================================================================
# RECUERDA: Coloca tu nuevo TOKEN y asegúrate de que el CHAT_ID empiece con -100
TOKEN_API = "8987529061:AAHbtHB9MjWyFN1-l9hxQlqMqNeTwL8ODY0"
CHAT_ID = -1003444527887  

# Lista de fuentes RSS sobre Venezuela
RSS_URLS = [
    "https://news.google.com/rss/search?q=Venezuela&hl=es-419&gl=VE&ceid=VE:es-419",
    "https://elpitazo.net/feed/",
    "https://www.elnacional.com/feed/"
]

# Memoria temporal para no repetir noticias
enlaces_enviados = set()

# =========================================================================
# SERVIDOR WEB FANTASMA (PARA RENDER)
# =========================================================================
app_web = Flask(__name__)

@app_web.route('/')
def index():
    return "Bot de noticias activo y transmitiendo a múltiples fuentes."

def correr_servidor_web():
    puerto = int(os.environ.get("PORT", 8080))
    app_web.run(host="0.0.0.0", port=puerto)

# =========================================================================
# FUNCIONES DE EXTRACCIÓN Y LIMPIEZA
# =========================================================================
def extraer_imagen(entrada):
    # 1. Busca en atributos de contenido multimedia
    if hasattr(entrada, 'media_content') and len(entrada.media_content) > 0:
        return entrada.media_content[0].get('url')
    
    # 2. Busca en archivos adjuntos (enclosures)
    if hasattr(entrada, 'enclosures') and len(entrada.enclosures) > 0:
        for enc in entrada.enclosures:
            if 'image' in enc.get('type', '') or enc.get('url', '').endswith(('.jpg', '.png', '.jpeg')):
                return enc.get('url')
    
    # 3. Busca etiquetas <img> crudas dentro de la descripción HTML
    if hasattr(entrada, 'description'):
        match = re.search(r'<img[^>]+src="([^">]+)"', entrada.description)
        if match:
            return match.group(1)
            
    return None

def limpiar_html(texto):
    # Reemplaza caracteres que rompen el parse_mode de Telegram
    return texto.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

# =========================================================================
# LECTURA Y PUBLICACIÓN DE NOTICIAS
# =========================================================================
async def chequear_y_publicar_rss(context: ContextTypes.DEFAULT_TYPE):
    print("Revisando fuentes RSS...")
    
    for url in RSS_URLS:
        try:
            feed = feedparser.parse(url)
            
            # Se limitan a las últimas 3 de cada fuente por ciclo para evitar spam masivo
            for entrada in reversed(feed.entries[:3]):
                enlace = entrada.link
                
                if enlace not in enlaces_enviados:
                    titulo = limpiar_html(entrada.title)
                    fuente = limpiar_html(entrada.source.title) if hasattr(entrada, 'source') else "Fuente de noticias"
                    imagen_url = extraer_imagen(entrada)
                    
                    # Estructura del mensaje en HTML
                    mensaje = (
                        f"📰 <b>{titulo}</b>\n\n"
                        f"✏️ <b>Fuente:</b> {fuente}\n"
                        f"🔗 <a href='{enlace}'>Leer noticia completa</a>"
                    )
                    
                    try:
                        # Si encuentra la imagen, envía foto con leyenda. Si no, envía texto plano.
                        if imagen_url:
                            await context.bot.send_photo(
                                chat_id=CHAT_ID,
                                photo=imagen_url,
                                caption=mensaje,
                                parse_mode="HTML"
                            )
                        else:
                            await context.bot.send_message(
                                chat_id=CHAT_ID, 
                                text=mensaje, 
                                parse_mode="HTML",
                                disable_web_page_preview=False
                            )
                        
                        enlaces_enviados.add(enlace)
                        print(f"Publicada: {titulo}")
                    except Exception as e_envio:
                        print(f"Error al enviar a Telegram ({titulo}): {e_envio}")
                        
        except Exception as e:
            print(f"Error al procesar el feed {url}: {e}")

# =========================================================================
# ARRANQUE
# =========================================================================
def main():
    if TOKEN_API == "TU_TOKEN_DE_BOTFATHER" or CHAT_ID == -100XXXXXXXXXX:
        print("ERROR: Configura las variables TOKEN_API y CHAT_ID.")
        return

    threading.Thread(target=correr_servidor_web, daemon=True).start()

    app = Application.builder().token(TOKEN_API).build()

    # Ejecuta la revisión cada 1800 segundos (30 minutos). Arranca a los 5 segundos.
    app.job_queue.run_repeating(chequear_y_publicar_rss, interval=1800, first=5)

    app.run_polling()

if __name__ == '__main__':
    main()
