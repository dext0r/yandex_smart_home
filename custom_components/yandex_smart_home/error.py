"""Errors for Yandex Smart Home."""


class SmartHomeError(Exception):
    """Yandex Smart Home errors.

    https://yandex.ru/dev/dialogs/alice/doc/smart-home/concepts/response-codes-docpage/
    """

    def __init__(self, code, msg):
        super().__init__(msg)
        self.code = code
        self.message = msg


class SmartHomeUserError(Exception):
    """Error producted by user's template, no logging"""
    def __init__(self, code):
        self.code = code
