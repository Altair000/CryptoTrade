from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from config import BotConfig
import requests
import re

# Botones para usuarios no registrados
not_registered_keyboard = ReplyKeyboardMarkup([
    ["Registro", "Información"]
], resize_keyboard=True)

# Botones para usuarios registrados
registered_keyboard = ReplyKeyboardMarkup([
    ["VIP", "Crear Oferta"],
    ["Ver Oferta", "Información"]
], resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    response = requests.get(f"{BotConfig.API_URL}/api/users/check/{user_id}")
    data = response.json()
    
    if response.status_code == 200 and data.get("exists"):
        await update.message.reply_text(
            "¡Bienvenido de nuevo!",
            reply_markup=registered_keyboard
        )
    else:
        await update.message.reply_text(
            "¡Bienvenido! Regístrate o consulta información.",
            reply_markup=not_registered_keyboard
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = str(update.effective_user.id)
    context.user_data.setdefault("step", {})

    # Verificar registro
    response = requests.get(f"{BotConfig.API_URL}/api/users/check/{user_id}")
    data = response.json()
    is_registered = response.status_code == 200 and data.get("exists")

    if not is_registered:
        if text == "Registro":
            context.user_data["step"] = {"stage": "name"}
            await update.message.reply_text("Por favor, envía tu nombre y apellido:")
        elif text == "Información":
            await info(update, context)
        else:
            await update.message.reply_text("Por favor, usa los botones.", reply_markup=not_registered_keyboard)
    else:
        if text == "VIP":
            await vip(update, context)
        elif text == "Crear Oferta":
            await create_offer(update, context)
        elif text == "Ver Oferta":
            await view_offers(update, context)
        elif text == "Información":
            await info(update, context)
        else:
            # Manejo de pasos para crear oferta
            step = context.user_data.get("step", {})
            if step.get("stage") in ["offer_amount", "offer_min", "offer_max", "offer_comment"]:
                await process_offer_step(update, context)
            else:
                await update.message.reply_text("Por favor, usa los botones.", reply_markup=registered_keyboard)

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    text = update.message.text
    step = context.user_data.get("step", {})

    if step.get("stage") == "name":
        context.user_data["step"]["name"] = text
        context.user_data["step"]["stage"] = "age"
        await update.message.reply_text("Por favor, envía tu edad:")
    elif step.get("stage") == "age":
        if not text.isdigit() or int(text) < 18:
            await update.message.reply_text("Edad inválida. Debes ser mayor de 18. Envía tu edad:")
            return
        context.user_data["step"]["age"] = int(text)
        context.user_data["step"]["stage"] = "identity"
        await update.message.reply_text("Por favor, envía tu carnet de identidad (11 dígitos):")
    elif step.get("stage") == "identity":
        if not re.match(r"^\d{11}$", text):
            await update.message.reply_text("Carnet inválido. Debe tener 11 dígitos. Envía tu carnet:")
            return
        context.user_data["step"]["identity"] = text
        data = {
            "email": f"{user_id}@telegram.com",
            "username": f"user_{user_id}",
            "password": f"tg_{user_id}_pass",
            "name": context.user_data["step"]["name"],
            "age": context.user_data["step"]["age"],
            "identity_card": text,
            "telegram_id": user_id
        }
        response = requests.post(f"{BotConfig.API_URL}/api/users/register", json=data)
        if response.status_code == 201:
            await update.message.reply_text(
                "¡Usuario registrado con éxito!\n"
                "Advertencia: Cualquier acto delictivo o que afecte al bot o sus usuarios resultará en un bloqueo permanente de su cuenta.",
                reply_markup=registered_keyboard
            )
        else:
            await update.message.reply_text(f"Error al registrar: {response.json().get('error')}")
        context.user_data["step"] = {}

async def vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Opción en desarrollo.")

async def create_offer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Compra", callback_data="offer_buy")],
        [InlineKeyboardButton("Venta", callback_data="offer_sell")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("¿Qué tipo de oferta deseas crear?", reply_markup=reply_markup)

async def process_offer_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    step = context.user_data.get("step", {})

    if step.get("stage") == "offer_amount":
        if not text.replace('.', '', 1).isdigit() or float(text) <= 0:
            await update.message.reply_text("Monto inválido. Envía un número positivo para el monto en USDT:")
            return
        context.user_data["step"]["amount"] = float(text)
        context.user_data["step"]["stage"] = "offer_min"
        await update.message.reply_text("Envía el monto mínimo para la oferta:")
    elif step.get("stage") == "offer_min":
        if not text.replace('.', '', 1).isdigit() or float(text) <= 0:
            await update.message.reply_text("Monto mínimo inválido. Envía un número positivo:")
            return
        context.user_data["step"]["min_amount"] = float(text)
        context.user_data["step"]["stage"] = "offer_max"
        await update.message.reply_text("Envía el monto máximo para la oferta:")
    elif step.get("stage") == "offer_max":
        if not text.replace('.', '', 1).isdigit() or float(text) <= context.user_data["step"]["min_amount"]:
            await update.message.reply_text("Monto máximo inválido. Debe ser mayor que el mínimo. Envía el monto máximo:")
            return
        context.user_data["step"]["max_amount"] = float(text)
        context.user_data["step"]["stage"] = "offer_comment"
        await update.message.reply_text("Envía un comentario para la oferta:")
    elif step.get("stage") == "offer_comment":
        context.user_data["step"]["comment"] = text
        offer_type = context.user_data["step"]["type"]
        offer = {
            "type": offer_type,
            "amount": context.user_data["step"]["amount"],
            "min_amount": context.user_data["step"]["min_amount"],
            "max_amount": context.user_data["step"]["max_amount"],
            "comment": text
        }
        message = (
            f"📋 *Resumen de tu oferta*\n"
            f"Tipo: {offer_type.capitalize()}\n"
            f"Monto: {offer['amount']} USDT\n"
            f"Mínimo: {offer['min_amount']} USDT\n"
            f"Máximo: {offer['max_amount']} USDT\n"
            f"Comentario: {offer['comment']}\n\n"
            "Por favor, revisa y selecciona una opción:"
        )
        keyboard = [
            [InlineKeyboardButton("Aceptar", callback_data="offer_accept")],
            [InlineKeyboardButton("Rechazar", callback_data="offer_reject")],
            [InlineKeyboardButton("Editar", callback_data="offer_edit")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(message, parse_mode="Markdown", reply_markup=reply_markup)
        context.user_data["step"]["stage"] = "offer_review"

async def view_offers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    response = requests.get(f"{BotConfig.API_URL}/api/offers")
    if response.status_code != 200:
        await update.message.reply_text("Error al obtener ofertas.")
        return
    offers = response.json() if response.status_code == 200 else []
    
    if not offers:
        await update.message.reply_text("No hay ofertas disponibles.")
        return
    
    page = context.user_data.get("page", 1)
    per_page = 5
    start = (page - 1) * per_page
    end = start + per_page
    paginated_offers = offers[start:end]

    keyboard = []
    for offer in paginated_offers:
        text = f"Oferta #{offer['id']} - {offer['type']} - {offer['amount']} USDT"
        keyboard.append([InlineKeyboardButton(text, callback_data=f"offer_{offer['id']}")])
    
    nav_buttons = []
    if start > 0:
        nav_buttons.append(InlineKeyboardButton("Anterior", callback_data=f"page_{page-1}"))
    if end < len(offers):
        nav_buttons.append(InlineKeyboardButton("Siguiente", callback_data=f"page_{page+1}"))
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(f"Ofertas disponibles (Página {page}):", reply_markup=reply_markup)

async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = (
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
    await update.message.reply_text(message, parse_mode="Markdown")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = str(query.from_user.id)

    if data == "offer_buy":
        context.user_data["step"] = {"stage": "offer_amount", "type": "buy"}
        await query.message.reply_text("Envía el monto en USDT para tu oferta de compra:")
    elif data == "offer_sell":
        context.user_data["step"] = {"stage": "offer_amount", "type": "sell"}
        await query.message.reply_text("Envía el monto en USDT para tu oferta de venta:")
    elif data == "offer_accept":
        step = context.user_data.get("step", {})
        offer = {
            "type": step.get("type"),
            "amount": step.get("amount"),
            "min_amount": step.get("min_amount"),
            "max_amount": step.get("max_amount"),
            "comment": step.get("comment")
        }
        headers = {"Authorization": f"Bearer {create_token(user_id)}"}
        response = requests.post(f"{BotConfig.API_URL}/api/offers/create", json=offer, headers=headers)
        if response.status_code == 201:
            await query.message.reply_text("¡Oferta publicada con éxito!")
        else:
            await query.message.reply_text(f"Error al publicar oferta: {response.json().get('error')}")
        context.user_data["step"] = {}
    elif data == "offer_reject":
        await query.message.reply_text("Oferta cancelada.")
        context.user_data["step"] = {}
    elif data == "offer_edit":
        context.user_data["step"]["stage"] = "offer_amount"
        await query.message.reply_text(f"Editando oferta. Envía el nuevo monto en USDT para tu oferta de {context.user_data['step']['type']}:")
    elif data.startswith("offer_"):
        await query.message.reply_text("Acción para esta oferta en desarrollo.")
    elif data.startswith("page_"):
        page = int(data.split("_")[1])
        context.user_data["page"] = page
        await view_offers(query, context)

def main():
    app = Application.builder().token(BotConfig.TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, register))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.run_polling()

if __name__ == '__main__':
    main()
