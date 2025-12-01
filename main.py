import requests
from xml.etree import ElementTree as ET
from datetime import datetime

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

URL = "https://cbr.ru/scripts/XML_daily.asp"

# Валюта, для которой строим помесячный график (можно изменить, например на 'EUR')
DEFAULT_TS_CURRENCY = "USD"


def load_dataset():
    """
    Загружает XML‑датасет с сайта ЦБ РФ и возвращает корневой элемент XML‑дерева.
    """
    response = requests.get(URL)
    response.raise_for_status()
    root = ET.fromstring(response.content)
    return root


def parse_rates(root):
    """
    Преобразует XML‑структуру в список словарей с данными по каждой валюте.
    Возвращаемая структура:
    [
        {
            "id": str,
            "num_code": str,
            "char_code": str,
            "nominal": int,
            "name": str,
            "value": float,
        },
        ...
    ]
    """
    rates = []
    for valute in root.findall("Valute"):
        value_raw = valute.find("Value").text
        nominal_raw = valute.find("Nominal").text

        # защита от возможных проблем с данными
        try:
            value = float(value_raw.replace(",", "."))
            nominal = int(nominal_raw)
        except (ValueError, AttributeError):
            continue

        rate = {
            "id": valute.attrib.get("ID"),
            "num_code": valute.find("NumCode").text,
            "char_code": valute.find("CharCode").text,
            "nominal": nominal,
            "name": valute.find("Name").text,
            "value": value,
        }
        rates.append(rate)
    return rates


def prepare_dataset(rates):
    """
    Подготавливает датасет для дальнейшего исследования.

    Выполняемые шаги:
    - фильтрация заведомо некорректных записей;
    - добавление нормализованного курса за 1 единицу валюты;
    - сортировка по буквенным кодам валют.

    Возвращает новый список словарей с полями:
    id, num_code, char_code, name, nominal, value, rate_per_unit.
    """
    cleaned = []
    for r in rates:
        # отбрасываем записи без кода или имени
        if not r.get("char_code") or not r.get("name"):
            continue
        if r["nominal"] <= 0 or r["value"] <= 0:
            continue

        rate_per_unit = r["value"] / r["nominal"]

        cleaned.append(
            {
                **r,
                "rate_per_unit": rate_per_unit,
            }
        )

    # сортировка по коду валюты для удобства анализа
    cleaned.sort(key=lambda x: x["char_code"])
    return cleaned


def describe_dataset(rates):
    """
    Печатает краткое текстовое описание датасета:
    - общая информация;
    - несколько примеров записей;
    - простая статистика по курсам.
    """
    print("=== ОПИСАНИЕ ДАТАСЕТА ЦБ РФ (XML_daily.asp) ===\n")

    # 1. Общая структура
    print("1. Структура набора данных")
    print(
        "- Каждый элемент <Valute> описывает одну валюту.\n"
        "- Основные поля:\n"
        "  * ID        – внутренний идентификатор записи\n"
        "  * NumCode   – числовой код валюты (по ISO 4217)\n"
        "  * CharCode  – буквенный код валюты (по ISO 4217)\n"
        "  * Nominal   – номинал (за сколько единиц валюты указан курс)\n"
        "  * Name      – русскоязычное название валюты\n"
        "  * Value     – стоимость указанного номинала в российских рублях\n"
    )

    # 2. Общая информация
    print("2. Общая информация по датасету")
    count = len(rates)
    print(f"- Количество валют в выборке: {count}")

    char_codes = sorted({r['char_code'] for r in rates})
    print(f"- Примеры кодов валют (первые 10): {', '.join(char_codes[:10])}")
    print()

    # 3. Примеры записей
    print("3. Примеры записей (первые 5 валют):")
    for r in rates[:5]:
        print(
            f"  {r['char_code']} ({r['name']}) — "
            f"номинал: {r['nominal']}, курс: {r['value']} RUB"
        )
    print()

    # 4. Простейшая статистика по курсам
    print("4. Простейшая статистика по курсам (Value приводится к курсу за 1 единицу валюты)")
    normalized = [
        (r["char_code"], r["name"], r["value"] / r["nominal"]) for r in rates
    ]

    min_rate = min(normalized, key=lambda x: x[2])
    max_rate = max(normalized, key=lambda x: x[2])

    avg_rate = sum(x[2] for x in normalized) / len(normalized)

    print(
        f"- Минимальный курс: {min_rate[0]} ({min_rate[1]}): "
        f"{min_rate[2]:.6f} RUB за 1 единицу"
    )
    print(
        f"- Максимальный курс: {max_rate[0]} ({max_rate[1]}): "
        f"{max_rate[2]:.6f} RUB за 1 единицу"
    )
    print(f"- Средний курс по всем валютам: {avg_rate:.6f} RUB за 1 единицу\n")

    print("=== Конец описания датасета ===")


