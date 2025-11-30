import logging  # стандартный модуль Python для вывода вспомогательных сообщений
import re  # используется для составления регулярного выражения по списку тегов
import requests  # выполняет HTTP-запросы к API LitRes
from datetime import datetime, timedelta
from xml.etree import ElementTree as ET
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import BotCommand, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters.callback_data import CallbackData
import asyncio

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

#===== БОТ =====
TOKEN = "8436005748:AAEJaC4TKd8MOkRJmCkNcT6K_pRUh7z_wOA"

#===== АДРЕС ССЫЛКИ =====
# Базовая ссылка, дата будет добавляться динамически
MY_ER_BASE = "https://cbr.ru/scripts/XML_daily.asp" 

# Переменная для хранения выбранной даты (по умолчанию текущая дата)
selected_date = None

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Callback data для кнопок меню
class MenuCallback(CallbackData, prefix="menu"):
    action: str

# Функция для получения курсов валют
def get_currency_rates(date_str=None):
    """Получает курсы валют с сайта ЦБ РФ"""
    global selected_date
    
    # Если дата не указана, используем сохраненную дату или текущую
    if date_str:
        url = f"{MY_ER_BASE}?date_req={date_str}"
    elif selected_date:
        url = f"{MY_ER_BASE}?date_req={selected_date}"
    else:
        url = MY_ER_BASE
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        root = ET.fromstring(response.content)
        
        rates = {}
        for valute in root.findall('Valute'):
            char_code = valute.find('CharCode').text
            name = valute.find('Name').text
            value = valute.find('Value').text
            nominal = valute.find('Nominal').text
            rates[char_code] = {
                'name': name,
                'value': float(value.replace(',', '.')),
                'nominal': int(nominal)
            }
        return rates
    except Exception as e:
        logger.error(f"Ошибка при получении курсов: {e}")
        return None

# Функция для форматирования курса валюты
def format_currency_rate(rates, code):
    """Форматирует информацию о валюте для вывода"""
    if rates and code in rates:
        currency = rates[code]
        return f"{currency['name']}\n{currency['nominal']} {code} = {currency['value']:.2f} RUB"
    return f"Валюта {code} не найдена"

# Функция для получения списка всех валют
def get_all_currencies_list(rates):
    """Возвращает отформатированный список всех доступных валют"""
    if not rates:
        return "Не удалось получить список валют"
    
    # Сортируем валюты по коду
    sorted_currencies = sorted(rates.keys())
    
    # Разбиваем на группы по 10 валют для удобства чтения
    currency_list = []
    for i in range(0, len(sorted_currencies), 10):
        group = sorted_currencies[i:i+10]
        currency_list.append(", ".join(group))
    
    return "\n".join(currency_list)

# Функция для создания меню с кнопками
def get_menu_keyboard():
    """Создает интерактивное меню с кнопками"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💲💰 Курс валюты", callback_data=MenuCallback(action="question").pack()),
            InlineKeyboardButton(text="📊 Сравнить валюты", callback_data=MenuCallback(action="compare").pack())
        ],
        [
            InlineKeyboardButton(text="📈 График", callback_data=MenuCallback(action="chart").pack()),
            InlineKeyboardButton(text="🗓️ Установить дату", callback_data=MenuCallback(action="date").pack())
        ],
        [
            InlineKeyboardButton(text="🗿 Помощь", callback_data=MenuCallback(action="help").pack())
        ]
    ])
    return keyboard

# Функция для вывода доступных команд
def get_commands_text():
    """Возвращает текст с доступными командами"""
    return (
        "\n\nДоступные команды:\n"
        "/question - получить курс валюты\n"
        "/compare - сравнить курсы валют\n"
        "/chart - показать график курсов\n"
        "/date - установить дату для запросов (формат: ДД/ММ/ГГГГ)\n"
        "/help - помощь"
    )

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Обработчик команды /start"""
    welcome_text = (
        "Привет! Я бот для работы с курсами валют ЦБ РФ.\n\n"
        "💡 Доступные команды:\n\n"
        "💲 /question - Задать вопрос о курсе валюты\n"
        "   Пример: /question USD\n\n"
        "📊 /compare - Сравнить курсы двух валют\n"
        "   Пример: /compare USD EUR\n\n"
        "📈 /chart - Показать график изменения курсов\n"
        "   Пример: /chart USD\n\n"
        "📅 /date - Установить дату для запросов\n"
        "   Пример: /date 02/03/2002\n\n"
        "🗿 /help - Показать справку\n\n"
        "Выберите действие:"
    )
    await message.answer(welcome_text, reply_markup=get_menu_keyboard())

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    """Обработчик команды /help"""
    help_text = (
        "💡 Доступные команды:\n\n"
        "💲 /question - Задать вопрос о курсе валюты\n"
        "   Пример: /question USD\n\n"
        "📊 /compare - Сравнить курсы двух валют\n"
        "   Пример: /compare USD EUR\n\n"
        "📈 /chart - Показать график изменения курсов\n"
        "   Пример: /chart USD\n\n"
        "📅 /date - Установить дату для запросов\n"
        "   Пример: /date 02/03/2002\n\n"
        "🗿 /help - Показать эту справку"
    )
    await message.answer(help_text, reply_markup=get_menu_keyboard())

