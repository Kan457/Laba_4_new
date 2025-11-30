import logging  # стандартный модуль Python для вывода вспомогательных сообщений
import re  # используется для составления регулярного выражения по списку тегов
import requests  # выполняет HTTP-запросы к API LitRes
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

#===== БОТ =====
TOKEN = "8436005748:AAEJaC4TKd8MOkRJmCkNcT6K_pRUh7z_wOA"

#===== АДРЕС ССЫЛКИ =====
MY_ER = "https://cbr.ru/scripts/XML_daily.asp?date_req=02/03/2002"

bot = Bot(token=TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Привет! Я бот на aiogram!")

@dp.message(Command("question"))
async def cmd_start(message: types.Message):
    await message.answer("Вопрос!")

@dp.message(Command("compare"))
async def cmd_start(message: types.Message):
    await message.answer("Сравнение!")

@dp.message(Command("chart"))
async def cmd_start(message: types.Message):
    await message.answer("График!")