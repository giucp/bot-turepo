import os
import feedparser
import threading
import requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, ContextTypes
from flask import Flask

# =========================================================================
# CONFIGURACIÓN
# =========================================================================
TOKEN_API = "8987529061:AAHbtHB9MjWyFN1-l9hxQlqMqNeTwL8ODY0"
CHAT_ID = -1003444527887  # Tu ID real de supergrupo

RSS_URLS = [
    "https://news.google.com/rss/search?q=Venezuela&hl=es-419&gl=VE&ceid=VE:es-419",
    "https://elpitazo.net/feed/",
    "https://www.elnacional.com/feed/"
]

enlaces_enviados = set()

# =========================================================================
# SERVIDOR WEB FANTASMA
# =========================================================================
app_web = Flask(__name__)

@app_web.route('/')
def index():
    return "Bot activo: Desempaquetando URLs para vistas previas nativas."

def correr_servidor_web():
    puerto = int(os.environ.get("PORT", 8080))
    app_web.run(host="0.0.0.0", port=puerto)

def limpiar_html(texto):
    return texto.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

# =========================================================================
# MOTOR DESEMPAQUETADOR
# =========================================================================
def desempaquetar_url(url_original):
    # Si no es de Google, no perdemos tiempo, devolvemos la original
    if "news.google.com" not in url_original:
        return url_original
        
    try:
        # Cabecera para simular un navegador
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/114.0.0.0 Safari/537.36"
        }
        # Hacemos la petición y dejamos que siga la redirección
        respuesta = requests.get(url_original, headers=headers, timeout=5, allow_redirects=True)
        return respuesta.url
    except Exception as e:
        print(f"Error al desempaquetar {url_original}: {e}")
        return url_original

# =========================================================================
# LECTURA Y PUBLICACIÓN
# =========================================================================
async def chequear_y_publicar_rss(context: ContextTypes.DEFAULT_TYPE):
    print("Revisando fuentes RSS...")
    
    for url_feed in RSS_URLS:
        try:
            feed = feedparser.parse(url_feed)
            
            for entrada in reversed(feed.entries[:3]):
                enlace_sucio = entrada.link
                
                if enlace_sucio not in enlaces_enviados:
                    titulo = limpiar_html(entrada.title)
                    fuente = limpiar_html(entrada.source.title) if hasattr(entrada, 'source') else "Fuente de noticias"
                    
                    # 1. Obtenemos el enlace real del periódico
                    enlace_limpio = desempaquetar_url(enlace_sucio)
                    
                    # 2. Insertamos el enlace limpio en la etiqueta invisible de Telegram
                    mensaje = (
                        f"<a href='{enlace_limpio}'>&#8203;</a>📰 <b>{titulo}</b>\n\n"
                        f"✏️ <b>Fuente:</b> {fuente}"
                    )
                    
                    # 3. El botón también lleva al usuario a la URL limpia
                    botones = [[InlineKeyboardButton(text="🔗 Leer noticia completa", url=enlace_limpio)]]
                    teclado = InlineKeyboardMarkup(botones)
                    
                    try:
                        await context.bot.send_message(
                            chat_id=CHAT_ID, 
                            text=mensaje, 
                            parse_mode="HTML",
                            reply_markup=teclado
                        )
                        
                        enlaces_enviados.add(enlace_sucio)
                        print(f"Publicada con éxito: {titulo}")
                    except Exception as e_envio:
                        print(f"Error publicando en Telegram ({titulo}): {e_envio}")
                        
        except Exception as e:
            print(f"Error procesando el feed {url_feed}: {e}")

# =========================================================================
# ARRANQUE
# =========================================================================
def main():
    if TOKEN_API == "TU_TOKEN_DE_BOTFATHER":
        print("ERROR: Configura la variable TOKEN_API.")
        return

    threading.Thread(target=correr_servidor_web, daemon=True).start()

    app = Application.builder().token(TOKEN_API).build()

    app.job_queue.run_repeating(chequear_y_publicar_rss, interval=1800, first=5)

    app.run_polling()

if __name__ == '__main__':
    main()