@dp.message(Command("question"))
async def cmd_question(message: types.Message):
    """Обработчик команды /question"""
    # Получаем аргументы команды
    args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    
    rates = get_currency_rates()
    
    if not args:
        currencies_list = get_all_currencies_list(rates) if rates else "Не удалось загрузить список валют"
        await message.answer(
            f"💲 Введите название валюты (можно без /question)\n"
            f"Пример: USD или /question USD\n\n"
            f"📋 Все доступные валюты:\n{currencies_list}",
            reply_markup=get_menu_keyboard()
        )
        return
    
    currency_code = args[0].upper()
    
    if rates:
        if currency_code in rates:
            result = format_currency_rate(rates, currency_code)
            await message.answer(f"📊 Курс валюты:\n\n{result}", reply_markup=get_menu_keyboard())
        else:
            currencies_list = get_all_currencies_list(rates)
            await message.answer(
                f"👺 Валюта {currency_code} не найдена.\n\n"
                f"📋 Все доступные валюты:\n{currencies_list}",
                reply_markup=get_menu_keyboard()
            )
    else:
        await message.answer(f"👺 Ошибка при получении данных с сайта ЦБ РФ", reply_markup=get_menu_keyboard())

@dp.message(Command("compare"))
async def cmd_compare(message: types.Message):
    """Обработчик команды /compare"""
    args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    
    rates = get_currency_rates()
    
    if len(args) < 2:
        currencies_list = get_all_currencies_list(rates) if rates else "Не удалось загрузить список валют"
        await message.answer(
            f"📊 Сравнение курсов валют\n\n"
            f"Использование: введите две валюты через пробел\n"
            f"Пример: USD EUR или /compare USD EUR\n\n"
            f"📋 Все доступные валюты:\n{currencies_list}",
            reply_markup=get_menu_keyboard()
        )
        return
    
    currency1 = args[0].upper()
    currency2 = args[1].upper()
    
    if rates:
        if currency1 in rates and currency2 in rates:
            rate1 = rates[currency1]
            rate2 = rates[currency2]
            
            # Нормализуем к 1 единице
            normalized1 = rate1['value'] / rate1['nominal']
            normalized2 = rate2['value'] / rate2['nominal']
            
            result = (
                f"📊 Сравнение курсов валют:\n\n"
                f"💵 {currency1}: {normalized1:.4f} RUB\n"
                f"💶 {currency2}: {normalized2:.4f} RUB\n\n"
                f"📈 Соотношение: 1 {currency1} = {normalized1/normalized2:.4f} {currency2}\n"
                f"📉 Соотношение: 1 {currency2} = {normalized2/normalized1:.4f} {currency1}"
            )
            await message.answer(f"{result}", reply_markup=get_menu_keyboard())
        else:
            missing = []
            if currency1 not in rates:
                missing.append(currency1)
            if currency2 not in rates:
                missing.append(currency2)
            currencies_list = get_all_currencies_list(rates)
            await message.answer(
                f"👺 Валюты не найдены: {', '.join(missing)}\n\n"
                f"📋 Все доступные валюты:\n{currencies_list}",
                reply_markup=get_menu_keyboard()
            )
    else:
        await message.answer(f"👺 Ошибка при получении данных с сайта ЦБ РФ", reply_markup=get_menu_keyboard())

