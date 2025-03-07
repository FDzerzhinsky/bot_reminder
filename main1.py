import datetime
import os
import sqlite3

from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler
from config import API
from BotController import ruWeekdays, ruMonths

# переменная, хранящая текущую функцию, требующую ответа от пользователя
STATE = None

# этапы для ConversationHandler
NAME, DEPARTMENT, BIRTHDATE = range(3)

# функция для инициализации базы данных
def init_db():
    conn = sqlite3.connect('log.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            user_id INTEGER,
            command TEXT
        )
    ''')
    conn.commit()
    conn.close()

    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            department TEXT,
            birthdate TEXT
        )
    ''')
    conn.commit()
    conn.close()

# функция для логирования запросов
def log_request(user_id, command):
    conn = sqlite3.connect('log.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO logs (timestamp, user_id, command)
        VALUES (?, ?, ?)
    ''', (datetime.datetime.now(), user_id, command))
    conn.commit()
    conn.close()

# функция для добавления пользователя в базу данных
def add_user(name, department, birthdate):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO users (name, department, birthdate)
        VALUES (?, ?, ?)
    ''', (name, department, birthdate))
    conn.commit()
    conn.close()

# функция для получения пользователей из базы данных
def get_users():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT name, department, birthdate FROM users')
    users = cursor.fetchall()
    conn.close()
    return users

# функция, которая обрабатывает start
async def start(update, context):
    log_request(update.message.from_user.id, "/start")
    await update.message.reply_text("""

<b>Привет! Я бот, который может помочь тебе с информацией о текущем времени и дате. Вот некоторые команды, которые я понимаю:</b>

<a>/time</a> - текущее время в формате "10:00".
<a>/date</a> - текущая дата.
<a>/day_of_week</a> - на какой день недели приходится введённая дата.
<a>/days_from</a> - сколько дней прошло с введённой даты до сегодняшнего дня.
<a>/days_before</a> - сколько дней осталось до введённой даты, начиная с сегодняшнего дня.
<a>/user</a> - добавить пользователя в базу данных.
<a>/users</a> - вывести таблицу с добавленными пользователями.

Чтобы начать, просто введи одну из команд выше. Если у тебя возникнут вопросы, не стесняйся спрашивать! """,
                                    parse_mode='HTML')

# функция, которая обрабатывает пользовательский ввод
async def get_user_input(update, context):
    global STATE

    if not STATE:
        await update.message.reply_text('Простите, не совсем понимаю, что вам от меня нужно.')
        return

    await STATE(update, context)

# функция, которая возвращает текущее время
async def get_time(update, context):
    log_request(update.message.from_user.id, "/time")
    global STATE
    STATE = None

    current_time = datetime.datetime.now().strftime('%H:%M')
    await update.message.reply_text(f"{current_time}")

# функция, которая возвращает текущую дату
async def get_date(update, context):
    log_request(update.message.from_user.id, "/date")
    global STATE
    STATE = None

    weekday = ruWeekdays[datetime.datetime.now().strftime('%A')]
    month = ruMonths[datetime.datetime.now().strftime("%B")]
    current_date = datetime.datetime.now().strftime(f'{weekday}, %d {month} %Y г.')
    await update.message.reply_text(f"{current_date}")

# функция, которая возвращает по дате название дня недели
async def get_day_of_week(update, context):
    log_request(update.message.from_user.id, "/day_of_week")
    global STATE

    if not STATE:
        STATE = get_day_of_week
        await update.message.reply_text('Введите дату в формате ДД.ММ.ГГГГ:')
        return

    try:
        weekday = ruWeekdays[datetime.datetime.strptime(update.message.text, "%d.%m.%Y").strftime('%A')]
        STATE = None
        await update.message.reply_text(f"День недели для введенной даты - {weekday.lower()}.")
    except ValueError:
        await update.message.reply_text("Неверный формат даты, попробуйте еще раз:")

# функция, которая возвращает по дате количеству дней, прошедших с того момента
async def get_days_from(update, context):
    log_request(update.message.from_user.id, "/days_from")
    global STATE

    if not STATE:
        STATE = get_days_from
        await update.message.reply_text('Введите дату в формате ДД.ММ.ГГГГ:')
        return

    try:
        date = datetime.datetime.strptime(update.message.text, "%d.%m.%Y")
        if datetime.date.today() < date.date():
            await update.message.reply_text("Эта дата не из прошлого!")
            STATE = None
            return

        diff = datetime.date.today() - date.date()

        answer = ''
        if diff.days == 0:
            answer = "Эта дата полностью совпадает с сегодняшней."
        else:
            answer = f"Количество дней, прошедших с введённой даты: {diff.days}"

        STATE = None
        await update.message.reply_text(answer)
    except ValueError:
        await update.message.reply_text("Неверный формат даты, попробуйте еще раз:")

