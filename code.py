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
    current_date=str(datetime.date.today())
    with open("data.csv", "r", encoding="utf-8") as fdata:
        reader = csv.DictReader(fdata, delimiter=";", quotechar='"')
        data = [row for row in reader]
    data += [{"date": current_date, "cost": cost, "currency": currency, "product": product, "category": category, "buyer": buyer}]
    with open("data.csv", "w", encoding="utf-8") as fdata:
        writer = csv.DictWriter(fdata, fieldnames=["date", "cost", "currency", "product", "category", "buyer"], delimiter=";", quotechar='"')
        writer.writeheader()
        for row in data:
            writer.writerow(row)


def set_base(st_id, param):
    with open("base.json", "r", encoding="utf-8") as fbase:
        data = json.load(fbase)
    if st_id in data:
        if param[0] == "currency":
            data[st_id][0] = param[1]
            bot.send_message(st_id, text=f'Вы установили валюту "{param[1]}"')
        if param[0] == "category":
            data[st_id][1] = param[1]
            bot.send_message(st_id, text=f'Вы установили категорию "{param[1]}"')
        if param[0] == "buyer":
            data[st_id][2] = param[1]
            bot.send_message(st_id, text=f'Вы установили имя "{param[1]}"')
    else:
        data[st_id] = ["руб", "общий", param[1]]
        bot.send_message(st_id, text=f'Вы установили имя "{param[1]}"')
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
    bot.send_message(message.chat.id, text='Правильная запись сообщения: “<стоимость покупки> <валюта> <наименование покупки> <категория, к которой отнести покупку>” без ковычек, в <> скобки ввести соответстенный параметр. Необязательные параметры: валюта, категория. Если они не указаны, то вместо них вводятся те, что по умолчанию. Их можно изменить функциями /set_currency и /set_category.')


@bot.message_handler(commands=['start'])
def start(message):
    answer = bot.send_message(message.chat.id, text='Добро пожаловать в Телеграмг-бота "кошельковая мышь". Введите имя.')
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
    set_base(str(message.chat.id), ["buyer", message.text])


def wrong_input(message):
    bot.send_message(message.chat.id, text='Неверный ввод.')
    c_message(message)


@bot.message_handler(commands=['get_info'])
def get_info(message):
    answer = bot.send_message(message.chat.id, text='Введите имя, о ком информацию вы хотите узнать.')
    bot.register_next_step_handler(answer, fget_info)


def fget_info(message):
    buyer_chat_id = message.chat.id
    buyer = message.text
    days = 1

    df = pd.read_csv("data.csv", delimiter=";", quotechar='"')
    df = df[df["buyer"] == buyer]

    imin = df["cost"].astype("int64").idxmin()
    imax = df["cost"].astype("int64").idxmax()
    summ = df["cost"].astype("int64").sum()
    mean = round(df["cost"].astype("float64").mean(), 2)

    text = f"Информация за {days} дней:\n\n" \
           f"Самая дешёвая покупка: {df.iloc[imin]['cost']} {df.iloc[imin]['currency']} {df.iloc[imin]['product']}\n" \
           f"Самая дорогая покупка: {df.iloc[imax]['cost']} {df.iloc[imax]['currency']} {df.iloc[imax]['product']}\n" \
           f"Суммарная стоимость покупки: {summ} руб\n" \
           f"Средняя стоимость покупки: {mean} руб"
    
    plt.figure()
    df[['date','cost']].set_index('date').plot(figsize=(8, 9))
    plt.xticks(rotation=45)
    fig = plt.gcf()
    send_pic(buyer_chat_id, fig)

    bot.send_message(buyer_chat_id, text=text)


def send_pic(messid, fig):
    buffer = io.BytesIO()
    fig.savefig(buffer, format='png')
    data = buffer.getvalue()
    base64_image = base64.b64encode(data)
    image_data = base64.b64decode(base64_image)
    bot.send_photo(messid, image_data)


@bot.message_handler(content_types=['text'])
def func(message):
    if message.text == "help":
        c_help(message)
    elif message.text == "message":
        c_message(message)
    elif message.text == "start":
        start(message)
    elif message.text == "set_currency":
        set_currency(message)
    elif message.text == "set_category":
        set_category(message)
    elif message.text == "change_name":
        change_name(message)
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