@dp.message(Command("date"))
async def cmd_date(message: types.Message):
    """Обработчик команды /date для установки даты"""
    global selected_date
    args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    
    if not args:
        current_date_info = f"Текущая установленная дата: {selected_date}" if selected_date else "Дата не установлена (используется текущая)"
        await message.answer(
            f"📅 Установка даты для запросов курсов валют\n\n"
            f"{current_date_info}\n\n"
            f"Использование: /date <дата>\n"
            f"Формат даты: ДД/ММ/ГГГГ\n"
            f"Пример: /date 02/03/2002\n\n"
            f"Чтобы сбросить дату, используйте: /date reset",
            reply_markup=get_menu_keyboard()
        )
        return
    
    date_input = args[0].lower()
    
    if date_input == "reset":
        selected_date = None
        await message.answer(f"✅🥰 Дата сброшена. Теперь используется текущая дата.", reply_markup=get_menu_keyboard())
        return
    
    # Проверка формата даты ДД/ММ/ГГГГ
    date_pattern = r'^\d{2}/\d{2}/\d{4}$'
    if not re.match(date_pattern, date_input):
        await message.answer(
            f"👺 Неверный формат даты!\n"
            f"Используйте формат: ДД/ММ/ГГГГ\n"
            f"Пример: 02/03/2002",
            reply_markup=get_menu_keyboard()
        )
        return
    
    # Проверка валидности даты
    try:
        day, month, year = date_input.split('/')
        test_date = datetime(int(year), int(month), int(day))
        selected_date = date_input
        await message.answer(f"✅🥰 Дата установлена: {selected_date}", reply_markup=get_menu_keyboard())
    except ValueError:
        await message.answer(f"👺 Неверная дата! Проверьте правильность введенной даты.", reply_markup=get_menu_keyboard())

@dp.message(Command("chart"))
async def cmd_chart(message: types.Message):
    """Обработчик команды /chart"""
    await message.answer(
        f"📈 График изменения курса валюты\n\n"
        f"Использование: /chart <валюта>\n"
        f"Пример: /chart USD\n\n"
        f"Показывает изменение курса за последние 7 дней",
        reply_markup=get_menu_keyboard()
    )

# Обработчик текстовых сообщений (для удобства)
@dp.message()
async def handle_text(message: types.Message):
    """Обработчик текстовых сообщений"""
    text = message.text.strip().upper()
    parts = text.split()
    
    rates = get_currency_rates()
    
    # Если пользователь ввел две валюты через пробел (например: USD EUR)
    if len(parts) == 2 and all(len(part) == 3 and part.isalpha() for part in parts):
        currency1 = parts[0]
        currency2 = parts[1]
        
        if rates:
            if currency1 in rates and currency2 in rates:
                rate1 = rates[currency1]
                rate2 = rates[currency2]
                
                # Нормализуем к 1 единице
                normalized1 = rate1['value'] / rate1['nominal']
                normalized2 = rate2['value'] / rate2['nominal']
                
                result = (
                    f"📊 Сравнение курсов валют:\n\n"
                    f"💵 {currency1}: {normalized1:.4f} RUB\n"
                    f"💶 {currency2}: {normalized2:.4f} RUB\n\n"
                    f"📈 Соотношение: 1 {currency1} = {normalized1/normalized2:.4f} {currency2}\n"
                    f"📉 Соотношение: 1 {currency2} = {normalized2/normalized1:.4f} {currency1}"
                )
                await message.answer(f"{result}", reply_markup=get_menu_keyboard())
            else:
                missing = []
                if currency1 not in rates:
                    missing.append(currency1)
                if currency2 not in rates:
                    missing.append(currency2)
                currencies_list = get_all_currencies_list(rates)
                await message.answer(
                    f"👺 Валюты не найдены: {', '.join(missing)}\n\n"
                    f"📋 Все доступные валюты:\n{currencies_list}",
                    reply_markup=get_menu_keyboard()
                )
        else:
            await message.answer(f"👺 Ошибка при получении данных с сайта ЦБ РФ", reply_markup=get_menu_keyboard())
    
    # Если пользователь просто написал код валюты (например: USD)
    elif len(text) == 3 and text.isalpha():
        if rates and text in rates:
            result = format_currency_rate(rates, text)
            await message.answer(f"📊 Курс валюты:\n\n{result}", reply_markup=get_menu_keyboard())
        else:
            currencies_list = get_all_currencies_list(rates) if rates else "Не удалось загрузить список валют"
            await message.answer(
                f"👺 Валюта {text} не найдена.\n\n"
                f"📋 Все доступные валюты:\n{currencies_list}",
                reply_markup=get_menu_keyboard()
            )
    else:
        await message.answer(
            f"Используйте команды для работы с ботом.\n"
            f"Введите /help для справки.",
            reply_markup=get_menu_keyboard()
        )