# функция, которая возвращает по дате через какое кол-во дней она будет
async def get_days_before(update, context):
    log_request(update.message.from_user.id, "/days_before")
    global STATE

    if not STATE:
        STATE = get_days_before
        await update.message.reply_text('Введите дату в формате ДД.ММ.ГГГГ:')
        return

    try:
        date = datetime.datetime.strptime(update.message.text, "%d.%м.%Y")

        if datetime.date.today() > date.date():
            await update.message.reply_text("Эта дата не из будущего!")
            STATE = None
            return

        diff = date.date() - datetime.date.today()

        answer = ''
        if diff.days == 0:
            answer = "Эта дата полностью совпадает с сегодняшней!"
        else:
            answer = f"Количество дней до введённой даты: {diff.days}."

        STATE = None
        await update.message.reply_text(answer)
    except ValueError:
        await update.message.reply_text("Неверный формат даты, попробуйте еще раз:")

# функция, которая обрабатывает команду /user
async def user(update, context):
    log_request(update.message.from_user.id, "/user")
    await update.message.reply_text('Введите ваше ФИО:')
    return NAME

# функция для получения ФИО
async def get_name(update, context):
    context.user_data['name'] = update.message.text
    await update.message.reply_text('Введите ваш отдел:')
    return DEPARTMENT

# функция для получения отдела
async def get_department(update, context):
    context.user_data['department'] = update.message.text
    await update.message.reply_text('Введите вашу дату рождения (ДД.ММ.ГГГГ):')
    return BIRTHDATE

# функция для получения даты рождения и добавления пользователя в базу данных
async def get_birthdate(update, context):
    context.user_data['birthdate'] = update.message.text
    add_user(context.user_data['name'], context.user_data['department'], context.user_data['birthdate'])
    await update.message.reply_text('Пользователь успешно добавлен в базу данных!')
    return ConversationHandler.END

# функция для отмены добавления пользователя
async def cancel(update, context):
    await update.message.reply_text('Добавление пользователя отменено.')
    return ConversationHandler.END

# функция, которая обрабатывает команду /users
async def users(update, context):
    log_request(update.message.from_user.id, "/users")
    users = get_users()
    if not users:
        await update.message.reply_text('Пользователи не найдены.')
        return

    response = '<b>Список пользователей:</b>\n\n'
    for user in users:
        response += f'ФИО: {user[0]}\nОтдел: {user[1]}\nДата рождения: {user[2]}\n\n'
    await update.message.reply_text(response, parse_mode='HTML')

def main():
    init_db()
    application = Application.builder().token(API).build()

    # не ожидают ответа
    start_commend_handler = CommandHandler("start", start)
    time_command_handler = CommandHandler("time", get_time)
    date_command_handler = CommandHandler("date", get_date)

    # ожидают ответа
    get_day_of_week_command_handler = CommandHandler("day_of_week", get_day_of_week)
    get_days_from_command_handler = CommandHandler("days_from", get_days_from)
    get_days_before_handler = CommandHandler("days_before", get_days_before)

    # обработчик для команды /user
    user_handler = ConversationHandler(
        entry_points=[CommandHandler('user', user)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            DEPARTMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_department)],
            BIRTHDATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_birthdate)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    # обработчик для команды /users
    users_command_handler = CommandHandler("users", users)

    # универсальный геттер текста
    user_input_handler = MessageHandler(filters.TEXT, get_user_input)

    # хендлеры
    application.add_handler(start_commend_handler)
    application.add_handler(time_command_handler)
    application.add_handler(date_command_handler)
    application.add_handler(get_day_of_week_command_handler)
    application.add_handler(get_days_from_command_handler)
    application.add_handler(get_days_before_handler)
    application.add_handler(user_handler)
    application.add_handler(users_command_handler)

    # геттер пользовательского ввода
    application.add_handler(user_input_handler)

    application.run_polling()

if __name__ == '__main__':
    main()