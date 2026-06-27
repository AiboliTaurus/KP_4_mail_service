# users/apps.py
"""
Конфигурация приложения пользователей.

Определяет настройки приложения users для Django.
"""

from django.apps import AppConfig


class UsersConfig(AppConfig):
    """
    Класс конфигурации приложения users.

    Attributes:
        default_auto_field: Тип поля автоинкремента по умолчанию
        name: Имя приложения
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'users'