# Обработчик callback для кнопок меню
@dp.callback_query(MenuCallback.filter())
async def handle_menu_callback(callback: types.CallbackQuery, callback_data: MenuCallback):
    """Обработчик нажатий на кнопки меню"""
    action = callback_data.action
    
    if action == "question":
        rates = get_currency_rates()
        currencies_list = get_all_currencies_list(rates) if rates else "Не удалось загрузить список валют"
        await callback.message.edit_text(
            f"💲 Введите код валюты (можно без /question)\n"
            f"Пример: USD или /question USD\n\n"
            f"📋 Все доступные валюты:\n{currencies_list}",
            reply_markup=get_menu_keyboard()
        )
    elif action == "compare":
        rates = get_currency_rates()
        currencies_list = get_all_currencies_list(rates) if rates else "Не удалось загрузить список валют"
        await callback.message.edit_text(
            f"📊 Сравнение курсов валют\n\n"
            f"Использование: введите две валюты через пробел\n"
            f"Пример: USD EUR или /compare USD EUR\n\n"
            f"📋 Все доступные валюты:\n{currencies_list}",
            reply_markup=get_menu_keyboard()
        )
    elif action == "chart":
        await callback.message.edit_text(
            f"📈 График изменения курса валюты\n\n"
            f"Использование: /chart <валюта>\n"
            f"Пример: /chart USD\n\n"
            f"Показывает изменение курса за последние 7 дней",
            reply_markup=get_menu_keyboard()
        )
    elif action == "date":
        global selected_date
        current_date_info = f"Текущая установленная дата: {selected_date}" if selected_date else "Дата не установлена (используется текущая)"
        await callback.message.edit_text(
            f"📅 Установка даты для запросов курсов валют\n\n"
            f"{current_date_info}\n\n"
            f"Использование: /date <дата>\n"
            f"Формат даты: ДД/ММ/ГГГГ\n"
            f"Пример: /date 02/03/2002\n\n"
            f"Чтобы сбросить дату, используйте: /date reset",
            reply_markup=get_menu_keyboard()
        )
    elif action == "help":
        help_text = (
            "💡 Доступные команды:\n\n"
            "💲 /question - Задать вопрос о курсе валюты\n"
            "   Пример: /question USD\n\n"
            "📊 /compare - Сравнить курсы двух валют\n"
            "   Пример: /compare USD EUR\n\n"
            "📈 /chart - Показать график изменения курсов\n"
            "   Пример: /chart USD\n\n"
            "📅 /date - Установить дату для запросов\n"
            "   Пример: /date 02/03/2002\n\n"
            "🗿 /help - Показать эту справку"
        )
        await callback.message.edit_text(help_text, reply_markup=get_menu_keyboard())
    
    await callback.answer()

# Функция для установки команд бота
async def set_bot_commands():
    """Устанавливает список команд бота для автодополнения"""
    commands = [
        BotCommand(command="start", description="Начать работу с ботом"),
        BotCommand(command="question", description="Получить курс валюты"),
        BotCommand(command="compare", description="Сравнить курсы валют"),
        BotCommand(command="chart", description="Показать график курсов"),
        BotCommand(command="date", description="Установить дату для запросов"),
        BotCommand(command="help", description="Помощь"),
    ]
    await bot.set_my_commands(commands)
    logger.info("Команды бота установлены")

# Запуск бота
async def main():
    """Главная функция для запуска бота"""
    await set_bot_commands()
    logger.info("Бот запущен")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())