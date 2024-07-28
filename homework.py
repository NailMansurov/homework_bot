from http import HTTPStatus
import logging
import os
import requests
import sys
import time

from dotenv import load_dotenv
from telebot import apihelper, TeleBot


from exceptions import (
    EmptyHomeworksError,
    EnvironmentEvariablesError,
    HTTPStatusError,
    RequestError,
    SendMessageError
)

load_dotenv()

logger = logging.getLogger(__name__)

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


def check_tokens():
    """Проверка доступности переменных оружения."""
    logger.info('Начата проверка доступности переменных окружения.')
    environment_variables = (
        ('PRACTICUM_TOKEN', PRACTICUM_TOKEN),
        ('TELEGRAM_TOKEN', TELEGRAM_TOKEN),
        ('TELEGRAM_CHAT_ID', TELEGRAM_CHAT_ID)
    )
    no_tokens = []
    for variable, variable_value in environment_variables:
        if variable_value is None:
            no_tokens.append(variable)
    if no_tokens:
        raise EnvironmentEvariablesError(
            f'Отсутствует обязательная переменная окружения {no_tokens}'
        )
    else:
        logger.info(
            'Закончена проверка доступности переменных окружения - успешно.'
        )


def send_message(bot, message):
    """Отправка сообщения в Telegram-чат."""
    try:
        logger.info('Начата отправка сообщения.')
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message,
        )
    except apihelper.ApiException as error:
        raise SendMessageError(f'Ошибка {error} при отправке сообщения')
    else:
        logger.debug('Сообщение отправлено')


def get_api_answer(timestamp):
    """Запрос к эндпоинту API-сервиса Яндекс Практикум."""
    logger.info('Отправка запроса к эндпоинту API-сервиса Яндекс Практикум')
    requests_parameters = {
        'url': ENDPOINT,
        'headers': HEADERS,
        'params': {'from_date': timestamp},
    }
    try:
        homework_statuses = requests.get(**requests_parameters)
    except requests.RequestException as error:
        raise RequestError(
            f'Недоступность эндпоинта Яндекс Практикум, ошибка {error} '
            f'Параметры запроса: {requests_parameters}'
        )
    else:
        logger.info(
            'Запрос отправлен к эндпоинту API-сервиса Яндекс Практикум'
        )
    if homework_statuses.status_code != HTTPStatus.OK:
        raise HTTPStatusError(
            'Сбой при обработке запросе к эндпоинту Яндекс Практикум'
        )
    else:
        logger.info(
            'Успешная обработка запроса '
            'к эндпоинту API-сервиса Яндекс Практикум'
        )
    return homework_statuses.json()


def check_response(response):
    """Проверка ответа API на соответствие документации."""
    logger.info('Проверка ответа API на соответствие документации')
    if not isinstance(response, dict):
        raise TypeError('Ответ не является словарем dict')
    if 'homeworks' not in response:
        raise KeyError('Ответ не содержит homeworks')
    if not isinstance(response['homeworks'], list):
        raise TypeError('Ответ не является списком list')
    homeworks = response['homeworks']
    if not homeworks:
        raise EmptyHomeworksError('Нет домашних работ')
    logger.info(
        'Проверка ответа API на соответствие документации - успешно'
    )
    return homeworks


def parse_status(homework):
    """Извлечение статуса работы."""
    logger.info('Проверка статуса работы')
    if 'homework_name' not in homework:
        raise KeyError('Отсутсвует ключ homework_name')
    if 'status' not in homework:
        raise KeyError('Отсутсвует ключ status')
    homework_name = homework['homework_name']
    status = homework['status']
    if status not in HOMEWORK_VERDICTS:
        raise ValueError(
            f'Домашняя работа {homework_name} '
            f'имеет неактуальный статус {status}'
        )
    verdict = HOMEWORK_VERDICTS[status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    bot = TeleBot(token=TELEGRAM_TOKEN)
    try:
        check_tokens()
    except EnvironmentEvariablesError as error:
        logger.critical(error)
        send_message(bot, error)
        sys.exit()

    timestamp = int(time.time())

    status = ''
    last_message = ''

    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            homework = homeworks[0]
            message = parse_status(homework)
            if status != homework['status']:
                send_message(bot, message)
                status = homework['status']
                logger.debug('Успешная отправка сообщения в Telegram')
            else:
                logger.debug('Статус домашней работы не изменился')
            timestamp = int(time.time())
        except Exception as error:
            logger.error(error)
            message = f'Сбой в работе программы: {error}'
            if last_message != message:
                send_message(bot, message)
                last_message = message
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s, %(levelname)s, %(message)s'
    )
    logging.StreamHandler(sys.stdout)

    main()
