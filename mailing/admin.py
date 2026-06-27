# mailing/admin.py
"""
Административный интерфейс для управления рассылками.

Настраивает отображение моделей Mailing, Message, Client, Attempt
в панели администратора Django.
"""

from django.contrib import admin
from .models import Mailing, Message, Client, Attempt


@admin.register(Mailing)
class MailingAdmin(admin.ModelAdmin):
    """
    Настройка отображения модели Mailing в админке.

    Поля:
        list_display: Поля, отображаемые в списке
        list_display_links: Поля, которые являются ссылками на редактирование
        list_filter: Поля для фильтрации
        search_fields: Поля для поиска
        readonly_fields: Только для чтения
    """
    list_display = ('id', 'start_time', 'end_time', 'status', 'message', 'owner', 'created_at')

    # ✅ ДОБАВЛЯЕМ list_display_links — делаем ID и start_time кликабельными
    list_display_links = ('id', 'start_time')

    list_filter = ('status', 'start_time', 'end_time')
    search_fields = ('message__subject', 'owner__email')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Временные параметры', {
            'fields': ('start_time', 'end_time')
        }),
        ('Статус и сообщение', {
            'fields': ('status', 'message', 'recipients')
        }),
        ('Владелец', {
            'fields': ('owner',)
        }),
        ('Даты', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    """
    Настройка отображения модели Message в админке.
    """
    list_display = ('id', 'subject', 'owner', 'created_at')

    # ✅ ДОБАВЛЯЕМ list_display_links
    list_display_links = ('id', 'subject')

    search_fields = ('subject', 'body', 'owner__email')
    list_filter = ('owner', 'created_at')


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    """
    Настройка отображения модели Client в админке.
    """
    list_display = ('id', 'email', 'full_name', 'owner', 'created_at')

    # ✅ ДОБАВЛЯЕМ list_display_links
    list_display_links = ('id', 'email')

    search_fields = ('email', 'full_name', 'comment', 'owner__email')
    list_filter = ('owner', 'created_at')


@admin.register(Attempt)
class AttemptAdmin(admin.ModelAdmin):
    """
    Настройка отображения модели Attempt в админке.
    """
    list_display = ('id', 'attempt_time', 'status', 'mailing', 'client')

    # ✅ ДОБАВЛЯЕМ list_display_links
    list_display_links = ('id', 'attempt_time')

    list_filter = ('status', 'attempt_time')
    search_fields = ('mailing__message__subject', 'client__email')
    readonly_fields = ('attempt_time',)
