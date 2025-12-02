# Анализ и визуализация курса доллара США по данным из Excel
import pandas as pd
import os
import warnings
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

warnings.filterwarnings('ignore', category=UserWarning)  # скрываем лишние предупреждения
warnings.filterwarnings('ignore', message='.*Workbook contains no default style.*')

# путь к файлу с данными и загрузка таблицы
script_dir = os.path.dirname(os.path.abspath(__file__))
data_path = os.path.join(script_dir, 'data.xlsx')
df = pd.read_excel(data_path)

print("\n===========================================")
print("📍 АНАЛИЗ ДАННЫХ ИЗ ФАЙЛА 📍")
print("===========================================\n")

print("===========================================")
print("⚙️  Размерность данных:⚙️\n")
print(f"* {df.shape[0]} строк🏴\n* {df.shape[1]} столбцов🏳️")

print("\n===========================================")
print("\n 📑 Названия столбцов и за что они отвечают:📑\n")
for i, col in enumerate(df.columns, 1):
    # короткое описание типа каждого столбца
    if str(col).lower() == 'nominal':
        col_desc = f"Кол-во денег 💸"
    elif pd.api.types.is_numeric_dtype(df[col]):
        col_desc = f"Курс 💹"
    elif pd.api.types.is_datetime64_any_dtype(df[col]):
        col_desc = f"Дата 🗓️"
    else:
        col_desc = f"Наименнование валюты 📝"
    print(f"  {i}. {col} - {col_desc}")

print("\n===========================================")
print("\n✏️   Вид :  ✏️\n")
print(df)
print("\n")

# простые текстовые выводы по датасету
print(" 🎓 ИССЛЕДОВАНИЕ:🎓 \n")
print("⚫ Наминал валют совпадает - 1")
print("⚫ Наименнования валют совпадают - Доллары США")
print("===========================================\n")

# ищем столбец с датой по типу или названию
date_col = None
for col in df.columns:
    if pd.api.types.is_datetime64_any_dtype(df[col]) or "дата" in str(col).lower() or "date" in str(col).lower():
        date_col = col
        break

numeric_cols = df.select_dtypes(include="number").columns
rate_cols = [c for c in numeric_cols if str(c).lower() != "nominal"]

# выбираем первый числовой столбец курса
rate_col = rate_cols[0] if len(rate_cols) > 0 else None

if rate_col is not None and date_col is not None:
    # приводим столбец даты к формату datetime и делаем индексом
    df[date_col] = pd.to_datetime(df[date_col])

    df_month = df.set_index(date_col)

    # усредняем курс по месяцам (MS — начало месяца)
    monthly_rate = df_month[rate_col].resample("MS").mean()

    # строим линейный график динамики курса
    plt.figure(figsize=(14, 6))
    plt.plot(
        monthly_rate.index,
        monthly_rate.values,
        marker="o",
        linestyle="-",
        color="#1f77b4",
        linewidth=2,
        markersize=6,
    )

    # Ось X: первое число каждого месяца, формат ДД.ММ.ГГГГ
    ax = plt.gca()
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d.%m.%Y"))
    plt.xticks(rotation=45)

    plt.xlabel("Месяц")
    plt.ylabel("Курс")
    plt.title(f"Средний курс по месяцам ({rate_col})")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()

