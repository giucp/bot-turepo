import os
import feedparser
import threading
from telegram.ext import Application, ContextTypes
from flask import Flask

# =========================================================================
# CONFIGURACIÓN
# =========================================================================
TOKEN_API = "8987529061:AAHbtHB9MjWyFN1-l9hxQlqMqNeTwL8ODY0"
CHAT_ID = 8954280016  # Reemplaza con el ID numérico exacto de tu grupo

# Fuente de noticias
RSS_URL = "https://news.google.com/rss/search?q=Venezuela&hl=es-419&gl=VE&ceid=VE:es-419"

# Memoria temporal para no repetir noticias
enlaces_enviados = set()

# =========================================================================
# SERVIDOR WEB FANTASMA (PARA RENDER)
# =========================================================================
app_web = Flask(__name__)

@app_web.route('/')
def index():
    return "Bot de noticias activo."

def correr_servidor_web():
    puerto = int(os.environ.get("PORT", 8080))
    app_web.run(host="0.0.0.0", port=puerto)

# =========================================================================
# LECTURA Y PUBLICACIÓN DE NOTICIAS
# =========================================================================
async def chequear_y_publicar_rss(context: ContextTypes.DEFAULT_TYPE):
    print("Revisando fuentes RSS...")
    try:
        feed = feedparser.parse(RSS_URL)
        
        # Lee las últimas 5 noticias
        for entrada in reversed(feed.entries[:5]):
            enlace = entrada.link
            
            if enlace not in enlaces_enviados:
                titulo = entrada.title
                fuente = entrada.source.title if hasattr(entrada, 'source') else "Fuente de noticias"
                
                mensaje = (
                    f"📰 *{titulo}*\n\n"
                    f"✏️ *Fuente:* {fuente}\n"
                    f"🔗 [Leer noticia completa]({enlace})"
                )
                
                # Envío al grupo general
                await context.bot.send_message(
                    chat_id=CHAT_ID, 
                    text=mensaje, 
                    parse_mode="Markdown",
                    disable_web_page_preview=False
                )
                
                enlaces_enviados.add(enlace)
                print(f"Publicada: {titulo}")
                
    except Exception as e:
        print(f"Error al procesar RSS: {e}")

# =========================================================================
# ARRANQUE
# =========================================================================
def main():
    if TOKEN_API == "TU_TOKEN_DE_BOTFATHER" or CHAT_ID == -1001234567890:
        print("ERROR: Configura las variables TOKEN_API y CHAT_ID.")
        return

    threading.Thread(target=correr_servidor_web, daemon=True).start()

    app = Application.builder().token(TOKEN_API).build()

    # Ejecuta la revisión cada 3600 segundos (1 hora). Arranca a los 5 segundos de encender.
    app.job_queue.run_repeating(chequear_y_publicar_rss, interval=3600, first=5)

    app.run_polling()

if __name__ == '__main__':
    main()
