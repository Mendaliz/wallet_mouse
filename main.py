from config import TOKEN
import telebot

import pandas as pd
import matplotlib.pyplot as plt
import io
import base64

import json
import csv
import datetime

bot = telebot.TeleBot(TOKEN)


def add_to_json(cost, product, currency, category, buyer):
    current_date = str(datetime.date.today())
    with open("data.csv", "r", encoding="utf-8") as fdata:
        reader = csv.DictReader(fdata, delimiter=";", quotechar='"')
        data = [row for row in reader]
    data += [{"date": current_date, "cost": cost, "currency": currency, "product": product, "category": category,
              "buyer": buyer}]
    with open("data.csv", "w", encoding="utf-8") as fdata:
        writer = csv.DictWriter(fdata, fieldnames=["date", "cost", "currency", "product", "category", "buyer"],
                                delimiter=";", quotechar='"')
        writer.writeheader()
        for row in data:
            writer.writerow(row)


def set_base(st_id, param):
    with open("base.json", "r", encoding="utf-8") as fbase:
        data = json.load(fbase)
    if st_id in data:
        if param[0] == "currency":
            data[st_id][0] = param[1]
            bot.send_message(st_id, text=f'Вы установили валюту "{param[1]}".')
        if param[0] == "category":
            data[st_id][1] = param[1]
            bot.send_message(st_id, text=f'Вы установили категорию "{param[1]}".')
        if param[0] == "buyer":
            data[st_id][2] = param[1]
            bot.send_message(st_id, text=f'Вы установили имя "{param[1]}".')
    else:
        data[st_id] = ["руб", "общий", param[1]]
        bot.send_message(st_id, text=f'Вы установили имя "{param[1]}".')
    with open("base.json", "w", encoding="utf-8") as fbase:
        json.dump(data, fbase, ensure_ascii=False, indent=2)


def get_base(st_id):
    with open("base.json", "r", encoding="utf-8") as fbase:
        data = json.load(fbase)
    return data[st_id]


@bot.message_handler(commands=['help'])
def c_help(message):
    bot.send_message(message.chat.id, text='Помощь.')


@bot.message_handler(commands=['message'])
def c_message(message):
    bot.send_message(message.chat.id,
                     text='Правильная запись сообщения: “<стоимость покупки> <валюта> <наименование покупки> '
                          '<категория, к которой отнести покупку>” без ковычек, в <> скобки ввести соответстенный '
                          'параметр. Необязательные параметры: валюта, категория. Если они не указаны, то вместо них '
                          'вводятся те, что по умолчанию. Их можно изменить функциями /set_currency и /set_category.')


@bot.message_handler(commands=['start'])
def start(message):
    answer = bot.send_message(message.chat.id,
                              text='Добро пожаловать в Телеграмг-бота "кошельковая мышь". Введите имя.')
    bot.register_next_step_handler(answer, fchange_name)


@bot.message_handler(commands=['set_currency'])
def set_currency(message):
    answer = bot.send_message(message.chat.id, text='Введите новый тип валюты по умолчанию.')
    bot.register_next_step_handler(answer, fset_currency)


def fset_currency(message):
    set_base(str(message.chat.id), ["currency", message.text])


@bot.message_handler(commands=['set_category'])
def set_category(message):
    answer = bot.send_message(message.chat.id, text='Введите новую категорию по умолчанию.')
    bot.register_next_step_handler(answer, fset_category)


def fset_category(message):
    set_base(str(message.chat.id), ["category", message.text])


@bot.message_handler(commands=['change_name'])
def change_name(message):
    answer = bot.send_message(message.chat.id, text='Введите новое имя.')
    bot.register_next_step_handler(answer, fchange_name)


def fchange_name(message):
    with open("base.json") as jsonf:
        data = json.load(jsonf)
    if filter(lambda x: data[x][-1] == message.text, data):
        answer = bot.send_message(message.chat.id, text='Такое имя сейчас используется другим пользоавтелем. '
                                                        'Попробуйте ещё раз')
        bot.register_next_step_handler(answer, fchange_name)
    set_base(str(message.chat.id), ["buyer", message.text])


