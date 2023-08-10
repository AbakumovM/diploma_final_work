from django.http import JsonResponse
from django.shortcuts import render
from django.contrib.auth.password_validation import validate_password
from rest_framework.views import APIView

from backend.admin import CustemUserAdmin
from backend.models import CustomUser
from backend.serializers import UserSerializer

class RegisterAccount(APIView):

    def post(self, request, *args, **kwargs):

        if {'email', 'password', 'company', 'position'}.issubset(request.data):

            try:
                validate_password(request.data['password'])
            except Exception as pass_error:
                errors = [error for error in pass_error]
                return JsonResponse({'Status': False, 'Errors': {'password': errors}})

            else:
                user_serial = UserSerializer(data=request.data)
                if user_serial.is_valid():
                    user = user_serial.save()
                    user.set_password(request.data['password'])
                    user.save()
                    return JsonResponse({'Status': True})
                else:
                    return JsonResponse({'Status': False, 'Errors': user_serial.errors})

        return JsonResponse({'Status': False, 'Errors': 'Указаны не все аргументы'})


        



class PartnerUpdate(APIView):

    def post(self, request, *args, **kwargs):
        pass


