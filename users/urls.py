# users/urls.py
"""
Маршруты (URL-адреса) для приложения пользователей.

Определяет пути к страницам регистрации, входа, выхода и профиля.
"""

from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    # Регистрация нового пользователя
    path('register/', views.UserRegistrationView.as_view(), name='register'),

    # Вход в систему
    path('login/', views.UserLoginView.as_view(), name='login'),

    # Выход из системы
    path('logout/', views.UserLogoutView.as_view(), name='logout'),

    # Профиль пользователя (редактирование)
    path('profile/<int:pk>/', views.UserProfileView.as_view(), name='profile'),
]
