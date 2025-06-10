import telebot
from telebot import types
from telebot.util import content_type_service

from config import BotConfig
import requests
import re

# Inicializar Bot
bot = telebot.TeleBot(BotConfig.TELEGRAM_TOKEN)

# Botones Usuarios no registrados
not_registered_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
not_registered_keyboard.add(types.KeyboardButton("🪪 Registro 🪪"), types.KeyboardButton("ℹ️ Información ℹ️"))

# Botones para usuarios registrados
registered_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
registered_keyboard.add(types.KeyboardButton("👑 VIP 👑"), types.KeyboardButton("➕ Crear Oferta ➕"))
registered_keyboard.add(types.KeyboardButton("📑 Ver Ofertas 📑"), types.KeyboardButton("ℹ️ Información ℹ️"))

# Comando /Start
@bot.message_handler(commands=['start'])
def start(message):
    user_id = str(message.from_user.id)
    response = requests.get(f"{BotConfig.API_URL}/api/users/check/{user_id}")
    data = response.json()

    if response.status_code == 200 and data.get("exists"):
        bot.reply_to(message, "Bienvenido de nuevo !!.", reply_markup=registered_keyboard)
    else:
        bot.reply_to(message, "Bienvenido, Regístrate o consulte la información", reply_keyboard=not_registered_keyboard)

# Manejar mensajes de texto (botones)
@bot.message_handler(content_type_service=['text'])
def handle_message(message):
    text = message.text
    user_id = str(message.from_user.id)
    response = requests.get(f"{BotConfig.API_URL}/api/users/check/{user_id}")
    data = response.json()
    is_registered = response.status_code == 200 and data.get("exists")

    if not is_registered:
        if text == "🪪 Registro 🪪":
            bot.reply_to(message, "Por favor, envía tu nombre: ")
            bot.register_next_step_handler(message, register_name)
        elif text == "ℹ️ Información ℹ️":
            info(message)
        else:
            bot.reply_to(message, "Por favor, usa los botones.", reply_markup=not_registered_keyboard)

    else:
        if text == "👑 VIP 👑":
            vip(message)
        elif text == "➕ Crear Oferta ➕":
            create_offer(message)
        elif text == "📑 Ver Ofertas 📑":
            view_offers(message)
        elif text == "ℹ️ Información ℹ️":
            info(message)
        else:
            bot.reply_to(message, "Por favor, usa los botones.", reply_markup=registered_keyboard)

# Proceso de registro
def register_name(message):
    user_id = str(message.from_user.id)
    bot.reply_to(message, "Por favor, envía tu edad: ")
    bot.register_next_step_handler(message, register_age, {"name": message.text, "user_id": user_id})

def register_age(message, data):
    text = message.text
    if not text.isdigit() or int(text) < 18:
        bot.reply_to(message, "Edad inválida. Debes ser mayor de 18 años. Envía tu edad: ")
        bot.register_next_step_handler(message, register_age, data)
    data["age"] = int(text)
    bot.reply_to(message, "Por favor, envía tu carnet de identidad (11 dígitos): ")
    bot.register_next_step_handler(message, register_identity, data)

def register_identity(message, data):
    text = message.text
    if not re.match(r"^\d{11}$", text):
        bot.reply_to(message, "Carnet de identidad inválido. Debe de tener 11 dígitos. Envía tu carnet: ")
        bot.register_next_step_handler(message, register_identity, data)
        return

    data["identity_card"] = text
    user_data = {
        "email": f"{data['user_id']}@telegram.com",
        "username": f"user_{data['user_id']}",
        "password": f"tg_{data['user_id']}",
        "name": data['name'],
        "age": data['age'],
        "identity_card": data['identity_card'],
        "telegram_id": data['telegram_id']
    }
    response = requests.post(f"{BotConfig.API_URL}/api/users/register", json=user_data)
    if response.status_code == 201:
        bot.reply_to(message,
                     "Usuario registrado con éxito!!\n"
                     "Advertencia: Cualquier acto delictivo o que afecte al bot o sus usuarios resultará en un bloqueo permanente de su cuenta.", reply_markup=registered_keyboard
                     )
    else:
        bot.reply_to(message, f"Error al registrar: {response.json().get('error')}")

