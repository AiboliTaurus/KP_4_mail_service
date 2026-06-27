# mailing/views.py
"""
Модуль представлений для приложения рассылок с кешированием.

Содержит классы для:
- Просмотра главной страницы со статистикой (кеширование)
- Управления рассылками (CRUD + кеширование)
- Управления сообщениями (CRUD)
- Управления получателями (CRUD)
- Просмотра статистики попыток
"""

from django.urls import reverse_lazy
from django.views.generic import TemplateView, ListView, DetailView, CreateView, UpdateView, DeleteView
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.mail import send_mail
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from .models import Mailing, Message, Client, Attempt
from .forms import MailingForm, MessageForm, ClientForm


class HomeView(TemplateView):
    """
    Главная страница с отображением статистики.

    Использует кеширование для:
    - Общего количества рассылок
    - Количества активных рассылок
    - Количества уникальных получателей

    Время кеширования: 5 минут (300 секунд)
    """
    template_name = 'mailing/home.html'

    def get_context_data(self, **kwargs):
        """Получение контекста с использованием кеширования"""
        context = super().get_context_data(**kwargs)

        # ✅ ОБНОВЛЯЕМ СТАТУС ВСЕХ РАССЫЛОК ПЕРЕД ПОДСЧЕТОМ СТАТИСТИКИ
        for mailing in Mailing.objects.all():
            mailing.update_status()

        cache_key = 'home_stats'

        if settings.CACHE_ENABLED:
            stats = cache.get(cache_key)
            if stats is not None:
                print("✅ КЭШ: Статистика главной страницы получена из кэша (ключ: home_stats)")
                context.update(stats)
                return context
            else:
                print("📊 БД: Статистика главной страницы загружается из базы данных (кеш MISS)")

        # Получаем статистику из базы данных
        now = timezone.now()
        stats = {
            'total_mailings': Mailing.objects.count(),
            'active_mailings': Mailing.objects.filter(
                start_time__lte=now,
                end_time__gte=now,
                status='started'
            ).count(),
            'unique_clients': Client.objects.count(),
        }

        context.update(stats)

        # Сохраняем в кеш
        if settings.CACHE_ENABLED:
            cache.set(cache_key, stats, timeout=300)
            print("💾 КЭШ: Статистика главной страницы сохранена в кеш (ключ: home_stats)")

        return context


class MailingListView(LoginRequiredMixin, ListView):
    """
    Список рассылок пользователя.

    Использует кеширование для хранения списка рассылок.
    Кеш индивидуальный для каждого пользователя.
    Время кеширования: 5 минут (300 секунд)
    """
    model = Mailing
    template_name = 'mailing/mailing_list.html'
    context_object_name = 'mailings'
    paginate_by = 10

    def get_queryset(self):
        """
        Получение списка рассылок с кешированием.

        Returns:
            list: Список рассылок
        """
        # ✅ ОБНОВЛЯЕМ СТАТУС ВСЕХ РАССЫЛОК ПЕРЕД ОТОБРАЖЕНИЕМ СПИСКА
        for mailing in Mailing.objects.all():
            mailing.update_status()

        cache_key = f'user_{self.request.user.id}_mailings'

        if settings.CACHE_ENABLED:
            mailings = cache.get(cache_key)
            if mailings is not None:
                print(f"✅ КЭШ: Список рассылок для пользователя {self.request.user.id} получен из кэша")
                return mailings
            else:
                print(f"📊 БД: Загрузка списка рассылок для пользователя {self.request.user.id} (кеш MISS)")

        # Получаем данные из базы данных
        user = self.request.user
        if user.has_perm('mailing.can_view_all_mailings'):
            mailings = list(Mailing.objects.all().select_related('message', 'owner'))
        else:
            mailings = list(Mailing.objects.filter(owner=user).select_related('message', 'owner'))

        # Сохраняем в кеш
        if settings.CACHE_ENABLED:
            cache.set(cache_key, mailings, timeout=300)
            print(f"💾 КЭШ: Список рассылок для пользователя {self.request.user.id} сохранен в кеш")

        return mailings


