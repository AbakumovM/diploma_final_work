from django.http import JsonResponse
from django.shortcuts import render
from django.contrib.auth.password_validation import validate_password
from requests import Response
from rest_framework.views import APIView
from django.contrib.auth import authenticate

from rest_framework.authtoken.models import Token
from backend.admin import CustemUserAdmin
from backend.models import CustomUser
from backend.serializers import UserSerializer


class RegisterAccount(APIView):
    def post(self, request, *args, **kwargs):
        if {"email", "password", "company", "position"}.issubset(request.data):
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
                    user.is_active = True
                    user.save()
                    return JsonResponse({"Status": True})
                else:
                    return JsonResponse({"Status": False, "Errors": user_serial.errors})

        return JsonResponse({"Status": False, "Errors": "Указаны не все аргументы"})


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
    def post(self, request, *args, **kwargs):
        pass
