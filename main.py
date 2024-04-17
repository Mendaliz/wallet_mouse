from config import TOKEN
# import pip
# pip.main(['install', 'pytelegrambotapi'])
import telebot

import pandas as pd
import matplotlib.pyplot as plt
import os
import io
import base64

import json
import csv
import datetime

bot = telebot.TeleBot(TOKEN)


def add_to_json(cost, product, currency, category, buyer, message=""):
    product = product.lower()
    currency = currency.lower()
    category = category.lower()
    current_date = str(datetime.date.today())
    with open("data.csv", "r", encoding="utf-8") as fdata:
        reader = csv.DictReader(fdata, delimiter=";", quotechar='"')
        data = [row for row in reader]
    data += [{"date": current_date, "cost": cost, "currency": currency, "product": product, "category": category,
              "buyer": int(buyer)}]
    with open("data.csv", "w", encoding="utf-8") as fdata:
        writer = csv.DictWriter(fdata, fieldnames=["date", "cost", "currency", "product", "category", "buyer"],
                                delimiter=";", quotechar='"')
        writer.writeheader()
        for row in data:
            writer.writerow(row)
    check_alerts(message, int(buyer), category)


def set_base(st_id, param):
    with open("base.json", "r", encoding="utf-8") as fbase:
        base = json.load(fbase)
    if st_id in base:
        if param[0] == "currency":
            base[st_id]["chosen_currency"] = param[1]
            bot.send_message(st_id, text=f'Вы установили валюту "{param[1]}".',
                             reply_markup=telebot.types.ReplyKeyboardRemove())
        if param[0] == "category":
            base[st_id]["chosen_category"] = param[1]
            bot.send_message(st_id, text=f'Вы установили категорию "{param[1]}".',
                             reply_markup=telebot.types.ReplyKeyboardRemove())
        if param[0] == "buyer":
            base[st_id]["name"] = param[1]
            bot.send_message(st_id, text=f'Вы установили имя "{param[1]}".',
                             reply_markup=telebot.types.ReplyKeyboardRemove())
    else:
        base[st_id] = {"chosen_currency": "руб", "currencies": ["руб"], "chosen_category": "все",
                       "categories": ["все"], "name": param[1], "ident": str(len(base))}
        bot.send_message(st_id, text=f'Вы установили имя "{param[1]}".')
    with open("base.json", "w", encoding="utf-8") as fbase:
        json.dump(base, fbase, ensure_ascii=False, indent=2)


def get_base(st_id):
    with open("base.json", "r", encoding="utf-8") as fbase:
        data = json.load(fbase)
    return data[st_id]


@bot.message_handler(commands=['help'])
def c_help(message):
    bot.send_message(message.chat.id, text='Чтобы получить информацию о способах ввода информации используйте функцию '
                                           '/message.\n'
                                           'Чтобы получить информацию о введенных данных используйте функцию '
                                           '/get_info\n'
                                           'Чтобы получить информацию об оповещениях используйте функцию /alerts')


@bot.message_handler(commands=['message'])
def c_message(message):
    bot.send_message(message.chat.id,
                     text='Правильная запись сообщения: “<стоимость покупки> <валюта> <наименование покупки> '
                          '<категория, к которой отнести покупку>” без ковычек, в <> скобки ввести соответстенный '
                          'параметр. Необязательные параметры: валюта, категория. Если они не указаны, то вместо них '
                          'вводятся те, что по умолчанию. Их можно выбрать из списка функциями '
                          '/set_currency и /set_category. \n'
                          'Списки можно посмотреть функцией /lists, '
                          'изменить функциями /add_currency, /del_currency, /add_category, /del_category.')


@bot.message_handler(commands=['lists'])
def show_lists(message):
    bot.send_message(message.chat.id, text="Список доступных валют:\n" +
                                           '\n'.join(get_base(str(message.chat.id))['currencies']) +
                                           "\n\nВалюта по умолчанию:\n" +
                                           get_base(str(message.chat.id))["chosen_currency"])
    bot.send_message(message.chat.id, text="Список доступных категорий:\n" +
                                           '\n'.join(get_base(str(message.chat.id))['categories']) +
                                           "\n\nКатегория по умолчанию:\n" +
                                           get_base(str(message.chat.id))["chosen_category"])