def visualize_dataset(rates):
    """
    Создает визуализации данных о курсах валют с помощью Matplotlib.
    
    Создаются следующие графики:
    1. Топ-10 самых дорогих валют (по курсу за 1 единицу)
    2. Топ-10 самых дешевых валют (по курсу за 1 единицу)
    3. Гистограмма распределения курсов валют
    4. Общий график всех валют (сортировка по курсу)
    """
    if not rates:
        print("Нет данных для визуализации")
        return
    
    # Используем rate_per_unit если он есть, иначе вычисляем
    rates_with_normalized = []
    for r in rates:
        if 'rate_per_unit' in r:
            rate = r['rate_per_unit']
        else:
            rate = r['value'] / r['nominal']
        rates_with_normalized.append({
            'char_code': r['char_code'],
            'name': r['name'],
            'rate': rate
        })
    
    # Сортировка по курсу
    sorted_rates = sorted(rates_with_normalized, key=lambda x: x['rate'], reverse=True)
    
    # Настройка стиля matplotlib
    try:
        plt.style.use('seaborn-v0_8-darkgrid')
    except OSError:
        try:
            plt.style.use('seaborn-darkgrid')
        except OSError:
            plt.style.use('default')
    
    fig = plt.figure(figsize=(16, 12))
    
    # 1. Топ-10 самых дорогих валют
    ax1 = plt.subplot(2, 2, 1)
    top_10_expensive = sorted_rates[:10]
    codes = [r['char_code'] for r in top_10_expensive]
    values = [r['rate'] for r in top_10_expensive]
    
    bars1 = ax1.barh(codes, values, color='#2ecc71')
    ax1.set_xlabel('Курс (RUB за 1 единицу)', fontsize=10)
    ax1.set_title('Топ-10 самых дорогих валют', fontsize=12, fontweight='bold')
    ax1.grid(axis='x', alpha=0.3)
    
    # Добавляем значения на столбцы
    for i, (bar, val) in enumerate(zip(bars1, values)):
        ax1.text(val, i, f' {val:.2f}', va='center', fontsize=8)
    
    # 2. Топ-10 самых дешевых валют
    ax2 = plt.subplot(2, 2, 2)
    top_10_cheap = sorted_rates[-10:]
    codes_cheap = [r['char_code'] for r in top_10_cheap]
    values_cheap = [r['rate'] for r in top_10_cheap]
    
    bars2 = ax2.barh(codes_cheap, values_cheap, color='#e74c3c')
    ax2.set_xlabel('Курс (RUB за 1 единицу)', fontsize=10)
    ax2.set_title('Топ-10 самых дешевых валют', fontsize=12, fontweight='bold')
    ax2.grid(axis='x', alpha=0.3)
    
    # Добавляем значения на столбцы
    for i, (bar, val) in enumerate(zip(bars2, values_cheap)):
        ax2.text(val, i, f' {val:.4f}', va='center', fontsize=8)
    
    # 3. Гистограмма распределения курсов
    ax3 = plt.subplot(2, 2, 3)
    all_rates = [r['rate'] for r in sorted_rates]
    
    # Используем логарифмическую шкалу для лучшей визуализации
    ax3.hist(all_rates, bins=30, color='#3498db', edgecolor='black', alpha=0.7)
    ax3.set_xlabel('Курс (RUB за 1 единицу)', fontsize=10)
    ax3.set_ylabel('Количество валют', fontsize=10)
    ax3.set_title('Распределение курсов валют', fontsize=12, fontweight='bold')
    ax3.grid(axis='y', alpha=0.3)
    ax3.set_yscale('log')  # Логарифмическая шкала для оси Y
    
    # 4. Общий график всех валют (топ-20 для читаемости)
    ax4 = plt.subplot(2, 2, 4)
    top_20 = sorted_rates[:20]
    codes_all = [r['char_code'] for r in top_20]
    values_all = [r['rate'] for r in top_20]
    
    bars4 = ax4.bar(range(len(codes_all)), values_all, color='#9b59b6', alpha=0.7)
    ax4.set_xticks(range(len(codes_all)))
    ax4.set_xticklabels(codes_all, rotation=45, ha='right', fontsize=8)
    ax4.set_ylabel('Курс (RUB за 1 единицу)', fontsize=10)
    ax4.set_title('Топ-20 валют по курсу', fontsize=12, fontweight='bold')
    ax4.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    
    # Сохранение графика
    plt.savefig('currency_rates_visualization.png', dpi=300, bbox_inches='tight')
    print("\n✅ Графики сохранены в файл 'currency_rates_visualization.png'")
    
    # Показываем графики
    plt.show()


