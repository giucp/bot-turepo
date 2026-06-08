import os
import re
import feedparser
import threading
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, ContextTypes
from flask import Flask

# =========================================================================
# CONFIGURACIÓN
# =========================================================================
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
    return "Bot de noticias activo con botones integrados."

def correr_servidor_web():
    puerto = int(os.environ.get("PORT", 8080))
    app_web.run(host="0.0.0.0", port=puerto)

# =========================================================================
# FUNCIONES DE EXTRACCIÓN Y LIMPIEZA
# =========================================================================
def extraer_imagen(entrada):
    if hasattr(entrada, 'media_content') and len(entrada.media_content) > 0:
        return entrada.media_content[0].get('url')
    
    if hasattr(entrada, 'enclosures') and len(entrada.enclosures) > 0:
        for enc in entrada.enclosures:
            if 'image' in enc.get('type', '') or enc.get('url', '').endswith(('.jpg', '.png', '.jpeg')):
                return enc.get('url')
    
    if hasattr(entrada, 'description'):
        match = re.search(r'<img[^>]+src="([^">]+)"', entrada.description)
        if match:
            return match.group(1)
            
    return None

def limpiar_html(texto):
    return texto.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

# =========================================================================
# LECTURA Y PUBLICACIÓN DE NOTICIAS
# =========================================================================
async def chequear_y_publicar_rss(context: ContextTypes.DEFAULT_TYPE):
    print("Revisando fuentes RSS...")
    
    for url in RSS_URLS:
        try:
            feed = feedparser.parse(url)
            
            for entrada in reversed(feed.entries[:3]):
                enlace = entrada.link
                
                if enlace not in enlaces_enviados:
                    titulo = limpiar_html(entrada.title)
                    fuente = limpiar_html(entrada.source.title) if hasattr(entrada, 'source') else "Fuente de noticias"
                    imagen_url = extraer_imagen(entrada)
                    
                    # Cuerpo del mensaje limpio (sin el enlace expuesto)
                    mensaje = (
                        f"📰 <b>{titulo}</b>\n\n"
                        f"✏️ <b>Fuente:</b> {fuente}"
                    )
                    
                    # Construcción del botón inline
                    botones = [[InlineKeyboardButton(text="🔗 Leer noticia completa", url=enlace)]]
                    teclado = InlineKeyboardMarkup(botones)
                    
                    try:
                        if imagen_url:
                            await context.bot.send_photo(
                                chat_id=CHAT_ID,
                                photo=imagen_url,
                                caption=mensaje,
                                parse_mode="HTML",
                                reply_markup=teclado
                            )
                        else:
                            await context.bot.send_message(
                                chat_id=CHAT_ID, 
                                text=mensaje, 
                                parse_mode="HTML",
                                reply_markup=teclado
                            )
                        
                        enlaces_enviados.add(enlace)
                        print(f"Publicada con botón: {titulo}")
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

    app.job_queue.run_repeating(chequear_y_publicar_rss, interval=1800, first=5)

    app.run_polling()

if __name__ == '__main__':
    main()