@bot.message_handler(commands=['start'])
def start(message):
    answer = bot.send_message(message.chat.id,
                              text='Добро пожаловать в Телеграмг-бота "кошельковая мышь". Введите имя.')
    bot.register_next_step_handler(answer, fchange_name)


@bot.message_handler(commands=['add_currency'])
def add_currency(message):
    answer = bot.send_message(message.chat.id, text='Введите новую валюту.')
    bot.register_next_step_handler(answer, fadd_currency)


def fadd_currency(message):
    with open("base.json", "r", encoding="utf-8") as fbase:
        base = json.load(fbase)
    base[str(message.chat.id)]["currencies"] += [message.text.lower()]
    with open("base.json", "w", encoding="utf-8") as fbase:
        json.dump(base, fbase, ensure_ascii=False, indent=2)
    bot.send_message(message.chat.id, text=f'Валюта "{message.text.lower()}" сохранена.')


@bot.message_handler(commands=['del_currency'])
def del_currency(message):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for curr in get_base(str(message.chat.id))["currencies"]:
        btn = telebot.types.KeyboardButton(curr)
        markup.add(btn)
    answer = bot.send_message(message.chat.id,
                              text='Выберите валюту, которую хотите удалить.',
                              reply_markup=markup)

    bot.register_next_step_handler(answer, fget_to_change_curr)


def fget_to_change_curr(message):
    if message.text.lower() not in get_base(str(message.chat.id))["currencies"]:
        bot.send_message(message.chat.id, text="Неверный ввод, попробуй ещё раз.")
        del_currency(message)
        return
    to_del = message.text.lower()
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for curr in get_base(str(message.chat.id))["currencies"]:
        btn = telebot.types.KeyboardButton(curr)
        markup.add(btn)
    answer = bot.send_message(message.chat.id,
                              text='Выберите валюту, на которую хотите заменить эту валютув в сохраненных данных.',
                              reply_markup=markup)

    bot.register_next_step_handler(answer, fdel_currency, to_del)


def fdel_currency(message, to_del):
    if message.text.lower() not in get_base(str(message.chat.id))["currencies"] or message.text == to_del:
        bot.send_message(message.chat.id, text="Неверный ввод, попробуй ещё раз.")
        del_currency(message)
        return
    with open("base.json", "r", encoding="utf-8") as fbase:
        base = json.load(fbase)
    base[str(message.chat.id)]["currencies"].remove(to_del)
    with open("base.json", "w", encoding="utf-8") as fbase:
        json.dump(base, fbase, ensure_ascii=False, indent=2)
    bot.send_message(message.chat.id, text=f'Валюта "{to_del}" удалена.',
                     reply_markup=telebot.types.ReplyKeyboardRemove())

    df = pd.read_csv("data.csv", delimiter=";", quotechar='"')
    if df[df["currency"] == to_del].shape[0] == 0:
        return
    df.loc[df["currency"] == to_del, "currency"] = message.text.lower()
    df.to_csv('data.csv', index=False)


@bot.message_handler(commands=['set_currency'])
def set_currency(message):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for curr in get_base(str(message.chat.id))["currencies"]:
        btn = telebot.types.KeyboardButton(curr)
        markup.add(btn)
    answer = bot.send_message(message.chat.id,
                              text='Выберите новую валюту по умолчанию.',
                              reply_markup=markup)

    bot.register_next_step_handler(answer, fset_currency)


def fset_currency(message):
    if message.text.lower() not in get_base(str(message.chat.id))["currencies"]:
        bot.send_message(message.chat.id, text="Неверный ввод, попробуй ещё раз.")
        set_currency(message)
        return
    set_base(str(message.chat.id), ["currency", message.text.lower()])


