import telebot
import configure
import sqlite3
from telebot import types
import threading

client = telebot.TeleBot(configure.config['token'])
db = sqlite3.connect('baza.db', check_same_thread=False)
lock = threading.Lock()

def get_cursor():
    return db.cursor()

# Глобальная переменная для хранения ID текущей покупки
current_purchase_id = None

# --- Создание таблиц ---
with lock:
    cur = get_cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS users (
        id BIGINT,
        nick TEXT,
        cash INT,
        access INT,
        bought INT
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS shop (
        id INT,
        name TEXT,
        price INT,
        tovar TEXT,
        whobuy TEXT
    )""")
    db.commit()

# --- Функции для меню ---

def main_menu(access_level=0):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_shop = types.KeyboardButton("🛍 Магазин")
    btn_donate = types.KeyboardButton("💰 Пополнить баланс")
    btn_mybuy = types.KeyboardButton("📜 Мои покупки")
    btn_help = types.KeyboardButton("🆘 Помощь")
    btn_profile = types.KeyboardButton("⚙️ Профиль")
    markup.row(btn_shop, btn_donate)
    markup.row(btn_mybuy, btn_help, btn_profile)
    if access_level >= 1:
        btn_admin = types.KeyboardButton("🔑 Админ-панель")
        markup.add(btn_admin)
    return markup

def admin_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_addbuy = types.KeyboardButton("➕ Добавить товар")
    btn_editbuy = types.KeyboardButton("✏️ Изменить товар")
    btn_rembuy = types.KeyboardButton("❌ Удалить товар")
    btn_users = types.KeyboardButton("👥 Список пользователей")
    btn_back = types.KeyboardButton("🔙 Выйти из админ-панели")
    markup.row(btn_addbuy, btn_editbuy, btn_rembuy)
    markup.row(btn_users)
    markup.row(btn_back)
    return markup

# --- ХЕНДЛЕРЫ ---

@client.message_handler(commands=['start'])
def start(message):
    cid = message.chat.id
    uid = message.from_user.id
    nick = message.from_user.first_name
    cur = get_cursor()
    cur.execute("SELECT * FROM users WHERE id = ?", (uid,))
    user = cur.fetchone()
    if user is None:
        if uid in [7006370658, 6916747393]:
            cur.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?)", (uid, nick, 0, 777, 0))
        else:
            cur.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?)", (uid, nick, 0, 0, 0))
        db.commit()
        access = 777 if uid in [7006370658, 6916747393] else 0
        client.send_message(cid, 
            f"👋 Добро пожаловать, {nick}!\nТы попал в бота-магазин. Измени этот текст под себя!",
            reply_markup=main_menu(access)
        )
    else:
        access = user[3]
        client.send_message(cid,
            "Ты уже зарегистрирован! Вот главное меню:",
            reply_markup=main_menu(access)
        )

@client.message_handler(commands=['help'])
def helpcmd(message):
    cid = message.chat.id
    uid = message.from_user.id
    cur = get_cursor()
    cur.execute("SELECT * FROM users WHERE id = ?", (uid,))
    user = cur.fetchone()
    if not user:
        client.send_message(cid, "Сначала введите /start для регистрации!")
        return
    access = user[3]
    text = (
        "📋 *Список команд:*\n\n"
        "/start — Главное меню\n"
        "/profile — Посмотреть профиль\n"
        "/help — Список команд\n"
        "/buy — Купить товар\n"
        "/donate — Пополнить счёт\n"
        "/mybuy — Мои покупки\n"
        "\nАдминские:\n"
        "/makeadmin — Сделать пользователя админом\n"
        "/giverub — Выдать деньги\n"
        "/addbuy — Добавить товар\n"
        "/editbuy — Изменить товар\n"
        "/rembuy — Удалить товар\n"
        "/users — Список пользователей\n"
    )
    client.send_message(cid, text, parse_mode='Markdown', reply_markup=main_menu(access))

@client.message_handler(commands=['profile','myprofile'])
def myprofile(message):
    cid = message.chat.id
    uid = message.from_user.id
    cur = get_cursor()
    cur.execute("SELECT * FROM users WHERE id = ?", (uid,))
    user = cur.fetchone()
    if not user:
        client.send_message(cid, "⛔ Сначала зарегистрируйтесь командой /start.")
        return
    user_id, nick, cash, access, bought = user
    if access == 0:
        accessname = 'Пользователь'
    elif access == 1:
        accessname = 'Администратор'
    elif access == 777:
        accessname = 'Разработчик'
    else:
        accessname = 'Неизвестно'
    text = (
        f"⚙️ *Ваш профиль:*\n\n"
        f"👤 *ID:* {user_id}\n"
        f"💸 *Баланс:* {cash} ₽\n"
        f"👑 *Уровень доступа:* {accessname}\n"
        f"📦 *Куплено товаров:* {bought}\n"
    )
    client.send_message(cid, text, parse_mode='Markdown', reply_markup=main_menu(access))

@client.message_handler(commands=['makeadmin'])
def make_admin(message):
    cid = message.chat.id
    args = message.text.split()
    if len(args) < 2:
        client.send_message(cid, "Использование: /makeadmin <user_id>")
        return
    uid = message.from_user.id
    cur = get_cursor()
    cur.execute("SELECT access FROM users WHERE id = ?", (uid,))
    row = cur.fetchone()
    if not row or row[0] < 1:
        client.send_message(cid, "⛔ У вас нет прав на добавление админа!")
        return
    try:
        target_id = int(args[1])
        cur.execute("SELECT * FROM users WHERE id = ?", (target_id,))
        user = cur.fetchone()
        if not user:
            client.send_message(cid, "⛔ Пользователь с таким ID не найден.")
            return
        cur.execute("UPDATE users SET access = 1 WHERE id = ?", (target_id,))
        db.commit()
        client.send_message(cid, f"✅ Пользователь {target_id} теперь Администратор!")
    except ValueError:
        client.send_message(cid, "⛔ Укажите корректный ID (числом).")

# --- Обработка inline-кнопок для покупки товара ---
@client.message_handler(commands=['buy'])
def buy_command(message):
    cid = message.chat.id
    uid = message.from_user.id
    cur = get_cursor()
    text = "🛍 *Список товаров:*\n\n"
    markup = types.InlineKeyboardMarkup(row_width=1)
    for item in cur.execute("SELECT * FROM shop"):
        item_id, name, price, tovar, whobuy = item
        button = types.InlineKeyboardButton(text=f"{name} - {price}₽", callback_data=f"buy_{item_id}")
        markup.add(button)
        text += f"{item_id}. {name} - {price}₽\n"
    client.send_message(cid, text, parse_mode='Markdown', reply_markup=markup)

@client.callback_query_handler(func=lambda call: call.data.startswith("buy_"))
def callback_buy(call):
    cid = call.message.chat.id
    uid = call.from_user.id
    try:
        product_id = int(call.data.split("_")[1])
    except:
        client.answer_callback_query(call.id, "Неверные данные товара!")
        return
    cur = get_cursor()
    cur.execute("SELECT * FROM shop WHERE id = ?", (product_id,))
    product = cur.fetchone()
    if not product:
        client.answer_callback_query(call.id, "Товар не найден!")
        return
    global current_purchase_id
    current_purchase_id = product_id

    # Просто даём ссылку на donate.stream без параметров, чтобы не было 404
    payment_url = configure.config.get('payment_url', 'https://donate.stream/').rstrip('/')
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_pay = types.InlineKeyboardButton(text="Оплатить", url=payment_url)
    btn_paid = types.InlineKeyboardButton(text="Оплатил", callback_data=f"paid_{product_id}")
    markup.add(btn_pay, btn_paid)

    client.send_message(cid, f"Вы выбрали товар: {product[1]} за {product[2]}₽.\nОплатите по ссылке (сумму укажите вручную) и нажмите 'Оплатил', когда оплата будет произведена.", reply_markup=markup)
    client.answer_callback_query(call.id)

@client.callback_query_handler(func=lambda call: call.data.startswith("paid_"))
def callback_paid(call):
    cid = call.message.chat.id
    uid = call.from_user.id
    # После нажатия кнопки "Оплатил" запрашиваем игровой ID
    client.send_message(cid, "Спасибо за оплату! Пожалуйста, введите ваш игровой ID для получения товара:")
    client.answer_callback_query(call.id)
    client.register_next_step_handler(call.message, handle_game_id)

def handle_game_id(message):
    uid = message.from_user.id
    game_id = message.text
    cur = get_cursor()
    cur.execute("SELECT * FROM shop WHERE id = ?", (current_purchase_id,))
    product = cur.fetchone()
    if product:
        client.send_message(uid, f"✅ Спасибо!\nВаш игровой ID: {game_id}\n\nТовар: {product[3]}\n\nСпасибо за покупку!")
        client.send_message(596060542, f"✉️ | Пользователь {uid} купил товар {product[1]}.\nИгровой ID: {game_id}")
    else:
        client.send_message(uid, "🚫 | Ошибка при получении данных о товаре.")

# --- Обработка кнопок меню ---
@client.message_handler(func=lambda m: m.text == "🛍 Магазин")
def button_shop(message):
    buy_command(message)

@client.message_handler(func=lambda m: m.text == "💰 Пополнить баланс")
def button_donate(message):
    cid = message.chat.id
    uid = message.from_user.id
    cur = get_cursor()
    cur.execute("SELECT access FROM users WHERE id = ?", (uid,))
    row = cur.fetchone()
    access = row[0] if row else 0
    payment_url = configure.config.get('payment_url', 'https://donate.stream/')
    client.send_message(cid, f"💰 Оплатите по ссылке:\n{payment_url}\n\nУкажите сумму вручную. После оплаты свяжитесь с администратором для зачисления средств.", reply_markup=main_menu(access))

@client.message_handler(func=lambda m: m.text == "📜 Мои покупки")
def button_mybuy(message):
    cid = message.chat.id
    uid = message.from_user.id
    cur = get_cursor()
    cur.execute("SELECT * FROM users WHERE id = ?", (uid,))
    user = cur.fetchone()
    if not user:
        client.send_message(cid, "Сначала /start для регистрации!")
        return
    access = user[3]
    text = "*🗂 | Список купленных товаров:*\n\n"
    for infoshop in cur.execute("SELECT * FROM shop"):
        if str(uid) in infoshop[4]:
            text += f"*{infoshop[0]}. {infoshop[1]}*\nТовар: {infoshop[3]}\n\n"
    client.send_message(cid, text, parse_mode='Markdown', reply_markup=main_menu(access))

@client.message_handler(func=lambda m: m.text == "🆘 Помощь")
def button_help(message):
    cid = message.chat.id
    uid = message.from_user.id
    cur = get_cursor()
    cur.execute("SELECT access FROM users WHERE id = ?", (uid,))
    row = cur.fetchone()
    if not row:
        client.send_message(cid, "Сначала /start для регистрации!")
        return
    access = row[0]
    text = (
        "🆘 Помощь\n\n"
        "Используйте /help для списка команд.\n"
        "Либо кнопки меню для навигации."
    )
    client.send_message(cid, text, reply_markup=main_menu(access))

@client.message_handler(func=lambda m: m.text == "⚙️ Профиль")
def button_profile(message):
    myprofile(message)

@client.message_handler(func=lambda m: m.text == "🔑 Админ-панель")
def button_admin_panel(message):
    cid = message.chat.id
    uid = message.from_user.id
    cur = get_cursor()
    cur.execute("SELECT access FROM users WHERE id = ?", (uid,))
    row = cur.fetchone()
    if not row:
        client.send_message(cid, "Сначала /start для регистрации!")
        return
    access = row[0]
    if access < 1:
        client.send_message(cid, "⛔ У вас нет доступа!")
        return
    client.send_message(cid, "🔑 Админ-панель:", reply_markup=admin_menu())

@client.message_handler(func=lambda m: m.text == "👥 Список пользователей")
def button_users(message):
    cid = message.chat.id
    uid = message.from_user.id
    cur = get_cursor()
    cur.execute("SELECT access FROM users WHERE id = ?", (uid,))
    row = cur.fetchone()
    if not row or row[0] < 1:
        client.send_message(cid, "⛔ У вас нет доступа!")
        return
    text = "*🗃 | Список всех пользователей:*\n\n"
    idusernumber = 0
    for info in cur.execute("SELECT * FROM users"):
        user_id, nick, cash, access_level, bought = info
        if access_level == 0:
            accessname = 'Пользователь'
        elif access_level == 1:
            accessname = 'Администратор'
        elif access_level == 777:
            accessname = 'Разработчик'
        else:
            accessname = 'Неизвестно'
        idusernumber += 1
        text += (
            f"*{idusernumber}. {user_id} ({nick})*\n"
            f"*💸 | Баланс:* {cash} ₽\n"
            f"*👑 | Уровень доступа:* {accessname}\n"
            f"*✉️ | Профиль:* [{nick}](tg://user?id={user_id})\n\n"
        )
    client.send_message(cid, text, parse_mode='Markdown', reply_markup=admin_menu())

@client.message_handler(func=lambda m: m.text == "➕ Добавить товар")
def button_addbuy(message):
    # Вызываем ваш обработчик /addbuy
    # Если у вас есть функция addbuy_command(message), то используйте её
    client.send_message(message.chat.id, "/addbuy")

@client.message_handler(func=lambda m: m.text == "✏️ Изменить товар")
def button_editbuy(message):
    client.send_message(message.chat.id, "Перехожу к изменению товара (команда /editbuy)")
    client.send_message(message.chat.id, "/editbuy")

@client.message_handler(func=lambda m: m.text == "❌ Удалить товар")
def button_rembuy(message):
    client.send_message(message.chat.id, "Перехожу к удалению товара (команда /rembuy)")
    client.send_message(message.chat.id, "/rembuy")

@client.message_handler(func=lambda m: m.text == "🔙 Выйти из админ-панели")
def button_admin_back(message):
    uid = message.from_user.id
    cur = get_cursor()
    cur.execute("SELECT access FROM users WHERE id = ?", (uid,))
    row = cur.fetchone()
    if not row:
        client.send_message(message.chat.id, "Сначала /start для регистрации!")
        return
    access = row[0]
    client.send_message(message.chat.id, "Выходим из админ-панели", reply_markup=main_menu(access))

client.polling(none_stop=True, interval=0)
