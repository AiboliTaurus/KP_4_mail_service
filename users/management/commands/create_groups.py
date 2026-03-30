# users/management/commands/create_groups.py
"""
Кастомная команда для создания группы "Менеджеры" с необходимыми правами.

Запуск:
    python manage.py create_groups
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission


class Command(BaseCommand):
    """
    Команда для создания группы "Менеджеры" и назначения прав.
    """
    help = 'Создает группу "Менеджеры" с необходимыми правами доступа'

    def handle(self, *args, **kwargs):
        """
        Основной метод выполнения команды.
        """
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('НАЧИНАЕМ СОЗДАНИЕ ГРУППЫ "МЕНЕДЖЕРЫ"'))
        self.stdout.write(self.style.SUCCESS('=' * 60))

        self.create_manager_group()

        self.stdout.write(self.style.SUCCESS('\n' + '=' * 60))
        self.stdout.write(self.style.SUCCESS('ГРУППЫ УСПЕШНО СОЗДАНЫ!'))
        self.stdout.write(self.style.SUCCESS('=' * 60))

    def create_manager_group(self):
        """
        Создание группы "Менеджеры" и назначение прав.
        """
        # Создаем группу "Менеджеры"
        manager_group, created = Group.objects.get_or_create(name='Менеджеры')

        if created:
            self.stdout.write(self.style.SUCCESS('✓ Создана группа "Менеджеры"'))
        else:
            self.stdout.write(self.style.WARNING('✓ Группа "Менеджеры" уже существует, обновляем права'))

        # Список прав, которые нужно назначить группе
        permission_codenames = [
            'can_view_all_mailings',  # Просмотр всех рассылок
            'can_view_all_clients',  # Просмотр всех получателей
            'can_view_all_messages',  # Просмотр всех сообщений
            'can_block_users',  # Блокировка пользователей
            'can_disable_mailing',  # Отключение рассылок
        ]

        # Получаем права из базы данных
        permissions = Permission.objects.filter(codename__in=permission_codenames)

        # Добавляем права группе
        added_count = 0
        for perm in permissions:
            manager_group.permissions.add(perm)
            added_count += 1
            self.stdout.write(f'  └─ Добавлено право: {perm.codename} - {perm.name}')

        if added_count == 0:
            self.stdout.write(self.style.WARNING('  ⚠️ Не найдено ни одного права! Возможно, миграции не применены.'))

        self.stdout.write(f'\n📊 Группа "Менеджеры" теперь имеет {manager_group.permissions.count()} прав')

        # Показываем все права группы
        self.stdout.write('\n📋 СПИСОК ПРАВ ГРУППЫ:')
        for perm in manager_group.permissions.all().order_by('codename'):
            self.stdout.write(f'   - {perm.codename}: {perm.name}')