@bot.message_handler(commands=['add_category'])
def add_category(message):
    answer = bot.send_message(message.chat.id, text='Введите новую категорию.')
    bot.register_next_step_handler(answer, fadd_category)


def fadd_category(message):
    with open("base.json", "r", encoding="utf-8") as fbase:
        base = json.load(fbase)
    base[str(message.chat.id)]["categories"] += [message.text.lower()]
    with open("base.json", "w", encoding="utf-8") as fbase:
        json.dump(base, fbase, ensure_ascii=False, indent=2)
    bot.send_message(message.chat.id, text=f'Категория "{message.text.lower()}" сохранена.')


@bot.message_handler(commands=['del_category'])
def del_category(message):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    for cat in get_base(str(message.chat.id))["categories"]:
        btn = telebot.types.KeyboardButton(cat)
        markup.add(btn)
    answer = bot.send_message(message.chat.id,
                              text='Выберите категорию, которую хотите удалить.',
                              reply_markup=markup)

    bot.register_next_step_handler(answer, fget_to_change_cat)


def fget_to_change_cat(message):
    if message.text.lower() not in get_base(str(message.chat.id))["categories"]:
        bot.send_message(message.chat.id, text="Неверный ввод, попробуй ещё раз.")
        del_category(message)
        return
    to_del = message.text.lower()
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    for curr in get_base(str(message.chat.id))["categories"]:
        btn = telebot.types.KeyboardButton(curr)
        markup.add(btn)
    answer = bot.send_message(message.chat.id,
                              text='Выберите категорию, на которую хотите заменить эту категрию в сохраненных данных.',
                              reply_markup=markup)

    bot.register_next_step_handler(answer, fdel_category, to_del)


def fdel_category(message, to_del):
    if message.text.lower() not in get_base(str(message.chat.id))["categories"] or message.text == to_del:
        bot.send_message(message.chat.id, text="Неверный ввод, попробуй ещё раз.")
        del_category(message)
        return
    with open("base.json", "r", encoding="utf-8") as fbase:
        base = json.load(fbase)
    base[str(message.chat.id)]["categories"].remove(to_del)
    with open("base.json", "w", encoding="utf-8") as fbase:
        json.dump(base, fbase, ensure_ascii=False, indent=2)
    bot.send_message(message.chat.id, text=f'Категория "{to_del}" удалена.',
                     reply_markup=telebot.types.ReplyKeyboardRemove())

    df = pd.read_csv("data.csv", delimiter=";", quotechar='"')
    if df[df["category"] == to_del].shape[0] == 0:
        return
    df.loc[df["category"] == to_del, "category"] = message.text.lower()
    df.to_csv('data.csv', index=False)


@bot.message_handler(commands=['set_category'])
def set_category(message):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for cat in get_base(str(message.chat.id))["categories"]:
        btn = telebot.types.KeyboardButton(cat)
        markup.add(btn)
    answer = bot.send_message(message.chat.id,
                              text='Выберите новую категорию по умолчанию.',
                              reply_markup=markup)

    bot.register_next_step_handler(answer, fset_category)


def fset_category(message):
    if message.text.lower() not in get_base(str(message.chat.id))["categories"]:
        bot.send_message(message.chat.id, text="Неверный ввод, попробуй ещё раз.")
        set_category(message)
        return
    set_base(str(message.chat.id), ["category", message.text.lower()])


@bot.message_handler(commands=['change_name'])
def change_name(message):
    answer = bot.send_message(message.chat.id, text='Введите новое имя.')
    bot.register_next_step_handler(answer, fchange_name)


def fchange_name(message):
    set_base(str(message.chat.id), ["buyer", message.text.lower()])


def wrong_input(message):
    bot.send_message(message.chat.id, text='Неверный ввод.')
    c_message(message)