def vip(message):
    bot.reply_to(message, "⚠️ Opción en desarrollo ⚠️")

def create_offer(message):
    keyboard = types.InlineKeyboardMarkup()

    keyboard.add(types.InlineKeyboardButton("Compra", callback_data='offer_buy'))
    keyboard.add(types.InlineKeyboardButton("Venta", callback_data='offer_sell'))

    bot.reply_to(message, "Qué tipo de oferta deseas crear?", reply_markup=keyboard)

# Proceso de creación de oferta
def offer_amount(message, data):
    text = message.text
    if not text.replace('.', '', 1).isdigit() or float(text) <= 0:
        bot.reply_to(message, "Monto inválido. Envía un número positivo para el monto en USDT: ")
        bot.register_next_step_handler(message, offer_amount, data)
        return

    elif int(text) < 10 or int(text) > 200:
        bot.reply_to(message, "Monto invalido, la cantidad a transferir debe de estar en un rango de entre 10-200 USDT. Envie el monto a transferir:")
        bot.register_next_step_handler(message, offer_amount, data)
        return

    data["amount"] = float(text)
    bot.reply_to(message, "Envía un comentario para la oferta: ")
    bot.register_next_step_handler(message, offer_comment, data)

def offer_comment(message, data):
    data["comment"] = message.text
    message_text = (
        f"📑 *Resumen de tu oferta*\n"
        f"Tipo: {data['type'].capitalize()}\n"
        f"Monto: {data['amount']} USDT\n"
        f"Detalles: {data['comment']}\n\n"
        "Por favor, revisa y selecciona una opción:"
    )
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("✅ Aceptar ✅", callback_data='offer_accept'))
    keyboard.add(types.InlineKeyboardButton("❌ Rechazar ❌", callback_data='offer_reject'))
    keyboard.add(types.InlineKeyboardButton("✏️ Editar ✏️", callback_data='offer_edit'))

    bot.reply_to(message, message_text, parse_mode='Markdown', reply_markup=keyboard)

def view_offers(message):
    response = requests.get(f"{BotConfig.API_URL}/api/offers")
    if response.status_code != 200:
        bot.reply_to(message, "Error al obtener ofertas.")
        return

    offers = response.json() if response.status_code == 200 else []

    if not offers:
        bot.reply_to(message, "No hay ofertas disponibles.")
        return

    page = 1
    per_page = 5
    start = (page - 1) * per_page
    end = start + per_page
    paginated_offers = offers[start:end]

    keyboard = types.InlineKeyboardMarkup()
    for offer in paginated_offers:
        text = f"Oferta #{offer['id']} - {offer['type']} - {offer['amount']} USDT"

        keyboard.add(types.InlineKeyboardButton(text, callback_data=f"offer_{offer['id']}"))
    nav_buttons = []
    if start > 0:
        nav_buttons.append(types.InlineKeyboardButton("Anterior", callback_data=f"page_{page-1}"))
    if end < len(offers):
        nav_buttons.append(types.InlineKeyboardButton("Siguiente", callback_data=f"page_{page+1}"))
    if nav_buttons:
        keyboard.add(*nav_buttons)

    bot.reply_to(message, f"Ofertas disponibles (Página {page}):", reply_markup=keyboard)

def info(message):
    message_text = (
        "📚 *Información del Bot*\n\n"
        "Este bot facilita transacciones P2P de USDT (BEP-20).\n"
        "- *Registro*: Regístrate con tus datos para comenzar.\n"
        "- *VIP*: En desarrollo, ¡pronto más beneficios!\n"
        "- *Crear Oferta*: Crea ofertas de compra o venta de USDT.\n"
        "- *Ver Oferta*: Consulta ofertas disponibles.\n\n"
        "*Políticas de Uso*:\n"
        "- No se permiten actividades ilegales o fraudulentas.\n"
        "- Cualquier violación resultará en un bloqueo permanente.\n"
        "- Contacta al soporte para dudas: @TuSoporte"
    )
    bot.reply_to(message, message_text, parse_mode="Markdown")

