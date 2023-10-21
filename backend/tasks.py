from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.dispatch import receiver, Signal
from django_rest_passwordreset.signals import reset_password_token_created
from celery import shared_task

from backend.models import ConfirmEmailToken, CustomUser


@shared_task()
def password_reset_token_created_task(reset_password_token, **kwargs):
    """
    Отправляем письмо с токеном для сброса пароля
    When a token is created, an e-mail needs to be sent to the user
    :param sender: View Class that sent the signal
    :param instance: View Instance that sent the signal
    :param reset_password_token: Token Model Object
    :param kwargs:
    :return:
    """
    # send an e-mail to the user

    msg = EmailMultiAlternatives(
        # title:
        f"Сброс пароля для {reset_password_token.user}",
        # message:
        f"Ваш токен для сброс пароля и создания нового: {reset_password_token.key}",
        # from:
        settings.EMAIL_HOST_USER,
        # to:
        [reset_password_token.user.email],
    )
    msg.send()


@shared_task()
def new_user_registered_task(user_id, **kwargs):
    """
    Отправляем письмо на почту для подтверждения регистрации через токен.
    """
    # send an e-mail to the user
    token, _ = ConfirmEmailToken.objects.get_or_create(user_id=user_id)

    msg = EmailMultiAlternatives(
        # title:
        f"Подтвердите регистранию по почте {token.user.email}",
        # message:
        f"Приветствуем {token.user.first_name}! Ваш токен для подтверждения регистрации: {token.key}",
        # from:
        settings.EMAIL_HOST_USER,
        # to:
        [token.user.email],
    )
    msg.send()


@shared_task()
def new_order_task(user_id, **kwargs):
    """
    Отправяем письмо при изменении статуса заказа.
    """
    # send an e-mail to the user
    user = CustomUser.objects.get(id=user_id)

    msg = EmailMultiAlternatives(
        # title:
        f"Обновление статуса заказа",
        # message:
        "Заказ сформирован",
        # from:
        settings.EMAIL_HOST_USER,
        # to:
        [user.email],
    )
    msg.send()