@bot.message_handler(commands=['get_info'])
def get_info(message):
    buyer_chat_id = message.chat.id
    buyer = int(get_base(str(buyer_chat_id))["ident"])
    days = 30
    category = "все"

    if fget_info(message, buyer, days, category) is None:
        return

    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
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
    df = df[df["buyer"] == buyer]
    if df.shape[0] == 0:
        bot.send_message(buyer_chat_id,
                         text=f"Нет информации о пользователе.")
        return

    if category != "все":
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
               f"Самая дешёвая покупка: {df.loc[imin]['cost']} {df.loc[imin]['currency']} " \
               f"{df.loc[imin]['product']}\n" \
               f"Самая дорогая покупка: {df.loc[imax]['cost']} {df.loc[imax]['currency']} " \
               f"{df.loc[imax]['product']}\n" \
               f"Суммарная стоимость покупок: {summ} руб\n" \
               f"Средняя стоимость покупки: {mean} руб"
    else:
        text = f"Информация за последние {days} дней в категориях '{category}':\n\n" \
               f"Самая дешёвая покупка: {df.loc[imin]['cost']} {df.loc[imin]['currency']} " \
               f"{df.loc[imin]['product']} категории: {df.loc[imin]['category']}\n" \
               f"Самая дорогая покупка: {df.loc[imax]['cost']} {df.loc[imax]['currency']} " \
               f"{df.loc[imax]['product']} категории: {df.loc[imin]['category']}\n" \
               f"Суммарная стоимость покупок: {summ} руб\n" \
               f"Средняя стоимость покупки: {mean} руб"
    if max_value:
        text = f"Информация с {datetime.date.today() - datetime.timedelta(days=days)} в " \
               f"{'категории' if len(category.split(', ')) == 1 else 'категориях'} '{category}':\n" \
               + "\n".join(text.split("\n")[1:])

    my_df = pd.DataFrame([{"date": i, "cost": 0, "currency": df["currency"].iloc[0], "product": None, "category": None,
                           "buyer": df["buyer"].iloc[0]} for i in list_days])
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

    bot.send_message(buyer_chat_id, text=text, reply_markup=telebot.types.ReplyKeyboardRemove())
    return True


@bot.message_handler(commands=['get_more_info'])
def get_more_info(message):
    text_message = message.text.lower()

    if text_message not in "/more_info":
        func(message)
        return

    buyer = int(get_base(str(message.chat.id))["ident"])

    answer = bot.send_message(message.chat.id, text="Введите за сколько дней вы хотите получить информацию.")
    bot.register_next_step_handler(answer, get_days, buyer)


def get_days(message, buyer):
    days = int(message.text)

    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for cat in get_base(str(message.chat.id))["categories"]:
        btn = telebot.types.KeyboardButton(cat)
        markup.add(btn)
    answer = bot.send_message(message.chat.id,
                              text='Выберите категорию, по которой Вы хотите получить информацию.',
                              reply_markup=markup)

    bot.register_next_step_handler(answer, get_category, buyer, days)


def get_category(message, buyer, days):
    category = message.text.lower()
    if message.text.lower() not in get_base(str(message.chat.id))["categories"]:
        bot.send_message(message.chat.id, text="Неверный ввод, попробуй ещё раз.")
        get_days(message, buyer)
        return

    fget_info(message, buyer, days, category)


def check_alerts_time():
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


def check_alerts(message, buyer, category):
    df = pd.read_csv("alerts.csv", delimiter=";", quotechar='"')
    df = df[(df["buyer"] == buyer)]
    for i in range(df.shape[0]):
        alert = df.iloc[i]
        if alert["category"] != category:
            continue
        data = pd.read_csv("data.csv", delimiter=";", quotechar='"')
        data = data[data["date"] >= alert["date_start"]]
        if alert["max_value"] < data[(data["buyer"] == buyer) & (data["category"] == category |
                                                                 category == "все")]['cost'].sum():
            bot.send_message(message.chat.id, text=f"ВНИМАНИЕ!!!\n"
                                                   f"У Вас превышен лимит трат в категории {category}\n"
                                                   f"Ограничение на {alert['max_value']} {alert['currency']}.")
            get_more_alert_info(message, ind=i)
        elif alert["max_value"] * 0.8 <= data[(data["buyer"] == buyer) & (data["category"] == category |
                                                                          category == "все")]['cost'].sum():
            bot.send_message(message.chat.id, text=f"ВНИМАНИЕ!!!\n"
                                                   f"У Вас ПОЧТИ превышен лимит трат в категории {category}\n"
                                                   f"Ограничение на {alert['max_value']} {alert['currency']}.")
            get_more_alert_info(message, ind=i)


