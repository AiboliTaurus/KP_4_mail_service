# mailing/management/commands/send_mailings.py
"""
Кастомная команда для отправки активных рассылок из командной строки.

Запуск:
    python manage.py send_mailings

Описание:
    Команда находит все активные рассылки (статус 'started' и текущее время
    между start_time и end_time) и отправляет их.
"""

from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.utils import timezone
from django.conf import settings
from mailing.models import Mailing, Attempt


class Command(BaseCommand):
    """
    Команда для отправки активных рассылок.
    """
    help = 'Отправляет все активные рассылки'

    def handle(self, *args, **kwargs):
        """
        Основной метод выполнения команды.

        Args:
            *args: Дополнительные аргументы
            **kwargs: Дополнительные именованные аргументы
        """
        self.stdout.write(self.style.SUCCESS('=' * 50))
        self.stdout.write(self.style.SUCCESS('Начинаем отправку рассылок...'))
        self.stdout.write(self.style.SUCCESS('=' * 50))

        # Получаем все активные рассылки
        mailings = Mailing.objects.filter(
            start_time__lte=timezone.now(),
            end_time__gte=timezone.now(),
            status='started'
        )

        self.stdout.write(f'\n📊 Найдено активных рассылок: {mailings.count()}')

        if mailings.count() == 0:
            self.stdout.write(self.style.WARNING('\n⚠️ Нет активных рассылок для отправки'))
            return

        total_success = 0
        total_failed = 0

        for mailing in mailings:
            self.stdout.write(
                f'\n📧 Обработка рассылки #{mailing.id} (от {mailing.start_time.strftime("%d.%m.%Y %H:%M")})')
            self.stdout.write(f'   Тема: {mailing.message.subject}')
            self.stdout.write(f'   Получателей: {mailing.recipients.count()}')

            success_count = 0
            failed_count = 0

            for client in mailing.recipients.all():
                try:
                    # Отправка письма
                    send_mail(
                        subject=mailing.message.subject,
                        message=mailing.message.body,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[client.email],
                        fail_silently=False,
                    )

                    # Создаем успешную попытку
                    Attempt.objects.create(
                        status='success',
                        server_response='Письмо успешно отправлено',
                        mailing=mailing,
                        client=client
                    )
                    success_count += 1
                    self.stdout.write(f'   ✓ Успешно: {client.email}')

                except Exception as e:
                    # Создаем неуспешную попытку
                    Attempt.objects.create(
                        status='failed',
                        server_response=str(e)[:500],
                        mailing=mailing,
                        client=client
                    )
                    failed_count += 1
                    self.stdout.write(f'   ✗ Ошибка: {client.email} - {str(e)}')

            total_success += success_count
            total_failed += failed_count

            self.stdout.write(f'\n   📊 Итог по рассылке #{mailing.id}:')
            self.stdout.write(f'      ✅ Успешно: {success_count}')
            self.stdout.write(f'      ❌ Ошибок: {failed_count}')

        self.stdout.write(self.style.SUCCESS('\n' + '=' * 50))
        self.stdout.write(self.style.SUCCESS('ОТПРАВКА ЗАВЕРШЕНА!'))
        self.stdout.write(self.style.SUCCESS(f'✅ Всего успешных: {total_success}'))
        self.stdout.write(self.style.SUCCESS(f'❌ Всего ошибок: {total_failed}'))
        self.stdout.write(self.style.SUCCESS('=' * 50))
