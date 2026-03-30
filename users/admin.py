# users/admin.py
"""
Административный интерфейс для управления пользователями.

Настраивает отображение кастомной модели User в панели администратора.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Настройка отображения кастомной модели User в админке.

    Поля:
        list_display: Поля, отображаемые в списке пользователей
        list_display_links: Поля, являющиеся ссылками на редактирование
        search_fields: Поля для поиска
        list_filter: Поля для фильтрации
        ordering: Сортировка по умолчанию
    """
    list_display = ('id', 'email', 'first_name', 'last_name', 'is_staff', 'is_active')
    list_display_links = ('id', 'email')
    search_fields = ('email', 'first_name', 'last_name')
    list_filter = ('is_staff', 'is_active', 'country')
    ordering = ('email',)

    fieldsets = (
        ('Основная информация', {
            'fields': ('email', 'password')
        }),
        ('Персональные данные', {
            'fields': ('first_name', 'last_name', 'avatar', 'phone_number', 'country')
        }),
        ('Права доступа', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')
        }),
        ('Даты', {
            'fields': ('last_login', 'date_joined'),
            'classes': ('collapse',)
        }),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2'),
        }),
    )