@bot.message_handler(commands=["alerts"])
def alerts(message):
    check_alerts_time()

    df = pd.read_csv("alerts.csv", delimiter=";", quotechar='"')
    bot.send_message(message.chat.id, text="У Вас зарегестрированы следущие оповещения:")

    df = df[df["buyer"] == int(get_base(str(message.chat.id))["ident"])]

    for i in range(len(df)):
        bot.send_message(message.chat.id, f"{i + 1}. Ограничение на {df.iloc[i]['max_value']} {df.iloc[i]['currency']} "
                                          f"в категории '{df.iloc[i]['category']}' до {df.iloc[i]['date_finish']}")

    answer = bot.send_message(message.chat.id, text='Если хотите получить специфичную информацию об оповещении, '
                                                    'введите его номер.')

    bot.register_next_step_handler(answer, get_more_alert_info)


"""1. Ограничение на 800 руб в категории 'еда' до 2024-03-22

date_start;date_finish;max_value;currency;category;buyer
2024-03-20;2024-03-22;800;руб;еда;1
"""


def get_more_alert_info(message, ind=-1):

    if message.text.isdigit() is False and ind == -1:
        func(message)
        return
    if ind != -1:
        indx = ind
    else:
        indx = int(message.text) - 1

    df = pd.read_csv("alerts.csv", delimiter=";")
    df = df[df["buyer"] == int(get_base(str(message.chat.id))["ident"])]
    if indx < 0 or indx > df.shape[0]:
        answer = bot.send_message(message.chat.id, text='Неверный номер оповещения. Попробуйте ещё раз.')
        bot.register_next_step_handler(answer, get_more_alert_info)
    alert = df.iloc[indx]
    days = (datetime.date.today() - datetime.datetime.strptime(alert["date_start"], "%Y-%m-%d").date()).days
    fget_info(message, alert["buyer"], days, alert["category"], max_value=int(alert['max_value']))


@bot.message_handler(commands=['make_alert'])
def make_alert(message):
    answer = bot.send_message(message.chat.id, text="В какой категории вы хотите сделать оповещение? "
                                                    "(запишите через запятую и пробел)")
    bot.register_next_step_handler(answer, get_alert_category)


def get_alert_category(message, categ=""):
    if categ:
        category = categ
    else:
        category = message.text.lower()
    answer = bot.send_message(message.chat.id, text="В какое количество денег вы хотите сделать оповещение?")
    bot.register_next_step_handler(answer, get_alert_cost, category)


def get_alert_cost(message, category):
    if message.text.isdigit() is False:
        bot.send_message(message.chat.id, text='Неправильный ввод.')
        get_alert_category(message, categ=category)
    cost = int(message.text)
    answer = bot.send_message(message.chat.id, text="В какой валюте стоимость оповещения?")
    bot.register_next_step_handler(answer, get_alert_currency, category, cost)


def get_alert_currency(message, category, cost, currencic=""):
    if currencic:
        currency = currencic
    else:
        currency = message.text.lower()
    answer = bot.send_message(message.chat.id, text="До какого числа Вы хотите установить оповещение? \n"
                                                    "Зпаишите в виде: год-месяц-день")
    bot.register_next_step_handler(answer, get_alert_date, category, cost, currency)


