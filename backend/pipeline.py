from .models import CustomUser
import vk_api


def save_to_email(backend, user, response, *args, **kwargs):
    print(kwargs)
    print(user)
    token = response["access_token"]

    print(token)
