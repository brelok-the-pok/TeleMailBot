import config
import time
import logging
import re
import smtplib
import ssl
import json

from multiprocessing import Pool
from aiogram import Bot, Dispatcher, executor, types
from pathlib import Path

id = 0
logging.basicConfig(level=logging.INFO)

bot = Bot(token=config.TOKEN)
dp = Dispatcher(bot)


def login():
    smtp_server = "smtp.gmail.com"
    port = 587  # For starttls
    sender_email = config.BOTMAIL
    password = config.TOKEN

    message = """\
    Subject: Hi there

    This message is sent from Python."""

    # Create a secure SSL context
    context = ssl.create_default_context()

    # Try to log in to server and send email
    try:
        config.SERVER = smtplib.SMTP(smtp_server, port)
        config.SERVER.ehlo()  # Can be omitted
        config.SERVER.starttls(context=context)  # Secure the connection
        config.SERVER.ehlo()  # Can be omitted
        config.SERVER.login(sender_email, password)
    except Exception as e:
        # Print any error messages to stdout
        print(e)
    # finally:
    #     server.quit()


def add_mail_to_list(mails_recipient, mail_text, mail_theme, mail_send_in):
    global id
    seconds_to_wait = int(mail_send_in.split(":")[1]) * 60
    seconds_to_wait += int(mail_send_in.split(":")[0]) * 60 * 60

    path = Path('mails.json')
    data = json.loads(path.read_text(encoding='utf-8'))
    data[id] = [mails_recipient, mail_text, mail_theme, seconds_to_wait]
    path.write_text(json.dumps(data), encoding='utf-8')

    id += 1


def send_mail(mails_recipient, mail_text, mail_theme):
    if mail_theme == 'Без темы':
        mail_theme = ''

    message = """\
    {}

    {}""".format(mail_theme, mail_text)
    message = message.encode()
    for mail in mails_recipient:
        config.SERVER.sendmail(config.BOTMAIL, mail, message)


def check_mails(mails_recipients):
    res = []
    mails_recipients = mails_recipients.replace('[', '')
    mails_recipients = mails_recipients.replace(']', '')
    mails_recipients = mails_recipients.split(',')
    reg_for_mails = '[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,4}'
    for mail in mails_recipients:
        if re.search(reg_for_mails, mail) is not None:
            res.append(mail.strip())
    return res


async def check_comands(message):
    answer = ''
    help_answer = 'Для отпавки письма введите следующую команду:\n' \
                  '/send [ivan@mail.ru] "Текст письма"\n' \
                  'В данном случае письмо отправится на почту ivan@mail.ru с текстом Текст письма\n' \
                  'Если вы хотите отправить письмо на несколько ящиков, то через запятую введите их, вот так:\n' \
                  '/send [ivan1@mail.ru, ivan2@mail.ru, ivan3@mail.ru] "Текст письма\n' \
                  'Если вы хотите отправить пиьсмо через какое-то время, то укажите это в команде вот так:\n' \
                  '/send [ivan@mail.ru] "Текст письма" 10:15\n' \
                  'Данно письмо будет отправлено через 10 часов 15 минут' \
                  'В письме можно указать тему, тема указывается после текста письма, если не указано через сколько' \
                  ' отпарвлять письмо, либо после метки времени, если указано\n' \
                  '/send [ivan@mail.ru] "Текст письма" 10:15 Тема письма\n' \
                  'либо\n' \
                  '/send [ivan@mail.ru] "Текст письма" Тема письма\n'
    message_text = message.text

    if '/help' in message_text:
        await message.answer(help_answer)
        print(help_answer)
        return

    print(message_text)
    reg = '\/send\s*(\[.*\])\s*(".*")\s*(\d\d:\d\d){0,1}\s*(.*)'
    result = re.search(reg, message_text)
    if result is not None:
        mails_recipients = check_mails(result[1])
        mail_text = result[2]
        mail_text = mail_text[1:len(mail_text) - 1]
        mail_send_in = result[3]
        mail_theme = result[4]

        if len(mails_recipients) != 0:
            answer += 'Письмо будет отправлено следующим получателям:\n'
            for mail in mails_recipients:
                answer += '{}\n'.format(mail)
            if mail_send_in is not None:
                hour = mail_send_in.split(':')[0]
                minute = mail_send_in.split(':')[1]
                answer += "Письмо будет отправлено через {} часов и {} минут\n".format(hour, minute)
                add_mail_to_list(mails_recipients, mail_text, mail_theme, mail_send_in)
            else:
                answer += "Письмо будет отправлено прямо сейчас\n"
                add_mail_to_list(mails_recipients, mail_text, mail_theme, '00:00')
            if mail_theme is not None and mail_theme != '':
                answer += "Письмо будет отправлено со следующей темой '{}'\n".format(mail_theme)
            else:
                answer += "Письмо будет отправлено без темы\n"

            answer += 'Текст письма:\n{}'.format(mail_text)
        else:
            answer = 'Неверный формат почты\n'
    else:
        answer = 'Команда введена неверно, введите /help для помощи\n'

    print(answer)
    await message.answer(answer)


@dp.message_handler()
async def echo(message: types.message):
    await check_comands(message)


def check_time():
    while True:
        print('ам ин')
        path = Path('mails.json')
        data = json.loads(path.read_text(encoding='utf-8'))
        mails = {}

        for key in data.keys():
            if data[key][3] <= 0:
                print(f'Письмо {key} отправлено')
                send_mail(data[key][0], data[key][1], data[key][2])
            else:
                data[key][3] -= 10
                print(f'Письмо {key} ожидает ещё {data[key][3]}')
                mails[key] = data[key]
        if len(data.keys()) > 0:
            path.write_text(json.dumps(mails), encoding='utf-8')
        time.sleep(10)


if __name__ == '__main__':
    pool = Pool(processes=1)
    pool.apply(login)
    pool.apply_async(check_time)

    executor.start_polling(dp, skip_updates=True)