def wrong_input(message):
    bot.send_message(message.chat.id, text='Неверный ввод.')
    c_message(message)


def get_date(st):
    return [int(i) for i in st.split("-")]


@bot.message_handler(commands=['get_info'])
def get_info(message):
    buyer_chat_id = message.chat.id
    buyer = get_base(str(buyer_chat_id))[-1]
    days = 30
    category = "general"

    if fget_info(message, buyer, days, category) is None:
        return

    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = telebot.types.KeyboardButton("more_info")
    markup.add(btn1)
    answer = bot.send_message(buyer_chat_id,
                              text='Если хотите получить специфичную информацию, введите "more_info".',
                              reply_markup=markup)

    bot.register_next_step_handler(answer, get_more_info)


def fget_info(message, buyer, days, category, max_value=0):
    buyer_chat_id = message.chat.id
    list_days = [str(datetime.date.today() - datetime.timedelta(days=i)) for i in range(days)]

    df = pd.read_csv("data.csv", delimiter=";", quotechar='"')
    df = df[df["buyer"].isin(buyer.split(", "))]
    if df.shape[0] == 0:
        bot.send_message(buyer_chat_id,
                         text=f"Нет информации о {'пользователе' if len(buyer.split(', ')) == 1 else 'пользователях'}.")
        return

    if category != "general":
        df = df[df["category"].isin(category.split(", "))]

    if df.shape[0] == 0:
        bot.send_message(buyer_chat_id,
                         text=f"В {'данной категории' if len(category.split(', ')) == 1 else 'данных категориях'} "
                              f"не было трат.")
        return

    df = df[df["date"].isin(list_days)]

    if df.shape[0] == 0:
        bot.send_message(buyer_chat_id, text=f"За последние {days} дней у вас не было трат.")
        return

    imin = df["cost"].astype("int64").idxmin()
    imax = df["cost"].astype("int64").idxmax()
    summ = df["cost"].astype("int64").sum()
    mean = round(df["cost"].astype("float64").mean(), 2)

    if len(category.split(", ")) == 1:
        text = f"Информация за последние {days} дней в категории '{category}':\n\n" \
               f"Самая дешёвая покупка: {df.iloc[imin]['cost']} {df.iloc[imin]['currency']} " \
               f"{df.iloc[imin]['product']}\n" \
               f"Самая дорогая покупка: {df.iloc[imax]['cost']} {df.iloc[imax]['currency']} " \
               f"{df.iloc[imax]['product']}\n" \
               f"Суммарная стоимость покупок: {summ} руб\n" \
               f"Средняя стоимость покупки: {mean} руб"
    else:
        text = f"Информация за последние {days} дней в категориях '{category}':\n\n" \
               f"Самая дешёвая покупка: {df.iloc[imin]['cost']} {df.iloc[imin]['currency']} " \
               f"{df.iloc[imin]['product']} категории: {df.iloc[imin]['category']}\n" \
               f"Самая дорогая покупка: {df.iloc[imax]['cost']} {df.iloc[imax]['currency']} " \
               f"{df.iloc[imax]['product']} категории: {df.iloc[imin]['category']}\n" \
               f"Суммарная стоимость покупок: {summ} руб\n" \
               f"Средняя стоимость покупки: {mean} руб"
    if max_value:
        text = f"Информация с {datetime.date.today() - datetime.timedelta(days=days)} в " \
               f"{'категории' if len(category.split(', ')) == 1 else 'категориях'} '{category}':\n" \
               + "\n".join(text.split("\n")[1:])

    my_df = pd.DataFrame([{"date": i, "cost": 0, "currency": df["currency"][0], "product": None, "category": None,
                           "buyer": df["buyer"][0]} for i in list_days])
    fin = []
    for i in my_df.values:
        if list(i)[0] in list(df["date"]):
            for j in df[df["date"] == list(i)[0]].values:
                fin.append(j)
        else:
            fin.append(i)
    df = pd.DataFrame(fin, columns=["date", "cost", "currency", "product", "category", "buyer"])

    plt.figure(figsize=(8, 9))
    df = df.groupby(by="date")["cost"].sum().reset_index()
    # df[['date', 'cost']].set_index('date').plot(figsize=(8, 9))
    if max_value:
        df['cost'] = df['cost'].cumsum()

        plt.plot([max_value] * (df.shape[0]), color="red")
    plt.plot(df['date'], df['cost'])
    plt.xticks(rotation=90)
    fig = plt.gcf()
    send_pic(buyer_chat_id, fig)

    bot.send_message(buyer_chat_id, text=text)
    return True


