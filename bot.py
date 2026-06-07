import os
import re
from telegram import Update
from telegram.ext import Application, MessageHandler, ChatMemberHandler, filters, ContextTypes
from telegram.constants import ChatMemberStatus
from sightengine.client import SightengineClient

# =========================================================================
# CONFIGURACIÓN: PEGA TUS LLAVES AQUÍ
# =========================================================================
TOKEN_API = "8987529061:AAHbtHB9MjWyFN1-l9hxQlqMqNeTwL8ODY0"

# Credenciales de Sightengine (Filtro de fotos)
SIGHTENGINE_USER = "160856800"
SIGHTENGINE_SECRET = "gFP37qGNd4NZp6ka6jbQd2Bxg4XVC8Az"

# =========================================================================
# DICCIONARIO DE PALABRAS PROHIBIDAS
# =========================================================================
PALABRAS_BLOQUEADAS = [
    'maduro', 'chavez', 'chavismo', 'chavista', 'madurismo', 'madurista', 'psuv',
    'dictadura', 'dictador', 'tirano', 'regimen', 'narco', 'comunista', 'comunismo',
    'cono', 'conazo', 'coneo', 'marico', 'maricon', 'mierda', 'mierdero',
    'puta', 'puto', 'putos', 'putas', 'putamadre', 'hijodeputa', 'hijueputa',
    'verga', 'vergacion', 'vergazo', 'perra', 'zorra', 'pendejo', 'pendeja',
    'malparido', 'cabron', 'mamaguevo', 'mamahuevo', 'guevon', 'huevon'
]

# Expresión regular avanzada para detectar CUALQUIER tipo de enlace/URL o mención a canales t.me
PATRON_ENLACES = re.compile(r'(https?://[^\s]+|www\.[^\s]+|[a-zA-O0-9-]+\.[a-z]{2,}/?[^\s]*|t\.me/[^\s]+|@[\w_]+bot)', re.IGNORECASE)

# =========================================================================
# FILTRO DE TEXTO
# =========================================================================
def normalizar_y_filtrar(texto: str) -> bool:
    if not texto:
        return False
    t = texto.lower()
    t = t.replace('0', 'o').replace('1', 'i').replace('3', 'e').replace('4', 'a')
    t = t.replace('5', 's').replace('7', 't').replace('8', 'b').replace('@', 'a').replace('$', 's')
    t = t.replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ú', 'u').replace('ñ', 'n')
    texto_limpio = re.sub(r'[^a-z]', '', t)
    
    for palabra in PALABRAS_BLOQUEADAS:
        if palabra in texto_limpio:
            return True
    return False

# =========================================================================
# MODERACIÓN DE TEXTO Y LINKS
# =========================================================================
async def moderar_texto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    texto_usuario = update.message.text
    user = update.message.from_user
    nombre = user.first_name if user.first_name else "Ciudadano"
    
    # Detectamos si contiene groserías/política o si contiene cualquier tipo de link
    tiene_enlace = bool(PATRON_ENLACES.search(texto_usuario))
    es_infraccion = normalizar_y_filtrar(texto_usuario) or tiene_enlace

    if es_infraccion:
        try:
            await context.bot.delete_message(chat_id=update.message.chat_id, message_id=update.message.message_id)
            
            if tiene_enlace:
                aviso = f"⚠️ @{user.username if user.username else nombre}, no está permitido enviar enlaces, links ni promocionar otros canales en este grupo."
            else:
                aviso = f"⚠️ @{user.username if user.username else nombre}, mantén el respeto. Aquí compartimos reportes de servicios, tráfico, ofertas y más para toda Venezuela. Evita las groserías o la política."
                
            await context.bot.send_message(chat_id=update.message.chat_id, text=aviso)
            print(f"[MODERADO] Mensaje/Link borrado a: {user.username or nombre}")
        except Exception as e:
            print(f"[ERROR TEXTO/LINKS] No se pudo borrar: {e}")

