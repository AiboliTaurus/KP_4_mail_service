# users/models.py
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    """Менеджер для кастомной модели пользователя"""

    def create_user(self, email, password=None, **extra_fields):
        """Создание обычного пользователя"""
        if not email:
            raise ValueError('Email должен быть указан')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """Создание суперпользователя"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Суперпользователь должен иметь is_staff=True')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Суперпользователь должен иметь is_superuser=True')

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """Кастомная модель пользователя"""
    username = None

    email = models.EmailField(
        unique=True,
        verbose_name='Электронная почта',
        help_text='Введите ваш email'
    )
    avatar = models.ImageField(
        upload_to='users/avatars/',
        verbose_name='Аватар',
        blank=True,
        null=True,
        help_text='Загрузите аватар (необязательно)'
    )
    phone_number = models.CharField(
        max_length=20,
        verbose_name='Номер телефона',
        blank=True,
        null=True,
        help_text='Введите номер телефона (необязательно)'
    )
    country = models.CharField(
        max_length=100,
        verbose_name='Страна',
        blank=True,
        null=True,
        help_text='Введите страну проживания (необязательно)'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Активен',
        help_text='Позволяет блокировать пользователя'
    )

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ['email']
        permissions = [
            ('can_view_all_mailings', 'Может просматривать все рассылки'),
            ('can_view_all_clients', 'Может просматривать всех получателей'),
            ('can_block_users', 'Может блокировать пользователей'),
            ('can_disable_mailings', 'Может отключать рассылки'),
        ]

    def __str__(self):
        return self.email