@bot.message_handler(commands=['get_more_info'])
def get_more_info(message):
    text_message = message.text

    if text_message not in "/more_info":
        func(message)
        return

    answer = bot.send_message(message.chat.id, text="Введите имя(-ена) пользователя(-ей), о ком "
                                                    "Вы хотите узнать информацию (через запятую и пробел).")
    bot.register_next_step_handler(answer, get_name)


def get_name(message):
    buyer = message.text

    answer = bot.send_message(message.chat.id, text="Введите за сколько дней вы хотите получить информацию.")
    bot.register_next_step_handler(answer, get_days, buyer)


def get_days(message, buyer):
    days = int(message.text)

    answer = bot.send_message(message.chat.id, text="Введите категорию(-ии), по которой(-ым) "
                                                    "Вы хотите получить информацию (через запятую и пробел).")
    bot.register_next_step_handler(answer, get_category, buyer, days)


def get_category(message, buyer, days):
    category = message.text

    fget_info(message, buyer, days, category)


def check_alerts():
    with open("alerts.csv", "r", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile, delimiter=";")
        data = list(reader)
    fin = []
    for i in data:
        if datetime.datetime.strptime(i["date_finish"], "%Y-%m-%d") >= datetime.datetime.now():
            fin.append(i)
    with open("alerts.csv", "w", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=list(data[0].keys()), delimiter=";")
        writer.writeheader()
        writer.writerows(fin)


@bot.message_handler(commands=["alerts"])
def alerts(message):
    check_alerts()

    df = pd.read_csv("alerts.csv", delimiter=";", quotechar='"')
    bot.send_message(message.chat.id, text="У Вас зарегестрированы следущие оповещения:")

    df = df[df["buyer"] == get_base(str(message.chat.id))[-1]]

    for i in range(len(df)):
        bot.send_message(message.chat.id, f"{i + 1}. Ограничение на {df.iloc[i]['max_value']} {df.iloc[i]['currency']} "
                                          f"в категории '{df.iloc[i]['category']}' до {df.iloc[i]['date_finish']}")

    answer = bot.send_message(message.chat.id, text='Если хотите получить специфичную информацию об оповещении, '
                                                    'введите его номер.')

    bot.register_next_step_handler(answer, get_more_alert_info)


"""1. Ограничение на 800 руб в категории 'еда' до 2024-03-22

date_start;date_finish;max_value;currency;category;buyer
2024-03-20;2024-03-22;800;руб;еда;Дима
"""


def get_more_alert_info(message):

    if message.text.isdigit() is False:
        func(message)
        return
    indx = int(message.text)

    df = pd.read_csv("alerts.csv", delimiter=";")
    df = df[df["buyer"] == get_base(str(message.chat.id))[-1]]
    if indx < 0 or indx - 1 > df.shape[0]:
        answer = bot.send_message(message.chat.id, text='Неверный номер оповещения. Попробуйте ещё раз.')
        bot.register_next_step_handler(answer, get_more_alert_info)
    alert = df.iloc[indx - 1]
    days = (datetime.date.today() - datetime.datetime.strptime(alert["date_start"], "%Y-%m-%d").date()).days
    fget_info(message, alert["buyer"], days, alert["category"], max_value=int(alert['max_value']))


