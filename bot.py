import os
import feedparser
import threading
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, ContextTypes
from flask import Flask

# =========================================================================
# CONFIGURACIÓN
# =========================================================================
TOKEN_API = "8987529061:AAHbtHB9MjWyFN1-l9hxQlqMqNeTwL8ODY0"
CHAT_ID = -1003444527887  # Tu ID real de supergrupo

# Fuentes RSS
RSS_URLS = [
    "https://news.google.com/rss/search?q=Venezuela&hl=es-419&gl=VE&ceid=VE:es-419",
    "https://elpitazo.net/feed/",
    "https://www.elnacional.com/feed/"
]

enlaces_enviados = set()

# =========================================================================
# SERVIDOR WEB FANTASMA (PARA RENDER)
# =========================================================================
app_web = Flask(__name__)

@app_web.route('/')
def index():
    return "Bot activo: Usando motor nativo de Telegram para imágenes."

def correr_servidor_web():
    puerto = int(os.environ.get("PORT", 8080))
    app_web.run(host="0.0.0.0", port=puerto)

def limpiar_html(texto):
    return texto.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

# =========================================================================
# LECTURA Y PUBLICACIÓN DE NOTICIAS
# =========================================================================
async def chequear_y_publicar_rss(context: ContextTypes.DEFAULT_TYPE):
    print("Revisando fuentes RSS...")
    
    for url_feed in RSS_URLS:
        try:
            feed = feedparser.parse(url_feed)
            
            # Limita a 3 noticias por medio
            for entrada in reversed(feed.entries[:3]):
                enlace = entrada.link
                
                if enlace not in enlaces_enviados:
                    titulo = limpiar_html(entrada.title)
                    fuente = limpiar_html(entrada.source.title) if hasattr(entrada, 'source') else "Fuente de noticias"
                    
                    # EL TRUCO: Enlace invisible al principio (&#8203;)
                    # Obliga a Telegram a generar la vista previa con imagen nativamente.
                    mensaje = (
                        f"<a href='{enlace}'>&#8203;</a>📰 <b>{titulo}</b>\n\n"
                        f"✏️ <b>Fuente:</b> {fuente}"
                    )
                    
                    # Botón inferior para leer la noticia
                    botones = [[InlineKeyboardButton(text="🔗 Leer noticia completa", url=enlace)]]
                    teclado = InlineKeyboardMarkup(botones)
                    
                    try:
                        # Ahora siempre usamos send_message
                        await context.bot.send_message(
                            chat_id=CHAT_ID, 
                            text=mensaje, 
                            parse_mode="HTML",
                            reply_markup=teclado
                        )
                        
                        enlaces_enviados.add(enlace)
                        print(f"Publicada: {titulo}")
                    except Exception as e_envio:
                        print(f"Error en Telegram al publicar ({titulo}): {e_envio}")
                        
        except Exception as e:
            print(f"Error general procesando el feed {url_feed}: {e}")

# =========================================================================
# ARRANQUE
# =========================================================================
def main():
    if TOKEN_API == "TU_TOKEN_DE_BOTFATHER":
        print("ERROR: Configura la variable TOKEN_API.")
        return

    threading.Thread(target=correr_servidor_web, daemon=True).start()

    app = Application.builder().token(TOKEN_API).build()

    # Ejecuta cada 30 minutos (1800 segundos)
    app.job_queue.run_repeating(chequear_y_publicar_rss, interval=1800, first=5)

    app.run_polling()

if __name__ == '__main__':
    main()