# =========================================================================
# MODERACIÓN DE FOTOS (ESCÁNER DE IA)
# =========================================================================
async def moderar_foto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.photo:
        return

    user = update.message.from_user
    nombre = user.first_name if user.first_name else "Ciudadano"
    
    foto = await update.message.photo[-1].get_file()
    ruta_temporal = f"temp_{update.message.message_id}.jpg"
    
    try:
        await foto.download_to_drive(ruta_temporal)
        client = SightengineClient(SIGHTENGINE_USER, SIGHTENGINE_SECRET)
        resultado = client.check('nudity').set_file(ruta_temporal)
        
        es_inapropiada = False
        if resultado.get('status') == 'success':
            nudity = resultado.get('nudity', {})
            porcentaje_inapropiado = nudity.get('raw', 0) + nudity.get('partial', 0)
            if porcentaje_inapropiado > 0.60:
                es_inapropiada = True

        if es_inapropiada:
            await context.bot.delete_message(chat_id=update.message.chat_id, message_id=update.message.message_id)
            aviso = f"⚠️ @{user.username if user.username else nombre}, las fotos con contenido explícito o no apto no están permitidas en este grupo."
            await context.bot.send_message(chat_id=update.message.chat_id, text=aviso)
            print(f"[MODERADO - FOTO] Foto inapropiada borrada a: {user.username or nombre}")
            
    except Exception as e:
        print(f"[ERROR FOTO] Falló el escaneo de la imagen: {e}")
    finally:
        if os.path.exists(ruta_temporal):
            os.remove(ruta_temporal)

# =========================================================================
# ANTIBOTS: BLOQUEA CUENTAS AUTOMATIZADAS AL ENTRAR
# =========================================================================
async def controlar_nuevos_miembros(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Verificamos si hay un cambio de estado en los miembros del chat
    status_change = update.chat_member
    if not status_change or status_change.old_chat_member.status != ChatMemberStatus.LEFT:
        return
        
    # Validamos que sea una nueva incorporación
    if status_change.new_chat_member.status == ChatMemberStatus.MEMBER:
        nuevo_usuario = status_change.new_chat_member.user
        
        # ¡La prueba de fuego! Verificamos si el usuario que acaba de entrar es un BOT de spam
        if nuevo_usuario.is_bot:
            try:
                # Lo expulsamos (baneamos) del grupo inmediatamente
                await context.bot.ban_chat_member(chat_id=status_change.chat.id, user_id=nuevo_usuario.id)
                print(f"[ANTIBOT] Bot malicioso detectado y expulsado: @{nuevo_usuario.username or nuevo_usuario.first_name}")
            except Exception as e:
                print(f"[ERROR ANTIBOT] No se pudo expulsar al bot: {e}")

# =========================================================================
# ARRANQUE GENERAL DEL BOT Y SERVIDOR WEB FANTASMA (PARA RENDER)
# =========================================================================
from flask import Flask
import threading
import os

# 1. Creamos una mini página web de mentira
app_web = Flask(__name__)

@app_web.route('/')
def index():
    return "¡Bot de turepo.com encendido y vigilando 24/7!"

def correr_servidor_web():
    # Render nos asignará un puerto automáticamente
    puerto = int(os.environ.get("PORT", 8080))
    app_web.run(host="0.0.0.0", port=puerto)

def main():
    if TOKEN_API == "TU_TOKEN_DE_BOTFATHER" or SIGHTENGINE_USER == "TU_API_USER_DE_SIGHTENGINE":
        print("❌ ERROR: Olvidaste configurar tus llaves API.")
        return

    print("⚡ Encendiendo el Escudo Total de turepo.com en la nube...")
    
    # 2. Encendemos la página web en un hilo paralelo (para que Render no nos apague)
    hilo_web = threading.Thread(target=correr_servidor_web)
    hilo_web.start()

    # 3. Encendemos el bot de Telegram de forma normal
    app = Application.builder().token(TOKEN_API).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, moderar_texto))
    app.add_handler(MessageHandler(filters.PHOTO, moderar_foto))
    app.add_handler(ChatMemberHandler(controlar_nuevos_miembros, ChatMemberHandler.CHAT_MEMBER))
    
    app.run_polling()

if __name__ == '__main__':
    main()