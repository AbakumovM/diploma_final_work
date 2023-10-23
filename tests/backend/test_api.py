import pytest
from rest_framework.test import APIClient
from model_bakery import baker

from backend.models import CustomUser, Shop
from rest_framework.authtoken.models import Token


pytestmark = pytest.mark.django_db


class TestRegisterUser:
    endpoint = "/api/v1/user/register"

    #     def test_post_user_success(self, client):
    #         response = client.post(
    #             self.endpoint,
    #             {
    #                 "first_name": "1",
    #                 "last_name": "2",
    #                 "email": "abs@mail.com",
    #                 "password": "7667766Cvb",
    #                 "company": "ass",
    #             },
    #         )
    #         data = response.json()
    #         assert data["user"]["first_name"] == "1"
    #         assert data["Status"] == True
    #         assert response.status_code == 200

    #     def test_post_user_error_not_all_data(self, client):
    #         response = client.post(
    #             self.endpoint,
    #             {
    #                 "first_name": "1",
    #                 "last_name": "2",
    #                 "email": "abs@mail.com",
    #                 "company": "ass",
    #             },
    #         )
    #         data = response.json()
    #         assert response.status_code == 400
    #         assert data["Status"] == False
    #         assert data["Errors"] == "Указаны не все аргументы"

    #     def test_post_user_error_password(self, client):
    #         response = client.post(
    #             self.endpoint,
    #             {
    #                 "first_name": "1",
    #                 "last_name": "2",
    #                 "email": "abs@mail.com",
    #                 "password": "7667",
    #                 "company": "ass",
    #             },
    #         )
    #         data = response.json()
    #         assert response.status_code == 400
    #         assert data["Status"] == False

    #     def test_post_error_email(self, client):
    #         response = client.post(
    #             self.endpoint,
    #             {
    #                 "first_name": "1",
    #                 "last_name": "2",
    #                 "email": "abs@as",
    #                 "password": "7667766Cvb",
    #                 "company": "ass",
    #             },
    #         )
    #         data = response.json()
    #         assert data["Status"] == False
    #         assert response.status_code == 400

    def test_delete_user(self, client, create_user):
        user = create_user(email="user@example.com", type="buyer", is_active=True)
        user_1 = create_user(email="user2@example.com", type="buyer", is_active=True)
        all_user = CustomUser.objects.count()
        response = client.delete(self.endpoint, data={"id": user.id})
        all_user_delete = CustomUser.objects.count()
        assert response.status_code == 204
        assert all_user != all_user_delete


class TestShop:
    endpoint = "/api/v1/shops"

    def test_shop(self, client, shop_create):
        shops = shop_create(name="Test_shop")
        response = client.get(self.endpoint)
        assert response.status_code == 200
        data = response.json()
        assert shops.name == data[0]["name"]
        assert (len(data)) != 5
        assert (len(data)) == 1

    def test_list_shop(self, client, shop_create):
        shops = shop_create(_quantity=5)
        response = client.get(self.endpoint)
        assert response.status_code == 200
        data = response.json()
        assert (len(data)) == len(shops)


class TestProduct:
    endpoint = "/api/v1/product/all"

    def test_product(self, client, products_create, category_create):
        category = category_create()
        product = products_create(category_id=category.id, name="iphone")
        response = client.get(self.endpoint)
        assert response.status_code == 200
        data = response.json()
        assert data[0]["name"] == product.name


class TestUserDetails:
    endpoint = "/api/v1/users/details"

    def test_post_user_first_name(self, client, create_user):
        user = create_user(email="user@example.com", type="buyer", is_active=True)
        token = Token.objects.create(user=user)
        response = client.post(
            self.endpoint,
            headers={"Authorization": f"Token {token.key}"},
            data={"first_name": "test"},
        )
        assert response.status_code == 200
        data = response.json()
        print(data)
        assert data["user"]["first_name"] == "test"

    def test_post_user_password_error(self, client, create_user):
        user = create_user(email="user1@example.com", type="buyer", is_active=True)
        token = Token.objects.create(user=user)
        response = client.post(
            self.endpoint,
            headers={"Authorization": f"Token {token.key}"},
            data={"password": "test"},
        )
        assert response.status_code == 400
        data = response.json()
        assert data["Status"] == False

    def test_post_user_email_error(self, client, create_user):
        user_1 = create_user(email="aaa@mail.com", type="buyer", is_active=True)
        user_2 = create_user(email="asd@mail.ru", type="buyer", is_active=True)
        token = Token.objects.create(user=user_2)
        response = client.post(
            self.endpoint,
            headers={"Authorization": f"Token {token.key}"},
            data={"email": "aaa@mail.com"},
        )
        assert response.status_code == 400
        data = response.json()
        assert data["Status"] == False


class TestCategory:
    endpoint = "/api/v1/category"

    def test_get_category_list(self, client, category_create):
        category = category_create(_quantity=5)
        response = client.get(self.endpoint)
        assert response.status_code == 200
        data = response.json()
        assert len(category) == len(data)

    def test_get_category_name(self, client, category_create):
        category = category_create(name="Test12")
        response = client.get(self.endpoint)
        assert response.status_code == 200
        data = response.json()
        assert category.name == data[0]["name"]