def load_monthly_time_series(char_code: str, months: int = 12) -> pd.DataFrame:
    """
    Загружает помесячный временной ряд для выбранной валюты за указанный
    период (по умолчанию 12 месяцев) и возвращает его в виде DataFrame pandas.

    Для каждой даты берется курс на первое число месяца.
    """
    char_code = char_code.upper()

    today = datetime.today()
    # первое число текущего месяца
    start_month = datetime(today.year, today.month, 1)

    dates = []
    values = []

    for i in range(months):
        # вычисляем i-й месяц назад от текущего
        month_shift = months - 1 - i
        year = start_month.year
        month = start_month.month - month_shift
        while month <= 0:
            month += 12
            year -= 1

        date_obj = datetime(year, month, 1)
        date_str = date_obj.strftime("%d/%m/%Y")

        try:
            resp = requests.get(f"{URL}?date_req={date_str}")
            resp.raise_for_status()
            root = ET.fromstring(resp.content)

            rate_value = None
            nominal_value = None
            for valute in root.findall("Valute"):
                cc = valute.find("CharCode").text
                if cc == char_code:
                    nominal_raw = valute.find("Nominal").text
                    value_raw = valute.find("Value").text
                    nominal_value = int(nominal_raw)
                    rate_value = float(value_raw.replace(",", "."))
                    break

            if rate_value is not None and nominal_value is not None and nominal_value > 0:
                rate_per_unit = rate_value / nominal_value
                dates.append(date_obj)
                values.append(rate_per_unit)
        except Exception as exc:
            # просто пропускаем неудачные запросы
            print(f"Предупреждение: не удалось получить данные за {date_str}: {exc}")
            continue

    df = pd.DataFrame({"date": dates, "rate": values}).set_index("date").sort_index()
    return df


def visualize_currency_time_series(char_code: str = DEFAULT_TS_CURRENCY, months: int = 12):
    """
    Строит график изменения курса выбранной валюты по месяцам и
    проверяет данные с помощью pandas (head(), describe()).
    """
    df = load_monthly_time_series(char_code, months)

    if df.empty:
        print(f"Нет данных для валюты {char_code}")
        return

    print(f"\n=== Временной ряд для валюты {char_code} (помесячно) ===")
    print("\nПервые строки DataFrame:")
    print(df.head())

    print("\nСтатистика по DataFrame (describe):")
    print(df.describe())

    plt.figure(figsize=(10, 5))
    plt.plot(df.index, df["rate"], marker="o", linestyle="-", color="#1abc9c")
    plt.title(f"Динамика курса {char_code} по месяцам", fontsize=14, fontweight="bold")
    plt.xlabel("Месяц")
    plt.ylabel("Курс (RUB за 1 единицу)")
    plt.grid(alpha=0.3)
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()

    filename = f"{char_code}_monthly_timeseries.png"
    plt.savefig(filename, dpi=300, bbox_inches="tight")
    print(f"\n✅ Помесячный график для {char_code} сохранен в файл '{filename}'")

    plt.show()


def main():
    """
    Основная функция:
    1) загружает XML‑датасет ЦБ РФ;
    2) преобразует его в удобную структуру;
    3) выводит текстовое описание и простую статистику.
    """
    root = load_dataset()
    raw_rates = parse_rates(root)

    # подготовка датасета к исследованию
    prepared_rates = prepare_dataset(raw_rates)

    # можно описывать уже подготовленный датасет
    describe_dataset(prepared_rates)
    
    # визуализация данных (общий обзор)
    print("\n📊 Создание визуализаций общего распределения...")
    visualize_dataset(prepared_rates)

    # визуализация помесячного временного ряда выбранной валюты
    print(f"\n📈 Построение помесячного графика для валюты {DEFAULT_TS_CURRENCY}...")
    visualize_currency_time_series(DEFAULT_TS_CURRENCY, months=12)


if __name__ == "__main__":
    main()