def get_alert_date(message, category, cost, currency):
    date_finish = message.text.lower()
    if len(date_finish.split('-')) != 3 or all([i.isdigit() for i in date_finish.split('-')]) is False:
        bot.send_message(message.chat.id, text='Неправильный ввод.')
        get_alert_currency(message, category, cost, currencic=currency)
    try:
        datetime.datetime.strptime(date_finish, "%Y-%m-%d").date()
    except Exception:
        bot.send_message(message.chat.id, text='Неправильный ввод.')
        bot.register_next_step_handler(message, get_alert_currency, category, cost)

    with open("alerts.csv", "r", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile, delimiter=";")
        data = list(reader)
    data.append({"date_start": datetime.datetime.now().date(), "date_finish": date_finish, "max_value": cost,
                 "currency": currency, "category": category, "buyer": int(get_base(str(message.chat.id))["ident"])})
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


@bot.message_handler(content_types=['excel_info'])
def send_excel(message):
    df = pd.read_csv("data.csv", delimiter=";", quotechar='"')
    with open("base.json", "r", encoding="utf-8") as jsonf:
        base = json.load(jsonf)
    a = -1
    for i in base:
        a += 1
        df["buyer"] = df["buyer"].replace(a, base[i]["name"])
    df.to_excel("wallet_mouse_data.xlsx", index=False)
    with open("wallet_mouse_data.xlsx", "rb") as xlsxf:
        bot.send_document(message.chat.id, xlsxf)
    os.remove("wallet_mouse_data.xlsx")


@bot.message_handler(content_types=['text'])
def func(message):
    if message.text.lower() in "/help":
        c_help(message)
    elif message.text.lower() in "/message":
        c_message(message)
    elif message.text.lower() in "/lists":
        show_lists(message)
    elif message.text.lower() in "/start":
        start(message)
    elif message.text.lower() in "/add_currency":
        add_currency(message)
    elif message.text.lower() in "/del_currency":
        del_currency(message)
    elif message.text.lower() in "/set_currency":
        set_currency(message)
    elif message.text.lower() in "/add_category":
        add_category(message)
    elif message.text.lower() in "/del_category":
        del_category(message)
    elif message.text.lower() in "/set_category":
        set_category(message)
    elif message.text.lower() in "/change_name":
        change_name(message)
    elif message.text.lower() in "/get_info":
        get_info(message)
    elif message.text.lower() in "/get_more_info":
        get_more_info(message)
    elif message.text.lower() in "/alerts":
        alerts(message)
    elif message.text.lower() in "/make_alert":
        make_alert(message)
    elif message.text.lower() in "/excel_info":
        send_excel(message)
    else:
        st = message.text.lower().split()
        bases = get_base(str(message.chat.id))
        if len(st) == 2:
            add_to_json(st[0], st[1], bases["chosen_currency"], bases["chosen_category"], bases["ident"],
                        message=message)
            bot.send_message(message.chat.id, text=" ".join([st[0], bases["chosen_currency"], st[1],
                                                             bases["chosen_category"]])
                                                   + '. Информация получена.')
        elif len(st) == 3:
            if st[2] not in get_base(str(message.chat.id))["currencies"]:
                bot.send_message(message.chat.id, text="Такой валюты нет в списке.")
                return
            add_to_json(st[0], st[2], st[1], bases["chosen_category"], bases["ident"], message=message)
            bot.send_message(message.chat.id, text=" ".join([st[0], st[2], st[1], bases["chosen_category"]])
                                                   + '. Информация получена.')
        elif len(st) == 4:
            if st[2] not in get_base(str(message.chat.id))["currencies"]:
                bot.send_message(message.chat.id, text="Такой валюты нет в списке.")
                return
            if st[3] not in get_base(str(message.chat.id))["categories"]:
                bot.send_message(message.chat.id, text="Такой категории нет в списке.")
                return
            add_to_json(st[0], st[2], st[1], st[3], bases["ident"], message=message)
            bot.send_message(message.chat.id, text=" ".join([st[0], st[2], st[1], st[3]])
                                                   + '. Информация получена.')
        else:
            wrong_input(message)


bot.polling()
