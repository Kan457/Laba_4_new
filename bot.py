import logging
import re
import asyncio

import requests
from datetime import datetime, timedelta
from xml.etree import ElementTree as ET
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import BotCommand, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters.callback_data import CallbackData

# базовая настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


TOKEN = "8436005748:AAEJaC4TKd8MOkRJmCkNcT6K_pRUh7z_wOA"
MY_ER_BASE = "https://cbr.ru/scripts/XML_daily.asp"

# выбранная пользователем дата (если None — берётся текущая)
selected_date = None

# экземпляры бота и диспетчера aiogram
bot = Bot(token=TOKEN)
dp = Dispatcher()

# callback‑данные для inline‑кнопок меню
class MenuCallback(CallbackData, prefix="menu"):
    action: str

# загрузка курсов валют с сайта ЦБ РФ
def get_currency_rates(date_str=None):
    global selected_date
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

# форматирование информации по одной валюте
def format_currency_rate(rates, code):
    if rates and code in rates:
        currency = rates[code]
        return f"{currency['name']}\n{currency['nominal']} {code} = {currency['value']:.2f} RUB"
    return f"Валюта {code} не найдена"

# формирование строки со всеми кодами валют
def get_all_currencies_list(rates):
    if not rates:
        return "Не удалось получить список валют"
    
    sorted_currencies = sorted(rates.keys())
    
    currency_list = []
    for i in range(0, len(sorted_currencies), 10):
        group = sorted_currencies[i:i+10]
        currency_list.append(", ".join(group))
    
    return "\n".join(currency_list)

# формирование списка валют с полными названиями
def get_all_currencies_with_titles(rates):
    if not rates:
        return "Не удалось получить список валют"
    
    sorted_currencies = sorted(rates.items())
    
    currency_list = []
    for code, currency_info in sorted_currencies:
        currency_list.append(f"{code} - {currency_info['name']}")
    
    result_lines = []
    for i in range(0, len(currency_list), 5):
        group = currency_list[i:i+5]
        result_lines.append("\n".join(group))
    
    return "\n\n".join(result_lines)


def get_menu_keyboard():

    """Клавиатура с основными командами бота."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💲 /question - Курс валюты", callback_data=MenuCallback(action="question").pack())
        ],
        [
            InlineKeyboardButton(text="📊 /compare - Сравнить валюты", callback_data=MenuCallback(action="compare").pack())
        ],
        [
            InlineKeyboardButton(text="📅 /date - Установить дату", callback_data=MenuCallback(action="date").pack())
        ],
        [
            InlineKeyboardButton(text="📝 /title - Список всех валют", callback_data=MenuCallback(action="title").pack())
        ],
        [
            InlineKeyboardButton(text="🗿 /help - Помощь", callback_data=MenuCallback(action="help").pack())
        ]
    ])
    return keyboard

def get_commands_text():
    """Текст со списком доступных команд."""
    return (
        "\n\nДоступные команды:\n"
        "/question - получить курс валюты\n"
        "/compare - сравнить курсы валют\n"
        "/date - установить дату для запросов (формат: ДД/ММ/ГГГГ)\n"
        "/title - показать все названия валют\n"
        "/help - помощь"
    )

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Стартовое приветствие и вывод основного меню."""
    welcome_text = (
        "Привет! Я бот для работы с курсами валют ЦБ РФ.\n\n"
        "💡 Доступные команды:\n\n"
        "💲 /question - Задать вопрос о курсе валюты\n"
        "   Пример: /question USD\n\n"
        "📊 /compare - Сравнить курсы двух валют\n"
        "   Пример: /compare USD EUR\n\n"
        "📅 /date - Установить дату для запросов\n"
        "   Пример: /date 02/03/2002\n\n"
        "📝 /title - Показать все названия валют\n\n"
        "🗿 /help - Показать справку\n\n"
        "Выберите действие:"
    )
    await message.answer(welcome_text, reply_markup=get_menu_keyboard())

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    """Вывод краткой справки по командам."""
    help_text = (
        "💡 Доступные команды:\n\n"
        "💲 /question - Задать вопрос о курсе валюты\n"
        "   Пример: /question USD\n\n"
        "📊 /compare - Сравнить курсы двух валют\n"
        "   Пример: /compare USD EUR\n\n"
        "📅 /date - Установить дату для запросов\n"
        "   Пример: /date 02/03/2002\n\n"
        "📝 /title - Показать все названия валют\n\n"
        "🗿 /help - Показать эту справку"
    )
    await message.answer(help_text, reply_markup=get_menu_keyboard())