class TestPartnerState:
    endpoint = "/api/v1/partner/state"

    def test_post_state(self, client, create_user, shop_create):
        user = create_user(email="user@example.com", type="shop", is_active=True)
        shop = shop_create(user_id=user.id, state=True)
        token = Token.objects.create(user=user)
        response = client.post(
            self.endpoint,
            headers={"Authorization": f"Token {token.key}"},
            data={"state": "False"},
        )
        shops = Shop.objects.get(user_id=user.id)
        assert response.status_code == 200
        data = response.json()
        shop_after = Shop.objects.get(user_id=user.id)
        assert shop_after.state != shop.state

    def test_post_user_not_shop(self, create_user, client, shop_create):
        user = create_user(email="user@example.com", type="buyer", is_active=True)
        token = Token.objects.create(user=user)
        shop = shop_create(user_id=user.id, state=True)
        response = client.post(
            self.endpoint,
            headers={"Authorization": f"Token {token.key}"},
            data={"state": "False"},
        )
        assert response.status_code == 403
        data = response.json()
        assert data["Status"] == False

    def test_get_shop(self, client, shop_create, create_user):
        user = create_user(email="user@example.com", type="shop", is_active=True)
        shop = shop_create(user_id=user.id, state=True)
        token = Token.objects.create(user=user)
        response = client.get(
            self.endpoint, headers={"Authorization": f"Token {token.key}"}
        )
        assert response.status_code == 200
        data = response.json()
        print(data)
        assert shop.name == data["Shop_info"]["name"]


class TestContact:
    endpoint = "/api/v1/contacts"

    def test_post_contact(self, create_user, client):
        user = create_user(email="user@example.com", type="buyer", is_active=True)
        token = Token.objects.create(user=user)
        response = client.post(
            self.endpoint,
            headers={"Authorization": f"Token {token.key}"},
            data={"city": "Ekb", "street": "test", "house": "1", "phone": "900"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["contact"]["city"] == "Ekb"

    def test_post_contact_error_not_data(self, create_user, client):
        user = create_user(email="user@example.com", type="buyer", is_active=True)
        token = Token.objects.create(user=user)
        response = client.post(
            self.endpoint,
            headers={"Authorization": f"Token {token.key}"},
            data={"street": "test", "house": "1", "phone": "900"},
        )
        assert response.status_code == 400
        data = response.json()
        print(data)
        assert data["Error"] == "Указаны не все необходимые аргументы"

    def test_put_contact(self, client, create_user, contact_create):
        user = create_user(email="user@example.com", type="buyer", is_active=True)
        token = Token.objects.create(user=user)
        contact = contact_create(user_id=user.id)
        response = client.put(
            self.endpoint,
            headers={"Authorization": f"Token {token.key}"},
            data={"id": contact.id, "city": "Moscow"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["contact"]["city"] == "Moscow"
        assert data["contact"]["city"] != contact.city

    def test_delete_contact(self, client, create_user, contact_create):
        user = create_user(email="user@example.com", type="buyer", is_active=True)
        token = Token.objects.create(user=user)
        contact = contact_create(user_id=user.id)
        response = client.delete(
            self.endpoint,
            headers={"Authorization": f"Token {token.key}"},
            data={"id": contact.id},
        )
        assert response.status_code == 204

    def test_delete_contact_error_id(self, client, create_user, contact_create):
        user = create_user(email="user@example.com", type="buyer", is_active=True)
        token = Token.objects.create(user=user)
        contact = contact_create(user_id=user.id)
        response = client.delete(
            self.endpoint,
            headers={"Authorization": f"Token {token.key}"},
            data={"id": "7"},
        )
        response_2 = client.delete(
            self.endpoint,
            headers={"Authorization": f"Token {token.key}"},
            data={"id": "hello"},
        )
        assert response.status_code == 400
        assert response_2.status_code == 400
        data = response.json()
        data_2 = response_2.json()
        assert data["Status"] == False
        assert data_2["Status"] == False


class TestProductInfo:
    endpoint = "/api/v1/products"

    def test_productinfo_shop(
        self, shop_create, client, product_info_create, products_create, category_create
    ):
        shop = shop_create()
        category = category_create()
        product = products_create(category_id=category.id)
        product_info = product_info_create(shop_id=shop.id, product_id=product.id)
        response = client.get(self.endpoint, data={"shop_id": product_info.shop_id})
        assert response.status_code == 200
        data = response.json()
        print(data)
        assert data["Data"][0]["model"] == product_info.model

    def test_productinfo_category(
        self, shop_create, client, product_info_create, products_create, category_create
    ):
        shop = shop_create()
        category = category_create()
        product = products_create(category_id=category.id)
        product_info = product_info_create(shop_id=shop.id, product_id=product.id)
        response = client.get(self.endpoint, data={"category_id": category.id})
        assert response.status_code == 200
        data = response.json()
        print(data)
        assert data["Data"][0]["model"] == product_info.model
