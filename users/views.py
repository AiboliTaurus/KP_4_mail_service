# users/views.py
"""
Модуль представлений (контроллеров) для управления пользователями.

Содержит классы для:
- Регистрации новых пользователей
- Аутентификации (вход/выход)
- Редактирования профиля пользователя
"""

from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.core.mail import send_mail
from django.conf import settings

from .forms import UserRegistrationForm, UserLoginForm, UserProfileForm
from .models import User


class UserRegistrationView(SuccessMessageMixin, CreateView):
    """
    Контроллер для регистрации нового пользователя.

    При успешной регистрации:
    - Отправляет приветственное письмо на указанный email
    - Выводит сообщение об успешной регистрации
    - Перенаправляет на страницу входа
    """
    model = User
    form_class = UserRegistrationForm
    template_name = 'users/register.html'
    success_url = reverse_lazy('users:login')
    success_message = 'Регистрация прошла успешно! Теперь вы можете войти в систему.'

    def form_valid(self, form):
        """
        Обработка валидной формы регистрации.

        Args:
            form: Валидная форма регистрации

        Returns:
            HttpResponse: Результат обработки формы
        """
        response = super().form_valid(form)
        self.send_welcome_email(form.cleaned_data['email'])
        return response

    def send_welcome_email(self, email):
        """
        Отправка приветственного письма после успешной регистрации.

        Args:
            email: Email адрес получателя
        """
        subject = 'Добро пожаловать в сервис рассылок!'
        message = '''
        Здравствуйте!

        Спасибо за регистрацию в сервисе управления рассылками!

        Теперь вы можете:
        - Создавать и управлять рассылками
        - Добавлять получателей
        - Создавать сообщения
        - Просматривать статистику отправок

        С уважением,
        Команда сервиса рассылок
        '''

        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
            print(f'✅ Приветственное письмо отправлено на {email}')
        except Exception as e:
            print(f'❌ Ошибка отправки письма: {e}')


class UserLoginView(LoginView):
    """
    Контроллер для аутентификации пользователя (вход в систему).

    Использует кастомную форму авторизации с полем email.
    После успешного входа перенаправляет на главную страницу сервиса.
    """
    form_class = UserLoginForm
    template_name = 'users/login.html'

    def get_success_url(self):
        """
        Возвращает URL для перенаправления после успешного входа.

        Returns:
            str: URL главной страницы приложения рассылок
        """
        return reverse_lazy('mailing:home')


class UserLogoutView(LogoutView):
    """
    Контроллер для выхода пользователя из системы.

    После выхода перенаправляет на главную страницу сервиса.
    """
    next_page = reverse_lazy('mailing:home')


class UserProfileView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    """
    Контроллер для просмотра и редактирования профиля пользователя.

    Доступен только авторизованным пользователям.
    Каждый пользователь может редактировать только свой профиль.
    """
    model = User
    form_class = UserProfileForm
    template_name = 'users/profile.html'
    success_message = 'Профиль успешно обновлен!'

    def get_success_url(self):
        """
        Возвращает URL для перенаправления после сохранения профиля.

        Returns:
            str: URL страницы профиля текущего пользователя
        """
        return reverse_lazy('users:profile', kwargs={'pk': self.object.pk})

    def get_object(self, queryset=None):
        """
        Возвращает объект пользователя для редактирования.

        Всегда возвращает текущего авторизованного пользователя,
        независимо от переданного в URL pk.

        Args:
            queryset: Набор объектов (не используется)

        Returns:
            User: Текущий авторизованный пользователь
        """
        return self.request.user