# Manejador de botones inline
@bot.callback_query_handler(func=lambda call: True)
def button_callback(call):
    user_id = str(call.from_user.id)
    data = call.data

    if data == "offer_buy":
        bot.answer_callback_query(call.id)
        bot.reply_to(call.message, "Envía el monto en USDT para tu oferta de compra:")
        bot.register_next_step_handler(call.message, offer_amount, {"type": "buy", "user_id": user_id})
    elif data == "offer_sell":
        bot.answer_callback_query(call.id)
        bot.reply_to(call.message, "Envía el monto en USDT para tu oferta de venta:")
        bot.register_next_step_handler(call.message, offer_amount, {"type": "sell", "user_id": user_id})
    elif data == "offer_accept":
        bot.answer_callback_query(call.id)
        data = call.message.reply_to_message
        offer = {
            "type": data["type"],
            "amount": data["amount"],
            "min_amount": data["min_amount"],
            "max_amount": data["max_amount"],
            "comment": data["comment"]
        }
        headers = {"Authorization": f"Bearer {create_token(user_id)}"}
        response = requests.post(f"{BotConfig.API_URL}/api/offers/create", json=offer, headers=headers)
        if response.status_code == 201:
            bot.reply_to(call.message, "¡Oferta publicada con éxito!")
        else:
            bot.reply_to(call.message, f"Error al publicar oferta: {response.json().get('error')}")
    elif data == "offer_reject":
        bot.answer_callback_query(call.id)
        bot.reply_to(call.message, "Oferta cancelada.")
    elif data == "offer_edit":
        bot.answer_callback_query(call.id)
        data = call.message.reply_to_message
        bot.reply_to(call.message, f"Editando oferta. Envía el nuevo monto en USDT para tu oferta de {data['type']}:")
        bot.register_next_step_handler(call.message, offer_amount, {"type": data["type"], "user_id": user_id})
    elif data.startswith("offer_"):
        bot.answer_callback_query(call.id)
        bot.reply_to(call.message, "Acción para esta oferta en desarrollo.")
    elif data.startswith("page_"):
        bot.answer_callback_query(call.id)
        page = int(data.split("_")[1])
        response = requests.get(f"{BotConfig.API_URL}/api/offers")
        if response.status_code != 200:
            bot.reply_to(call.message, "Error al obtener ofertas.")
            return
        offers = response.json() if response.status_code == 200 else []
        if not offers:
            bot.reply_to(call.message, "No hay ofertas disponibles.")
            return
        per_page = 5
        start = (page - 1) * per_page
        end = start + per_page
        paginated_offers = offers[start:end]
        keyboard = types.InlineKeyboardMarkup()
        for offer in paginated_offers:
            text = f"Oferta #{offer['id']} - {offer['type']} - {offer['amount']} USDT"
            keyboard.add(types.InlineKeyboardButton(text, callback_data=f"offer_{offer['id']}"))
        nav_buttons = []
        if start > 0:
            nav_buttons.append(types.InlineKeyboardButton("Anterior", callback_data=f"page_{page-1}"))
        if end < len(offers):
            nav_buttons.append(types.InlineKeyboardButton("Siguiente", callback_data=f"page_{page+1}"))
        if nav_buttons:
            keyboard.add(*nav_buttons)
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"Ofertas disponibles (Página {page}):",
            reply_markup=keyboard
            )

# Función para crear token (requerida para la API)
def create_token(user_id):
    import jwt
    from datetime import datetime, timedelta
    from bot.config import BotConfig
    payload = {
        'id': user_id,
        'exp': datetime.utcnow() + timedelta(hours=1)
    }
    return jwt.encode(payload, BotConfig.JWT_SECRET, algorithm='HS256')

# Iniciar el bot
bot.polling()