@bot.message_handler(commands=['make_alert'])
def make_alert(message):
    answer = bot.send_message(message.chat.id, text="В какой категории вы хотите сделать оповещение? "
                                                    "(запишите через запятую и пробел)")

    bot.register_next_step_handler(answer, get_alert_category)


def get_alert_category(message):
    category = message.text

    answer = bot.send_message(message.chat.id, text="В какое количество денег вы хотите сделать оповещение?")
    if answer.text.isdigit() is False:
        bot.send_message(message.chat.id, text='Неправильный ввод.')
        bot.register_next_step_handler(message, get_alert_category)
    bot.register_next_step_handler(answer, get_alert_cost, category)


def get_alert_cost(message, category):
    cost = int(message.text)

    answer = bot.send_message(message.chat.id, text="В какой валюте стоимость оповещения?")
    bot.register_next_step_handler(answer, get_alert_currency, category, cost)


def get_alert_currency(message, category, cost):
    currency = message.text

    answer = bot.send_message(message.chat.id, text="До какого числа Вы хотите установить оповещение? \n"
                                                    "Зпаишите в виде: год-месяц-день")
    if answer.text.split('-') != 3 or all([i.isdigit() for i in answer.text.split('-')]) is False:
        bot.send_message(message.chat.id, text='Неправильный ввод.')
        bot.register_next_step_handler(message, get_alert_currency, category, cost)

    try:
        datetime.datetime.strptime(answer.text, "%Y-%m-%d").date()
    except Exception:
        bot.send_message(message.chat.id, text='Неправильный ввод.')
        bot.register_next_step_handler(message, get_alert_currency, category, cost)

    bot.register_next_step_handler(answer, get_alert_date, category, cost, currency)


def get_alert_date(message, category, cost, currency):
    date_finish = message.text

    with open("alerts.csv", "r", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile, delimiter=";")
        data = list(reader)
    data.append({"date_start": datetime.datetime.now().date(), "date_finish": date_finish, "max_value": cost,
                 "currency": currency, "category": category, "buyer": get_base(str(message.chat.id))[-1]})
    with open("alerts.csv", "w", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile,
                                fieldnames=["date_start", "date_finish", "max_value", "currency", "category", "buyer"],
                                delimiter=";")
        writer.writeheader()
        for i in data:
            writer.writerow(i)
    bot.send_message(message.chat.id, text="Оповещение добавлено.")


def send_pic(messid, fig):
    buffer = io.BytesIO()
    fig.savefig(buffer, format='png')
    data = buffer.getvalue()
    base64_image = base64.b64encode(data)
    image_data = base64.b64decode(base64_image)
    bot.send_photo(messid, image_data)


@bot.message_handler(content_types=['text'])
def func(message):
    if message.text in "/help":
        c_help(message)
    elif message.text in "/message":
        c_message(message)
    elif message.text in "/start":
        start(message)
    elif message.text in "/set_currency":
        set_currency(message)
    elif message.text in "/set_category":
        set_category(message)
    elif message.text in "/change_name":
        change_name(message)
    elif message.text in "/get_info":
        get_info(message)
    elif message.text in "/get_more_info":
        get_more_info(message)
    elif message.text in "/alerts":
        alerts(message)
    elif message.text in "/make_alert":
        make_alert(message)
    else:
        st = message.text.split()
        bases = get_base(str(message.chat.id))
        if len(st) == 2:
            add_to_json(st[0], st[1], bases[0], bases[1], bases[2])
            bot.send_message(message.chat.id, text='Информация получена.')
        elif len(st) == 3:
            add_to_json(st[0], st[2], st[1], bases[1], bases[2])
            bot.send_message(message.chat.id, text='Информация получена.')
        elif len(st) == 4:
            add_to_json(st[0], st[2], st[1], st[3], bases[2])
            bot.send_message(message.chat.id, text='Информация получена.')
        else:
            wrong_input(message)


bot.polling()