@dp.message(Command("question"))
async def cmd_question(message: types.Message):
    """Получение курса одной валюты по коду."""
    args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    
    rates = get_currency_rates()
    
    if not args:
        currencies_list = get_all_currencies_list(rates) if rates else "Не удалось загрузить список валют"
        await message.answer(
            f"💲 Введите название валюты (можно без /question)\n"
            f"Пример: USD или /question USD\n\n"
            f"📋 Полный список аббревиатур валют:\n{currencies_list}",
            reply_markup=get_menu_keyboard()
        )
        return
    
    currency_code = args[0].upper()
    
    if rates:
        if currency_code in rates:
            result = format_currency_rate(rates, currency_code)
            currencies_with_titles = get_all_currencies_with_titles(rates)
            await message.answer(
                f"📊 Курс валюты:\n\n{result}\n\n"
                f"📝 Все валюты с полными названиями:\n{currencies_with_titles}",
                reply_markup=get_menu_keyboard()
            )
        else:
            currencies_with_titles = get_all_currencies_with_titles(rates)
            await message.answer(
                f"👺 Валюта {currency_code} не найдена.\n\n"
                f"📝 Все валюты с полными названиями:\n{currencies_with_titles}",
                reply_markup=get_menu_keyboard()
            )
    else:
        await message.answer(f"👺 Ошибка при получении данных с сайта ЦБ РФ", reply_markup=get_menu_keyboard())

@dp.message(Command("compare"))
async def cmd_compare(message: types.Message):
    """Сравнение курсов двух валют."""
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
            
            normalized1 = rate1['value'] / rate1['nominal']
            normalized2 = rate2['value'] / rate2['nominal']
            
            currencies_with_titles = get_all_currencies_with_titles(rates)
            result = (
                f"📊 Сравнение курсов валют:\n\n"
                f"💵 {currency1}: {normalized1:.4f} RUB\n"
                f"💶 {currency2}: {normalized2:.4f} RUB\n\n"
                f"📈 Соотношение: 1 {currency1} = {normalized1/normalized2:.4f} {currency2}\n"
                f"📉 Соотношение: 1 {currency2} = {normalized2/normalized1:.4f} {currency1}\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📝 Все валюты с полными названиями:\n{currencies_with_titles}"
            )
            await message.answer(f"{result}", reply_markup=get_menu_keyboard())
        else:
            missing = []
            if currency1 not in rates:
                missing.append(currency1)
            if currency2 not in rates:
                missing.append(currency2)
            currencies_with_titles = get_all_currencies_with_titles(rates)
            await message.answer(
                f"👺 Валюты не найдены: {', '.join(missing)}\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📝 Все валюты с полными названиями:\n{currencies_with_titles}",
                reply_markup=get_menu_keyboard()
            )
    else:
        await message.answer(f"👺 Ошибка при получении данных с сайта ЦБ РФ", reply_markup=get_menu_keyboard())