class MailingDetailView(LoginRequiredMixin, DetailView):
    """
    Детальная страница рассылки.

    Использует кеширование для хранения данных рассылки.
    Статус рассылки обновляется при каждом просмотре (не кешируется).
    Время кеширования: 5 минут (300 секунд)
    """
    model = Mailing
    template_name = 'mailing/mailing_detail.html'
    context_object_name = 'mailing'

    def get_object(self, queryset=None):
        """
        Получение объекта рассылки с кешированием.

        Returns:
            Mailing: Объект рассылки
        """
        cache_key = f'mailing_{self.kwargs.get("pk")}'

        if settings.CACHE_ENABLED:
            mailing = cache.get(cache_key)
            if mailing is not None:
                print(f"✅ КЭШ: Рассылка ID={self.kwargs.get('pk')} получена из кэша")
                # Обновляем статус (статус не кешируется)
                mailing.update_status()
                return mailing
            else:
                print(f"📊 БД: Загрузка рассылки ID={self.kwargs.get('pk')} из базы данных (кеш MISS)")

        # Получаем из базы данных
        mailing = super().get_object(queryset)
        mailing.update_status()

        # Сохраняем в кеш
        if settings.CACHE_ENABLED:
            cache.set(cache_key, mailing, timeout=300)
            print(f"💾 КЭШ: Рассылка ID={self.kwargs.get('pk')} сохранена в кеш")

        return mailing

    def get_context_data(self, **kwargs):
        """
        Добавляет попытки отправки и статистику в контекст.

        Returns:
            dict: Контекст с дополнительными данными
        """
        context = super().get_context_data(**kwargs)

        # Получаем все попытки для этой рассылки
        attempts = self.object.attempts.all()

        # Добавляем попытки в контекст (только последние 20)
        context['attempts'] = attempts[:20]

        # Добавляем статистику (подсчет успешных и неудачных попыток)
        context['success_count'] = attempts.filter(status='success').count()
        context['failed_count'] = attempts.filter(status='failed').count()

        return context


class MailingCreateView(LoginRequiredMixin, CreateView):
    """
    Создание новой рассылки.

    При создании:
    - Устанавливает владельца
    - Очищает кеш списка рассылок пользователя
    - Очищает кеш статистики главной страницы
    """
    model = Mailing
    form_class = MailingForm
    template_name = 'mailing/mailing_form.html'
    success_url = reverse_lazy('mailing:mailing_list')

    def form_valid(self, form):
        """
        Обработка валидной формы.

        Args:
            form: Валидная форма рассылки

        Returns:
            HttpResponse: Результат обработки
        """
        form.instance.owner = self.request.user
        response = super().form_valid(form)

        # Очищаем кеш
        self.clear_cache()

        messages.success(self.request, f'Рассылка "{self.object}" успешно создана!')
        return response

    def clear_cache(self):
        """Очистка кеша после создания рассылки"""
        # Очищаем кеш статистики главной страницы
        cache.delete('home_stats')
        print("🗑️ КЭШ: Очищен кеш главной страницы")

        # Очищаем кеш списка рассылок пользователя
        cache.delete(f'user_{self.request.user.id}_mailings')
        print(f"🗑️ КЭШ: Очищен кеш списка рассылок пользователя {self.request.user.id}")

        # Очищаем общий кеш (если используется)
        cache.delete('all_mailings_list')

    def form_invalid(self, form):
        """
        Обработка невалидной формы.

        Args:
            form: Невалидная форма рассылки

        Returns:
            HttpResponse: Результат обработки
        """
        messages.error(self.request, 'Пожалуйста, исправьте ошибки в форме.')
        return super().form_invalid(form)


