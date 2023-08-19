from rest_framework.generics import ListAPIView
from urllib.parse import urlparse
from django.http import JsonResponse
from django.shortcuts import render
from django.contrib.auth.password_validation import validate_password
from requests import Response, get
from django.core.validators import URLValidator
from rest_framework.views import APIView
from django.contrib.auth import authenticate
from rest_framework.authentication import SessionAuthentication
from rest_framework.authtoken.models import Token
import yaml
from backend.admin import CustemUserAdmin
from backend.models import (
    Category,
    CustomUser,
    Parameter,
    Product,
    ProductParameter,
    Shop,
    ProductInfo,
)
from backend.serializers import ShopSerializer, UserSerializer
from rest_framework.permissions import IsAuthenticated


class RegisterAccount(APIView):
    def post(self, request, *args, **kwargs):
        if {"email", "password", "company", "position", "type"}.issubset(request.data):
            try:
                validate_password(request.data["password"])
            except Exception as pass_error:
                errors = [error for error in pass_error]
                return JsonResponse({"Status": False, "Errors": {"password": errors}})

            else:
                user_serial = UserSerializer(data=request.data)
                if user_serial.is_valid():
                    user = user_serial.save()
                    user.set_password(request.data["password"])
                    user.save()
                    return JsonResponse({"Status": True})
                else:
                    return JsonResponse({"Status": False, "Errors": user_serial.errors})

        return JsonResponse({"Status": False, "Errors": "Указаны не все аргументы"})

    def delete(self, request, pk):
        CustomUser.objects.filter(id=pk).delete()
        return JsonResponse({"users": "True"})


class AutUser(APIView):
    def get(self, request, *args, **kwargs):
        users = CustomUser.objects.all().values()

        return JsonResponse({"users": list(users)})

    def post(self, request, *args, **kwargs):
        if {"email", "password"}.issubset(request.data):
            user = authenticate(
                request=request,
                username=request.data["email"],
                password=request.data["password"],
            )

            if user is not None:
                if user.is_active:
                    token, _ = Token.objects.get_or_create(user=user)

                    return JsonResponse({"Status": True, "Token": token.key})

            return JsonResponse({"Status": False, "Errors": "Не удалось авторизовать"})

        return JsonResponse(
            {"Status": False, "Errors": "Не указаны все необходимые аргументы"}
        )


class PartnerUpdate(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        if request.user.type != "saler":
            return JsonResponse({"Status": False, "Errors": "you not seler"})

        # url = request.data.get('url')
        # if url:
        #     try:
        #         valid_url = URLValidator()
        #         valid_url(url)
        #     except Exception  as url_error:
        #             return JsonResponse({"Status": False, "Errors": {"url": [error for error in url_error]}})

        # data = get(url).content
        # data_js = yaml.load(data, Loader=yaml.SafeLoader)
        # print(data_js)
        with open("data/shop1.yaml", "r") as f:
            data = yaml.load(f, Loader=yaml.SafeLoader)
            shop = Shop.objects.get_or_create(
                name=data["shop"], user_id=request.user.id
            )
            for category in data["categories"]:
                category_object, _ = Category.objects.get_or_create(
                    id=category["id"], name=category["name"]
                )
                category_object.shops.add(shop[0].id)
                category_object.save()

            for item in data["goods"]:
                product = Product.objects.get_or_create(
                    name=item["name"], id=item["id"], category_id=item["category"]
                )
                prodinfo = ProductInfo.objects.get_or_create(
                    external_id=item["id"],
                    product_id=product[0].id,
                    model=item["model"],
                    quantity=item["quantity"],
                    price=item["price"],
                    price_rrc=item["price_rrc"],
                    shop_id=shop[0].id,
                )
                for name, value in item["parameters"].items():
                    parameter_object = Parameter.objects.get_or_create(name=name)
                    ProductParameter.objects.create(
                        product_info_id=prodinfo[0].id,
                        parametr_id=parameter_object[0].id,
                        value=value,
                    )

        return JsonResponse({"Status": True, "Errors": "Добро пожаловать"})


class ShopsView(ListAPIView):

   queryset = Shop.objects.all()
   serializer_class = ShopSerializer

