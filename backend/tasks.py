from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.dispatch import receiver, Signal
from django_rest_passwordreset.views import reset_password_request_token
from celery import shared_task
import PIL.Image as Image
import io
import requests
import base64
import os
from django.core.files import File

from backend.models import AvatarUser, ConfirmEmailToken, CustomUser, ProductInfo


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


@shared_task()
def upload_image(data):
    user_id = data["user_id"]

    byte_data = data["avatar"].encode(encoding="utf-8")
    b = base64.b64decode(byte_data)
    img = Image.open(io.BytesIO(b))
    img.save(data["name"], format=img.format)

    with open(data["name"], "rb") as file:
        picture = File(file)

        instance = AvatarUser(user_id=user_id, avatar=picture)
        instance.save()

    os.remove(data["name"])


@shared_task
def download_image(data):
    response = requests.get(data["url"])
    path = f"media/products_image/shop_id_{data['shop_id']}"
    if not os.path.exists(path):
        os.makedirs(path)
    with open(f'{path}/{data["filename"]}', "wb") as f:
        f.write(response.content)
        ProductInfo.objects.filter(external_id=data["product_id"]).update(
            image=data["filename"]
        )
