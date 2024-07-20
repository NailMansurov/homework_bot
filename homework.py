from http.client import OK
import logging
import os
import requests
import sys
import time

from dotenv import load_dotenv
from telebot import TeleBot

import exceptions

load_dotenv()

PRACTICUM_TOKEN = os.getenv('TOKEN')
TELEGRAM_TOKEN = os.getenv('MY_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('MY_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s, %(levelname)s, %(message)s'
)
logging.StreamHandler(sys.stdout)
logger = logging.getLogger(__name__)


def check_tokens():
    """Проверка доступности переменных оружения."""
    environment_variables = (PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)
    for variable in environment_variables:
        if variable:
            continue
        else:
            logging.critical(
                f'Отсутствует обязательная переменная окружения {variable}'
            )
            return False
    return True


def send_message(bot, message):
    """Отправка сообщения в Telegram-чат."""
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message,
        )
        logging.debug('Сообщение отправлено')
        return True
    except Exception as error:
        logging.error(f'Ошибка {error} при отправке сообщения')
        return False


def get_api_answer(timestamp):
    """Запрос к эндпоинту API-сервиса Яндекс Практикум."""
    try:
        homework_statuses = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params={'from_date': timestamp}
        )
    except requests.RequestException as error:
        return logging.error(
            f'Недоступность эндпоинта Яндекс Практикум, ошибка {error}'
        )
    if homework_statuses.status_code != OK:
        raise exceptions.HTTPStatusIsNotOK(
            logging.error('Сбой при запросе к эндпоинту Яндекс Практикум')
        )
    return homework_statuses.json()


def check_response(response):
    """Проверка ответа API на соответствие документации."""
    if not isinstance(response, dict):
        raise TypeError(logging.error('Ответ не является словарем dict'))
    if 'homeworks' not in response:
        raise KeyError(logging.error('Ответ не содержит homeworks'))
    if not isinstance(response['homeworks'], list):
        raise TypeError(logging.error('Ответ не является списком list'))


def parse_status(homework):
    """Извлечение статуса работы."""
    try:
        homework_name = homework['homework_name']
        status = homework.get('status')
    except KeyError:
        raise KeyError(logging.error('Отсутсвует ключ homework_name'))
    if status is None:
        raise ValueError(
            logging.error(f'Домашняя работа {homework_name} не имеет статуса')
        )
    elif status not in HOMEWORK_VERDICTS:
        raise ValueError(
            logging.error(
                f'Домашняя работа {homework_name} '
                f'имеет неактуальный статус {status}'
            )
        )
    verdict = HOMEWORK_VERDICTS[status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        sys.exit()

    # Создаем объект класса бота
    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())

    status = 'send'

    while True:
        try:
            response = get_api_answer(timestamp)
            check_response(response)
            homeworks = response['homeworks']
            if not homeworks:
                logging.debug('Нет изменеий статуса')
            else:
                last_homework = homeworks[0]
                new_status = last_homework['status']
                if new_status != status:
                    message = parse_status(last_homework)
                    if send_message(bot, message):
                        status = new_status
                    else:
                        logging.error('Ошибка при отправке сообщения')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
