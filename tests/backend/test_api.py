import pytest
from rest_framework.test import APIClient
from model_bakery import baker

from backend.models import CustomUser, Shop




@pytest.fixture
def shop_create():
    def create(*args, **kwargs):
        return baker.make(Shop, *args, **kwargs)
    return create
pytestmark = pytest.mark.django_db

class TestRegisterUser:

    endpoint = "/api/v1/user/register"


    def test_post_user_success(self, client):       
        response = client.post(self.endpoint, {
            "first_name": "1", 
            "last_name": "2",
            "email": "abs@mail.com",
            "password": "7667766Cvb", 
            "company": "ass",
            
        })
        data = response.json()
        assert data["user"]["first_name"] == "1" 
        assert data["Status"] == True
        assert response.status_code == 200

    def test_post_user_error_not_all_data(self, client):
        response = client.post(self.endpoint, {
            "first_name": "1", 
            "last_name": "2",
            "email": "abs@mail.com",
            "company": "ass",
            
        })
        data = response.json()
        assert response.status_code == 400
        assert data["Status"] == False
        assert data["Errors"] == "Указаны не все аргументы"

    def test_post_user_error_password(self, client):
        response = client.post(self.endpoint, {
            "first_name": "1", 
            "last_name": "2",
            "email": "abs@mail.com",
            "password": "7667", 
            "company": "ass",
            
        })
        data = response.json()
        assert response.status_code == 400
        assert data["Status"] == False
        
    def test_post_error_email(self, client):
        response = client.post(self.endpoint, {
            "first_name": "1", 
            "last_name": "2",
            "email": "abs@as",
            "password": "7667766Cvb", 
            "company": "ass",
            
        })
        data = response.json() 
        assert data["Status"] == False
        assert response.status_code == 400
    
    def test_delete_user(self, client):
        pass
        # user = CustomUser.objects.create(first_name="1", last_name="2", email="abs@mail.com",password="7667766Cvb", company="ass",)
        
        # response = client.delete(self.endpoint, {"id": })
        # assert response.status_code == 204
        # data = response.json()
        # assert data["Status"] == True

class TestShop:

    endpoint = "/api/v1/shops"

    def test_list_shop(self, client, shop_create):
        shops = shop_create(_quantity=5)
        response = client.get(self.endpoint)
        assert response.status_code == 200
        data = response.json()
        assert shops[0].name == data[0]["name"]
        assert(len(data)) == 5
        assert(len(data)) != 1
    