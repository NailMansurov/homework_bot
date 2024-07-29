class HTTPStatusError(Exception):
    """Запрос не выполнен успешно."""


class SendMessageError(Exception):
    """Ошибка при отправке сообщения."""


class RequestError(Exception):
    """Ошибка запроса к к эндпоинту Яндекс Практикум."""


class EmptyHomeworksError(Exception):
    """Получен пустой список домашних работ."""