class MailingUpdateView(LoginRequiredMixin, UpdateView):
    """
    Редактирование рассылки.

    При редактировании:
    - Проверяет права доступа
    - Очищает кеш рассылки, списка рассылок пользователя и статистики
    """
    model = Mailing
    form_class = MailingForm
    template_name = 'mailing/mailing_form.html'

    def dispatch(self, request, *args, **kwargs):
        """
        Проверка прав доступа перед обработкой запроса.

        Args:
            request: HTTP запрос

        Returns:
            HttpResponse: Результат проверки
        """
        obj = self.get_object()
        if not (request.user == obj.owner or request.user.has_perm('mailing.can_disable_mailing')):
            raise PermissionDenied("У вас нет прав для редактирования этой рассылки")
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        """
        Перенаправление после успешного сохранения.

        Returns:
            str: URL детальной страницы рассылки
        """
        # Очищаем кеш
        self.clear_cache()

        messages.success(self.request, f'Рассылка "{self.object}" успешно обновлена!')
        return reverse_lazy('mailing:mailing_detail', kwargs={'pk': self.object.pk})

    def clear_cache(self):
        """Очистка кеша после обновления рассылки"""
        # Очищаем кеш конкретной рассылки
        cache.delete(f'mailing_{self.object.pk}')
        print(f"🗑️ КЭШ: Очищен кеш рассылки ID={self.object.pk}")

        # Очищаем кеш списка рассылок пользователя
        cache.delete(f'user_{self.request.user.id}_mailings')
        print(f"🗑️ КЭШ: Очищен кеш списка рассылок пользователя {self.request.user.id}")

        # Очищаем кеш статистики главной страницы
        cache.delete('home_stats')
        print("🗑️ КЭШ: Очищен кеш главной страницы")

    def form_invalid(self, form):
        """
        Обработка невалидной формы.

        Args:
            form: Невалидная форма рассылки

        Returns:
            HttpResponse: Результат обработки
        """
        messages.error(self.request, 'Пожалуйста, исправьте ошибки в форме.')
        return super().form_invalid(form)


