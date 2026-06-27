# mailing/apps.py
"""
Конфигурация приложения рассылок.

Определяет настройки приложения mailing для Django.
"""

from django.apps import AppConfig


class MailingConfig(AppConfig):
    """
    Класс конфигурации приложения mailing.

    Attributes:
        default_auto_field: Тип поля автоинкремента по умолчанию
        name: Имя приложения
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'mailing'
