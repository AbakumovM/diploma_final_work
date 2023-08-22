from distutils.util import strtobool
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
    Contact,
    CustomUser,
    Parameter,
    Product,
    ProductParameter,
    Shop,
    ProductInfo,
)
from backend.serializers import (
    CategorySerializer,
    ContactSerializer,
    ProductSerializer,
    ShopSerializer,
    UserSerializer,
)
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


class ProductView(ListAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer


class UserDetails(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        data = UserSerializer(request.user)
        return JsonResponse({"USER": data.data})

    def post(self, request, *args, **kwargs):
        if {"password"}.issubset(request.data):
            try:
                validate_password(request.data["password"])
            except Exception as pass_error:
                return JsonResponse(
                    {
                        "Status": False,
                        "Errors": {"password": [error for error in pass_error]},
                    }
                )
            else:
                request.user.set_password(request.data["password"])

        user_serializer = UserSerializer(request.user, data=request.data, partial=True)
        if user_serializer.is_valid():
            user_serializer.save()
            return JsonResponse({"status": True, "massege": "success"})
        else:
            return JsonResponse({"Status": False, "Errors": user_serializer.errors})


class CategoryView(ListAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class PartnerState(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        if request.user.type != "saler":
            return JsonResponse(
                {"Status": False, "Errors": "you not seler"}, status=403
            )

        state = request.user.shop
        serializer_shop = ShopSerializer(state)

        return JsonResponse({"status": True, "shop": serializer_shop.data["state"]})

    def post(self, request, *args, **kwargs):
        if request.user.type != "saler":
            return JsonResponse(
                {"Status": False, "Errors": "you not seler"}, status=403
            )

        state = request.data.get("state")
        if state:
            try:
                Shop.objects.filter(user_id=request.user.id).update(
                    state=strtobool(request.data["state"])
                )
                return JsonResponse({"status": True})
            except ValueError as e:
                return JsonResponse({"status": False, "Error": str(e)})
        else:
            return JsonResponse({"status": False, "Error": "didn't pass all arguments"})


class ContactView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        contacts = Contact.objects.filter(user_id=request.user.id)
        if contacts:
            serializer = ContactSerializer(contacts, many=True)
            return JsonResponse({"status": True, "answer": serializer.data})
        return JsonResponse({"status": False, "error": "not info"})

    def post(self, request, *args, **kwargs):
        if {"city", "street", "house", "phone"}.issubset(request.data):
            request.data.update({"user": request.user.id})
            serializer_contacts = ContactSerializer(data=request.data)
            if serializer_contacts.is_valid():
                serializer_contacts.save()
                return JsonResponse({"status": True, "answer": "success"})
            else:
                return JsonResponse(
                    {"Status": False, "Errors": serializer_contacts.errors}
                )

        return JsonResponse({"status": False, "error": "didn't pass all arguments"})

    def put(self, request, *args, **kwargs):
        contact_id = request.data.get("id")
        if contact_id and contact_id.isdigit():
            contact = Contact.objects.filter(id=contact_id, user_id=request.user.id)[0]
            if contact:
                serializer = ContactSerializer(contact, data=request.data, partial=True)
                if serializer.is_valid():
                    serializer.save()
                    return JsonResponse({"status": True})
                else:
                    return JsonResponse({"status": False, "errors": serializer.errors})
            return JsonResponse({"status": False, "error": "not id in contacts"})
        return JsonResponse({"status": False, "error": "didn't pass all arguments"})

    def delete(self, request, *args, **kwargs):
        pass
