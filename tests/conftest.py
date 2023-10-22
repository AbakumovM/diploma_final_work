import uuid
import pytest
from rest_framework.test import APIClient
from model_bakery import baker
from rest_framework.authtoken.models import Token

from backend.models import Category, CustomUser, Product, Shop


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def shop_create():
    def create(*args, **kwargs):
        return baker.make(Shop, *args, **kwargs)

    return create


@pytest.fixture
def products_create():
    def create(*args, **kwargs):
        return baker.make(Product, *args, **kwargs)

    return create


@pytest.fixture
def category_create():
    def create(*args, **kwargs):
        return baker.make(Category, *args, **kwargs)

    return create


@pytest.fixture
def test_password():
    return "strong-test-pass"


@pytest.fixture
def create_user(db, django_user_model, test_password):
    def make_user(**kwargs):
        kwargs["password"] = test_password
        if "username" not in kwargs:
            kwargs["username"] = str(uuid.uuid4())
        return django_user_model.objects.create_user(**kwargs)

    return make_user
