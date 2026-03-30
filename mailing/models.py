# mailing/models.py
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError


class Client(models.Model):
    """Модель получателя рассылки (клиента)"""
    email = models.EmailField(unique=True, verbose_name='Email')
    full_name = models.CharField(max_length=200, verbose_name='ФИО')
    comment = models.TextField(blank=True, null=True, verbose_name='Комментарий')
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name='Владелец',
        related_name='clients',
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = 'Получатель рассылки'
        verbose_name_plural = 'Получатели рассылки'
        ordering = ['-created_at']
        permissions = [
            ('can_view_all_clients', 'Может просматривать всех получателей'),
        ]

    def __str__(self):
        return f'{self.full_name} ({self.email})'


class Message(models.Model):
    """Модель сообщения для рассылки"""
    subject = models.CharField(max_length=255, verbose_name='Тема письма')
    body = models.TextField(verbose_name='Тело письма')
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name='Владелец',
        related_name='messages',
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = 'Сообщение'
        verbose_name_plural = 'Сообщения'
        ordering = ['-created_at']
        permissions = [
            ('can_view_all_messages', 'Может просматривать все сообщения'),
        ]

    def __str__(self):
        return self.subject


class Mailing(models.Model):
    """Модель рассылки"""
    STATUS_CHOICES = [
        ('created', 'Создана'),
        ('started', 'Запущена'),
        ('completed', 'Завершена'),
        ('disabled', 'Отключена'),
    ]

    start_time = models.DateTimeField(verbose_name='Дата и время начала')
    end_time = models.DateTimeField(verbose_name='Дата и время окончания')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='created', verbose_name='Статус')
    message = models.ForeignKey(Message, on_delete=models.CASCADE, verbose_name='Сообщение', related_name='mailings')
    recipients = models.ManyToManyField(Client, verbose_name='Получатели', related_name='mailings')
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name='Владелец',
        related_name='mailings',
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = 'Рассылка'
        verbose_name_plural = 'Рассылки'
        ordering = ['-created_at']
        permissions = [
            ('can_view_all_mailings', 'Может просматривать все рассылки'),
            ('can_disable_mailing', 'Может отключать рассылки'),
        ]

    def __str__(self):
        return f'Рассылка от {self.start_time.strftime("%d.%m.%Y %H:%M")}'

    def clean(self):
        if self.start_time and self.end_time:
            if self.start_time >= self.end_time:
                raise ValidationError('Дата начала должна быть раньше даты окончания')
            if self.start_time < timezone.now():
                raise ValidationError('Дата начала не может быть в прошлом')

    def update_status(self):
        now = timezone.now()
        if self.status == 'disabled':
            return
        if now < self.start_time:
            new_status = 'created'
        elif self.start_time <= now <= self.end_time:
            new_status = 'started'
        else:
            new_status = 'completed'
        if new_status != self.status:
            self.status = new_status
            self.save(update_fields=['status'])

    def can_send(self):
        now = timezone.now()
        return self.start_time <= now <= self.end_time and self.status != 'disabled'


class Attempt(models.Model):
    """Модель попытки отправки"""
    STATUS_CHOICES = [
        ('success', 'Успешно'),
        ('failed', 'Не успешно'),
    ]

    attempt_time = models.DateTimeField(auto_now_add=True, verbose_name='Дата и время попытки')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, verbose_name='Статус')
    server_response = models.TextField(blank=True, null=True, verbose_name='Ответ сервера')
    mailing = models.ForeignKey(Mailing, on_delete=models.CASCADE, verbose_name='Рассылка', related_name='attempts')
    client = models.ForeignKey(Client, on_delete=models.CASCADE, verbose_name='Получатель', related_name='attempts',
                               null=True, blank=True)

    class Meta:
        verbose_name = 'Попытка рассылки'
        verbose_name_plural = 'Попытки рассылки'
        ordering = ['-attempt_time']

    def __str__(self):
        return f'Попытка от {self.attempt_time.strftime("%d.%m.%Y %H:%M")} - {self.get_status_display()}'