@dp.message(Command("date"))
async def cmd_date(message: types.Message):
    """Установка или сброс даты для запросов."""
    global selected_date
    args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    
    if not args:
        current_date_info = f"Текущая установленная дата: {selected_date}" if selected_date else "Дата не установлена (используется текущая)"
        await message.answer(
            f"📅 Установка даты для запросов курсов валют\n\n"
            f"{current_date_info}\n\n"
            f"Использование: /date <дата> или ДД/ММ/ГГГГ\n"
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
    
    date_pattern = r'^\d{2}/\d{2}/\d{4}$'
    if not re.match(date_pattern, date_input):
        await message.answer(
            f"👺 Неверный формат даты!\n"
            f"Используйте формат: ДД/ММ/ГГГГ\n"
            f"Пример: 02/03/2002",
            reply_markup=get_menu_keyboard()
        )
        return
    
    try:
        day, month, year = date_input.split('/')
        test_date = datetime(int(year), int(month), int(day))
        selected_date = date_input
        await message.answer(f"✅🥰 Дата установлена: {selected_date}", reply_markup=get_menu_keyboard())
    except ValueError:
        await message.answer(f"👺 Неверная дата! Проверьте правильность введенной даты.", reply_markup=get_menu_keyboard())

@dp.message(Command("title"))
async def cmd_title(message: types.Message):
    """Вывод всех валют с полными названиями."""
    rates = get_currency_rates()
    
    if rates:
        currencies_with_titles = get_all_currencies_with_titles(rates)
        await message.answer(
            f"📝 Полный список всех валют всех стран\n\n{currencies_with_titles}",
            reply_markup=get_menu_keyboard()
        )
    else:
        await message.answer(f"👺 Ошибка при получении данных с сайта ЦБ РФ", reply_markup=get_menu_keyboard())

@dp.message()
async def handle_text(message: types.Message):
    """Обработка текстовых сообщений без команд."""
    text_original = message.text.strip()
    text = text_original.upper()
    parts = text.split()
    
    rates = get_currency_rates()
    
    date_pattern = r'^\d{2}/\d{2}/\d{4}$'
    if re.match(date_pattern, text_original):
        global selected_date
        date_input = text_original.lower()
        
        try:
            day, month, year = date_input.split('/')
            test_date = datetime(int(year), int(month), int(day))
            selected_date = date_input
            await message.answer(f"✅🥰 Дата установлена: {selected_date}", reply_markup=get_menu_keyboard())
            return
        except ValueError:
            await message.answer(f"👺 Неверная дата! Проверьте правильность введенной даты.", reply_markup=get_menu_keyboard())
            return
    
    if len(parts) == 2 and all(len(part) == 3 and part.isalpha() for part in parts):
        currency1 = parts[0]
        currency2 = parts[1]
        
        if rates:
            if currency1 in rates and currency2 in rates:
                rate1 = rates[currency1]
                rate2 = rates[currency2]
                
                normalized1 = rate1['value'] / rate1['nominal']
                normalized2 = rate2['value'] / rate2['nominal']
                
                currencies_list = get_all_currencies_list(rates)
                result = (
                    f"📊 Сравнение курсов валют:\n\n"
                    f"💵 {currency1}: {normalized1:.4f} RUB\n"
                    f"💶 {currency2}: {normalized2:.4f} RUB\n\n"
                    f"📈 Соотношение: 1 {currency1} = {normalized1/normalized2:.4f} {currency2}\n"
                    f"📉 Соотношение: 1 {currency2} = {normalized2/normalized1:.4f} {currency1}\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"📋 Полный список аббревиатур валют:\n{currencies_list}"
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
    
    elif len(text) == 3 and text.isalpha():
        if rates and text in rates:
            result = format_currency_rate(rates, text)
            currencies_list = get_all_currencies_list(rates)
            await message.answer(
                f"📊 Курс валюты:\n\n{result}\n\n"
                f"📋 Полный список аббревиатур валют:\n{currencies_list}",
                reply_markup=get_menu_keyboard()
            )
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

@dp.callback_query(MenuCallback.filter())
async def handle_menu_callback(callback: types.CallbackQuery, callback_data: MenuCallback):
    """Обработка нажатий на кнопки меню."""
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
    elif action == "date":
        global selected_date
        current_date_info = f"Текущая установленная дата: {selected_date}" if selected_date else "Дата не установлена (используется текущая)"
        await callback.message.edit_text(
            f"📅 Установка даты для запросов курсов валют\n\n"
            f"{current_date_info}\n\n"
            f"Использование: /date <дата> или ДД/ММ/ГГГГ\n"
            f"Формат даты: ДД/ММ/ГГГГ\n"
            f"Пример: /date 02/03/2002\n\n"
            f"Чтобы сбросить дату, используйте: /date reset",
            reply_markup=get_menu_keyboard()
        )
    elif action == "title":
        rates = get_currency_rates()
        if rates:
            currencies_with_titles = get_all_currencies_with_titles(rates)
            await callback.message.edit_text(
                f"📝 Полный список всех валют всех стран\n\n{currencies_with_titles}",
                reply_markup=get_menu_keyboard()
            )
        else:
            await callback.message.edit_text(
                f"👺 Ошибка при получении данных с сайта ЦБ РФ",
                reply_markup=get_menu_keyboard()
            )
    elif action == "help":
        help_text = (
            "💡 Доступные команды:\n\n"
            "💲 /question - Задать вопрос о курсе валюты\n"
            "   Пример: /question USD\n\n"
            "📊 /compare - Сравнить курсы двух валют\n"
            "   Пример: /compare USD EUR\n\n"
            "📅 /date - Установить дату для запросов\n"
            "   Пример: /date 02/03/2002\n\n"
            "📝 /title - Показать все названия валют\n\n"
            "🗿 /help - Показать эту справку"
        )
        await callback.message.edit_text(help_text, reply_markup=get_menu_keyboard())
    
    await callback.answer()

async def set_bot_commands():
    """Регистрация команд бота в интерфейсе Telegram."""
    commands = [
        BotCommand(command="start", description="Начать работу с ботом"),
        BotCommand(command="question", description="Получить курс валюты"),
        BotCommand(command="compare", description="Сравнить курсы валют"),
        BotCommand(command="date", description="Установить дату для запросов"),
        BotCommand(command="title", description="Показать все названия валют"),
        BotCommand(command="help", description="Помощь"),
    ]
    await bot.set_my_commands(commands)
    logger.info("Команды бота установлены")

async def main():
    """Точка входа: регистрация команд и запуск поллинга."""
    await set_bot_commands()
    logger.info("Бот запущен")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())