class MailingDeleteView(LoginRequiredMixin, DeleteView):
    """
    Удаление рассылки.

    При удалении:
    - Проверяет права доступа
    - Очищает кеш списка рассылок пользователя и статистики
    """
    model = Mailing
    template_name = 'mailing/mailing_confirm_delete.html'
    success_url = reverse_lazy('mailing:mailing_list')

    def dispatch(self, request, *args, **kwargs):
        """
        Проверка прав доступа перед обработкой запроса.

        Args:
            request: HTTP запрос

        Returns:
            HttpResponse: Результат проверки
        """
        obj = self.get_object()
        if request.user != obj.owner:
            raise PermissionDenied("У вас нет прав для удаления этой рассылки")
        return super().dispatch(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        """
        Удаление рассылки с очисткой кеша.

        Args:
            request: HTTP запрос

        Returns:
            HttpResponse: Результат удаления
        """
        self.object = self.get_object()
        mailing_name = str(self.object)
        mailing_id = self.object.pk

        response = super().delete(request, *args, **kwargs)

        # Очищаем кеш
        self.clear_cache(mailing_id)

        messages.success(request, f'Рассылка "{mailing_name}" успешно удалена!')
        return response

    def clear_cache(self, mailing_id):
        """Очистка кеша после удаления рассылки"""
        # Очищаем кеш конкретной рассылки (если есть)
        cache.delete(f'mailing_{mailing_id}')
        print(f"🗑️ КЭШ: Очищен кеш рассылки ID={mailing_id}")

        # Очищаем кеш списка рассылок пользователя
        cache.delete(f'user_{self.request.user.id}_mailings')
        print(f"🗑️ КЭШ: Очищен кеш списка рассылок пользователя {self.request.user.id}")

        # Очищаем кеш статистики главной страницы
        cache.delete('home_stats')
        print("🗑️ КЭШ: Очищен кеш главной страницы")


class MailingSendView(LoginRequiredMixin, View):
    """
    Отправка рассылки вручную через интерфейс.

    При отправке:
    - Проверяет возможность отправки
    - Отправляет письма всем получателям
    - Сохраняет попытки отправки
    """

    def post(self, request, pk):
        """
        Обработка POST запроса на отправку рассылки.

        Args:
            request: HTTP запрос
            pk: ID рассылки

        Returns:
            HttpResponse: Редирект на страницу рассылки
        """
        mailing = get_object_or_404(Mailing, pk=pk)

        # ✅ ОБНОВЛЯЕМ СТАТУС ПЕРЕД ПРОВЕРКОЙ
        mailing.update_status()

        # Проверка прав
        if not (request.user == mailing.owner or request.user.has_perm('mailing.can_disable_mailing')):
            raise PermissionDenied("У вас нет прав для отправки этой рассылки")

        # ✅ ПРОВЕРКА ВОЗМОЖНОСТИ ОТПРАВКИ С ДЕТАЛЬНЫМ ЛОГИРОВАНИЕМ
        now = timezone.now()
        can_send = mailing.can_send()

        print("🔍 ПРОВЕРКА ОТПРАВКИ:")
        print(f"   start_time: {mailing.start_time}")
        print(f"   end_time: {mailing.end_time}")
        print(f"   now: {now}")
        print(f"   start_time <= now: {mailing.start_time <= now}")
        print(f"   now <= end_time: {now <= mailing.end_time}")
        print(f"   status != disabled: {mailing.status != 'disabled'}")
        print(f"   can_send: {can_send}")

        if not can_send:
            messages.error(request, 'Нельзя отправить рассылку: время отправки не наступило или уже прошло')
            return redirect('mailing:mailing_detail', pk=pk)

        # Отправка рассылки
        success_count, failed_count = self.send_mailing(mailing)

        # Очищаем кеш после отправки
        cache.delete(f'mailing_{mailing.pk}')
        cache.delete(f'user_{request.user.id}_mailings')
        cache.delete(f'user_{request.user.id}_attempts')
        cache.delete('home_stats')
        print("🗑️ КЭШ: Очищен кеш рассылки и статистики после отправки")

        messages.success(request, f'Рассылка отправлена! Успешно: {success_count}, Ошибок: {failed_count}')
        return redirect('mailing:mailing_detail', pk=pk)

    def send_mailing(self, mailing):
        """
        Отправка писем всем получателям.

        Args:
            mailing: Объект рассылки

        Returns:
            tuple: (количество успешных, количество неудачных отправок)
        """
        success_count = 0
        failed_count = 0

        for client in mailing.recipients.all():
            try:
                send_mail(
                    subject=mailing.message.subject,
                    message=mailing.message.body,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[client.email],
                    fail_silently=False,
                )

                Attempt.objects.create(
                    status='success',
                    server_response='Письмо успешно отправлено',
                    mailing=mailing,
                    client=client
                )
                success_count += 1
                print(f"📧 Успешно отправлено письмо на {client.email}")

            except Exception as e:
                Attempt.objects.create(
                    status='failed',
                    server_response=str(e)[:500],
                    mailing=mailing,
                    client=client
                )
                failed_count += 1
                print(f"❌ Ошибка отправки на {client.email}: {str(e)}")

        return success_count, failed_count


class MessageListView(LoginRequiredMixin, ListView):
    """
    Список сообщений пользователя.

    Использует кеширование для хранения списка сообщений.
    Время кеширования: 5 минут (300 секунд)
    """
    model = Message
    template_name = 'mailing/message_list.html'
    context_object_name = 'messages'
    paginate_by = 10

    def get_queryset(self):
        """
        Получение списка сообщений с кешированием.

        Returns:
            list: Список сообщений
        """
        cache_key = f'user_{self.request.user.id}_messages'

        if settings.CACHE_ENABLED:
            messages_list = cache.get(cache_key)
            if messages_list is not None:
                print(f"✅ КЭШ: Список сообщений для пользователя {self.request.user.id} получен из кэша")
                return messages_list
            else:
                print(f"📊 БД: Загрузка списка сообщений для пользователя {self.request.user.id} (кеш MISS)")

        # Получаем данные из базы данных
        user = self.request.user
        if user.has_perm('mailing.can_view_all_messages'):
            messages_list = list(Message.objects.all().select_related('owner'))
        else:
            messages_list = list(Message.objects.filter(owner=user).select_related('owner'))

        # Сохраняем в кеш
        if settings.CACHE_ENABLED:
            cache.set(cache_key, messages_list, timeout=300)
            print(f"💾 КЭШ: Список сообщений для пользователя {self.request.user.id} сохранен в кеш")

        return messages_list


class MessageDetailView(LoginRequiredMixin, DetailView):
    """
    Детальная страница сообщения.
    """
    model = Message
    template_name = 'mailing/message_detail.html'
    context_object_name = 'message'


class MessageCreateView(LoginRequiredMixin, CreateView):
    """
    Создание нового сообщения.

    При создании:
    - Устанавливает владельца
    - Очищает кеш списка сообщений пользователя
    """
    model = Message
    form_class = MessageForm
    template_name = 'mailing/message_form.html'
    success_url = reverse_lazy('mailing:message_list')

    def form_valid(self, form):
        """
        Обработка валидной формы.

        Args:
            form: Валидная форма сообщения

        Returns:
            HttpResponse: Результат обработки
        """
        form.instance.owner = self.request.user
        response = super().form_valid(form)

        # Очищаем кеш
        cache.delete(f'user_{self.request.user.id}_messages')
        print(f"🗑️ КЭШ: Очищен кеш списка сообщений пользователя {self.request.user.id}")

        messages.success(self.request, f'Сообщение "{self.object}" успешно создано!')
        return response

    def form_invalid(self, form):
        """
        Обработка невалидной формы.

        Args:
            form: Невалидная форма сообщения

        Returns:
            HttpResponse: Результат обработки
        """
        messages.error(self.request, 'Пожалуйста, исправьте ошибки в форме.')
        return super().form_invalid(form)


class MessageUpdateView(LoginRequiredMixin, UpdateView):
    """
    Редактирование сообщения.

    При редактировании:
    - Проверяет права доступа
    - Очищает кеш списка сообщений пользователя
    """
    model = Message
    form_class = MessageForm
    template_name = 'mailing/message_form.html'

    def dispatch(self, request, *args, **kwargs):
        """
        Проверка прав доступа перед обработкой запроса.

        Args:
            request: HTTP запрос

        Returns:
            HttpResponse: Результат проверки
        """
        obj = self.get_object()
        if request.user != obj.owner:
            raise PermissionDenied("У вас нет прав для редактирования этого сообщения")
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        """
        Перенаправление после успешного сохранения.

        Returns:
            str: URL детальной страницы сообщения
        """
        # Очищаем кеш
        cache.delete(f'user_{self.request.user.id}_messages')
        print(f"🗑️ КЭШ: Очищен кеш списка сообщений пользователя {self.request.user.id}")

        messages.success(self.request, f'Сообщение "{self.object}" успешно обновлено!')
        return reverse_lazy('mailing:message_detail', kwargs={'pk': self.object.pk})

    def form_invalid(self, form):
        """
        Обработка невалидной формы.

        Args:
            form: Невалидная форма сообщения

        Returns:
            HttpResponse: Результат обработки
        """
        messages.error(self.request, 'Пожалуйста, исправьте ошибки в форме.')
        return super().form_invalid(form)


class MessageDeleteView(LoginRequiredMixin, DeleteView):
    """
    Удаление сообщения.

    При удалении:
    - Проверяет права доступа
    - Очищает кеш списка сообщений пользователя
    """
    model = Message
    template_name = 'mailing/message_confirm_delete.html'
    success_url = reverse_lazy('mailing:message_list')

    def dispatch(self, request, *args, **kwargs):
        """
        Проверка прав доступа перед обработкой запроса.

        Args:
            request: HTTP запрос

        Returns:
            HttpResponse: Результат проверки
        """
        obj = self.get_object()
        if request.user != obj.owner:
            raise PermissionDenied("У вас нет прав для удаления этого сообщения")
        return super().dispatch(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        """
        Удаление сообщения с очисткой кеша.

        Args:
            request: HTTP запрос

        Returns:
            HttpResponse: Результат удаления
        """
        self.object = self.get_object()
        message_name = str(self.object)

        response = super().delete(request, *args, **kwargs)

        # Очищаем кеш
        cache.delete(f'user_{self.request.user.id}_messages')
        print(f"🗑️ КЭШ: Очищен кеш списка сообщений пользователя {self.request.user.id}")

        messages.success(request, f'Сообщение "{message_name}" успешно удалено!')
        return response


class ClientListView(LoginRequiredMixin, ListView):
    """
    Список получателей пользователя.

    Использует кеширование для хранения списка получателей.
    Время кеширования: 5 минут (300 секунд)
    """
    model = Client
    template_name = 'mailing/client_list.html'
    context_object_name = 'clients'
    paginate_by = 10

    def get_queryset(self):
        """
        Получение списка получателей с кешированием.

        Returns:
            list: Список получателей
        """
        cache_key = f'user_{self.request.user.id}_clients'

        if settings.CACHE_ENABLED:
            clients = cache.get(cache_key)
            if clients is not None:
                print(f"✅ КЭШ: Список получателей для пользователя {self.request.user.id} получен из кэша")
                return clients
            else:
                print(f"📊 БД: Загрузка списка получателей для пользователя {self.request.user.id} (кеш MISS)")

        # Получаем данные из базы данных
        user = self.request.user
        if user.has_perm('mailing.can_view_all_clients'):
            clients = list(Client.objects.all().select_related('owner'))
        else:
            clients = list(Client.objects.filter(owner=user).select_related('owner'))

        # Сохраняем в кеш
        if settings.CACHE_ENABLED:
            cache.set(cache_key, clients, timeout=300)
            print(f"💾 КЭШ: Список получателей для пользователя {self.request.user.id} сохранен в кеш")

        return clients


class ClientDetailView(LoginRequiredMixin, DetailView):
    """
    Детальная страница получателя.
    """
    model = Client
    template_name = 'mailing/client_detail.html'
    context_object_name = 'client'


class ClientCreateView(LoginRequiredMixin, CreateView):
    """
    Создание нового получателя.

    При создании:
    - Устанавливает владельца
    - Очищает кеш списка получателей пользователя
    - Очищает кеш статистики главной страницы
    """
    model = Client
    form_class = ClientForm
    template_name = 'mailing/client_form.html'
    success_url = reverse_lazy('mailing:client_list')

    def form_valid(self, form):
        """
        Обработка валидной формы.

        Args:
            form: Валидная форма получателя

        Returns:
            HttpResponse: Результат обработки
        """
        form.instance.owner = self.request.user
        response = super().form_valid(form)

        # Очищаем кеш
        self.clear_cache()

        messages.success(self.request, f'Клиент "{self.object}" успешно добавлен!')
        return response

    def clear_cache(self):
        """Очистка кеша после создания получателя"""
        # Очищаем кеш списка получателей пользователя
        cache.delete(f'user_{self.request.user.id}_clients')
        print(f"🗑️ КЭШ: Очищен кеш списка получателей пользователя {self.request.user.id}")

        # Очищаем кеш статистики главной страницы
        cache.delete('home_stats')
        print("🗑️ КЭШ: Очищен кеш главной страницы")

    def form_invalid(self, form):
        """
        Обработка невалидной формы.

        Args:
            form: Невалидная форма получателя

        Returns:
            HttpResponse: Результат обработки
        """
        messages.error(self.request, 'Пожалуйста, исправьте ошибки в форме.')
        return super().form_invalid(form)


class ClientUpdateView(LoginRequiredMixin, UpdateView):
    """
    Редактирование получателя.

    При редактировании:
    - Проверяет права доступа
    - Очищает кеш списка получателей пользователя
    """
    model = Client
    form_class = ClientForm
    template_name = 'mailing/client_form.html'

    def dispatch(self, request, *args, **kwargs):
        """
        Проверка прав доступа перед обработкой запроса.

        Args:
            request: HTTP запрос

        Returns:
            HttpResponse: Результат проверки
        """
        obj = self.get_object()
        if request.user != obj.owner:
            raise PermissionDenied("У вас нет прав для редактирования этого клиента")
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        """
        Перенаправление после успешного сохранения.

        Returns:
            str: URL детальной страницы получателя
        """
        # Очищаем кеш
        cache.delete(f'user_{self.request.user.id}_clients')
        print(f"🗑️ КЭШ: Очищен кеш списка получателей пользователя {self.request.user.id}")

        messages.success(self.request, f'Клиент "{self.object}" успешно обновлен!')
        return reverse_lazy('mailing:client_detail', kwargs={'pk': self.object.pk})

    def form_invalid(self, form):
        """
        Обработка невалидной формы.

        Args:
            form: Невалидная форма получателя

        Returns:
            HttpResponse: Результат обработки
        """
        messages.error(self.request, 'Пожалуйста, исправьте ошибки в форме.')
        return super().form_invalid(form)


class ClientDeleteView(LoginRequiredMixin, DeleteView):
    """
    Удаление получателя.

    При удалении:
    - Проверяет права доступа
    - Очищает кеш списка получателей пользователя
    - Очищает кеш статистики главной страницы
    """
    model = Client
    template_name = 'mailing/client_confirm_delete.html'
    success_url = reverse_lazy('mailing:client_list')

    def dispatch(self, request, *args, **kwargs):
        """
        Проверка прав доступа перед обработкой запроса.

        Args:
            request: HTTP запрос

        Returns:
            HttpResponse: Результат проверки
        """
        obj = self.get_object()
        if request.user != obj.owner:
            raise PermissionDenied("У вас нет прав для удаления этого клиента")
        return super().dispatch(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        """
        Удаление получателя с очисткой кеша.

        Args:
            request: HTTP запрос

        Returns:
            HttpResponse: Результат удаления
        """
        self.object = self.get_object()
        client_name = str(self.object)

        response = super().delete(request, *args, **kwargs)

        # Очищаем кеш
        self.clear_cache()

        messages.success(request, f'Клиент "{client_name}" успешно удален!')
        return response

    def clear_cache(self):
        """Очистка кеша после удаления получателя"""
        # Очищаем кеш списка получателей пользователя
        cache.delete(f'user_{self.request.user.id}_clients')
        print(f"🗑️ КЭШ: Очищен кеш списка получателей пользователя {self.request.user.id}")

        # Очищаем кеш статистики главной страницы
        cache.delete('home_stats')
        print("🗑️ КЭШ: Очищен кеш главной страницы")


class AttemptListView(LoginRequiredMixin, ListView):
    """
    Список попыток рассылок (статистика).

    Использует кеширование для хранения статистики.
    Время кеширования: 5 минут (300 секунд)
    """
    model = Attempt
    template_name = 'mailing/attempt_list.html'
    context_object_name = 'attempts'
    paginate_by = 20

    def get_queryset(self):
        """
        Получение списка попыток с кешированием.

        Returns:
            list: Список попыток
        """
        user = self.request.user
        cache_key = f'user_{user.id}_attempts'

        if settings.CACHE_ENABLED:
            attempts = cache.get(cache_key)
            if attempts is not None:
                print(f"✅ КЭШ: Список попыток для пользователя {user.id} получен из кэша")
                return attempts
            else:
                print(f"📊 БД: Загрузка списка попыток для пользователя {user.id} (кеш MISS)")

        # Получаем данные из базы данных
        if user.has_perm('mailing.can_view_all_mailings'):
            attempts = list(Attempt.objects.all().select_related('mailing', 'client'))
        else:
            attempts = list(Attempt.objects.filter(mailing__owner=user).select_related('mailing', 'client'))

        # Сохраняем в кеш
        if settings.CACHE_ENABLED:
            cache.set(cache_key, attempts, timeout=300)
            print(f"💾 КЭШ: Список попыток для пользователя {user.id} сохранен в кеш")

        return attempts

    def get_context_data(self, **kwargs):
        """
        Добавляет статистику в контекст.

        Returns:
            dict: Контекст с дополнительными данными
        """
        context = super().get_context_data(**kwargs)

        user = self.request.user

        # Считаем статистику
        if user.has_perm('mailing.can_view_all_mailings'):
            context['total_attempts'] = Attempt.objects.count()
            context['success_attempts'] = Attempt.objects.filter(status='success').count()
            context['failed_attempts'] = Attempt.objects.filter(status='failed').count()
        else:
            context['total_attempts'] = Attempt.objects.filter(mailing__owner=user).count()
            context['success_attempts'] = Attempt.objects.filter(mailing__owner=user, status='success').count()
            context['failed_attempts'] = Attempt.objects.filter(mailing__owner=user, status='failed').count()

        return context
