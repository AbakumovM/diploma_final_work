from distutils.util import strtobool
from django.db import IntegrityError
from rest_framework.generics import ListAPIView
from django.http import JsonResponse
from django.contrib.auth.password_validation import validate_password
from requests import Response, get
from django.contrib.auth.views import LoginView
from django.db.models import Q, Sum, F
from django.core.validators import URLValidator
from rest_framework.views import APIView
from django.contrib.auth import authenticate
from rest_framework.authentication import SessionAuthentication
from rest_framework.authtoken.models import Token
import yaml
from django.core.mail import send_mail
from backend.models import (
    Category,
    Contact,
    CustomUser,
    Order,
    OrderItem,
    Parameter,
    Product,
    ProductParameter,
    Shop,
    ProductInfo,
    ConfirmEmailToken,
)
from backend.serializers import (
    CategorySerializer,
    ContactSerializer,
    OrderItemSerializer,
    OrderSerializer,
    ProductInfoSerializer,
    ProductSerializer,
    ShopSerializer,
    UserSerializer,
)
from rest_framework.permissions import IsAuthenticated

from backend.signals import new_user_registered, new_order


class RegisterAccount(APIView):
    def get(self, request, *args, **kwargs):
        user = CustomUser.objects.all().values()
        return JsonResponse({"user": [*user]})

    def post(self, request, *args, **kwargs):
        if {"email", "password", "company", "type"}.issubset(request.data):
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
                    new_user_registered.send(sender=self.__class__, user_id=user.id)
                    return JsonResponse({"Status": True})
                else:
                    return JsonResponse({"Status": False, "Errors": user_serial.errors})

        return JsonResponse({"Status": False, "Errors": "Указаны не все аргументы"})

    def delete(self, request, *args, **kwargs):
        try:
            CustomUser.objects.get(id=request.data["id"]).delete()
        except Exception as error:
            return JsonResponse({"Status": False, "Errors": str(error)})
        return JsonResponse({"users": "True"})


class AutUser(APIView, LoginView):
    def post(self, request, *args, **kwargs):
        if {"email", "password"}.issubset(request.data):
            user = authenticate(
                request=request,
                username=request.data["email"],
                password=request.data["password"],
            )
            if user is not None and user.is_active:
                token = Token.objects.get_or_create(user=user)

                return JsonResponse({"Status": True, "Token": token[0].key})

            return JsonResponse({"Status": False, "Errors": "Не удалось авторизовать"})

        return JsonResponse(
            {"Status": False, "Errors": "Укажите email и password от личного кабинета."}
        )


class ConfirmAccount(APIView):
    """
    Класс для подтверждения почтового адреса
    """

    def post(self, request, *args, **kwargs):


        if {"email", "token"}.issubset(request.data):

            token = ConfirmEmailToken.objects.filter(user__email=request.data["email"],
                                                     key=request.data["token"]).first()
            if token:
                token.user.is_active = True
                token.user.save()
                token.delete()
                return JsonResponse({"Status": True})
            else:
                return JsonResponse({"Status": False, "Errors": "Неправильно указан токен или email"})

        return JsonResponse({"Status": False, "Errors": "Не указаны все необходимые аргументы"})



class PartnerUpdate(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        if request.user.type != "shop":
            return JsonResponse({"Status": False, "Errors": "only shop"})

        url = request.data.get("url")
        if url:
            try:
                URLValidator(url)
            except Exception as url_error:
                return JsonResponse(
                    {"Status": False, "Errors": {"url": [error for error in url_error]}}
                )
            else:
                data = get(url).content
                data_dict = yaml.load(data, Loader=yaml.Loader)
                shop = Shop.objects.get_or_create(
                    name=data_dict["shop"], user_id=request.user.id
                )
                for category in data_dict["categories"]:
                    category_object, _ = Category.objects.get_or_create(
                        id=category["id"], name=category["name"]
                    )
                    category_object.shops.add(shop[0].id)
                    category_object.save()

                for item in data_dict["goods"]:
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

        return JsonResponse({"Status": True, "Answer": "Информация успешно добавлена!"})


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
        if request.user.type != "shop":
            return JsonResponse(
                {"Status": False, "Errors": "only shop"}, status=403
            )

        state = request.user.shop
        serializer_shop = ShopSerializer(state)
        print(state)

        return JsonResponse({"status": True, "state": serializer_shop.data["state"]})

    def post(self, request, *args, **kwargs):
        if request.user.type != "shop":
            return JsonResponse(
                {"Status": False, "Errors": "only shop"}, status=403
            )

        state = request.data.get("state")
        if state:
            try:
                Shop.objects.filter(user_id=request.user.id).update(
                    state=strtobool(request.data["state"])
                )
                return JsonResponse({"status": True, "state": state})
            except ValueError as e:
                return JsonResponse({"status": False, "Error": str(e)})
        else:
            return JsonResponse({"status": False, "Error": "didn't pass all arguments"})


class ContactView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        if request.user.type != "buyer":
            return JsonResponse({"Status": False, "Error": "only buyer"})
    
        contacts = Contact.objects.filter(user_id=request.user.id)
        if contacts:
            serializer = ContactSerializer(contacts, many=True)
            return JsonResponse({"status": True, "answer": serializer.data})
        return JsonResponse({"status": False, "error": "not info"})

    def post(self, request, *args, **kwargs):
        if request.user.type != "buyer":
            return JsonResponse({"Status": False, "Error": "only buyer"})

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
        if request.user.type != "buyer":
            return JsonResponse({"Status": False, "Error": "only buyer"})

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
        if request.user.type != "buyer":
            return JsonResponse({"Status": False, "Error": "only buyer"})
        
        contact_id = request.data.get("id")
        if contact_id.isdigit():
            try:
                Contact.objects.get(id=contact_id).delete()
                return JsonResponse({"status": True, "answer": "success"})
            except Exception as error:
                return JsonResponse(
                    {"status": False, "error": "id is not in the database"}
                )
        return JsonResponse({"status": False, "error": "no data available"})


class BasketView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        basket = Order.objects.filter(
            user_id=request.user.id, status="basket").prefetch_related(
            "ordered_items__product_info__product__category",
            "ordered_items__product_info__product_param__parameter").annotate(
            total_sum=Sum(F("ordered_items__quantity") * F("ordered_items__product_info__price"))).distinct()

        serializer = OrderSerializer(basket, many=True)
        return JsonResponse({"status": True, "answer": serializer.data})


    def post(self, request, *args, **kwargs):
        items_sting = request.data.get("items")
        if items_sting:
            
            basket, _ = Order.objects.get_or_create(
                user_id=request.user.id, status="basket"
            )
            objects_created = 0
            for order_item in items_sting:
                order_item.update({"order": basket.id})
                serializer = OrderItemSerializer(data=order_item)
                if serializer.is_valid():
                    try:
                        serializer.save()
                    except IntegrityError as error:
                        return JsonResponse({"Status": False, "Eors": str(error)})
                    else:
                        objects_created += 1

                else:
                    return JsonResponse(
                        {"Status": False, "Errors": serializer.errors}
                    )

                return JsonResponse(
                    {"Status": True, "Создано объектов": objects_created}
                )
        return JsonResponse(
            {"Status": False, "Errors": "Не указаны все необходимые аргументы"}
        )

    def put(self, request, *args, **kwargs):
        items_sting = request.data.get("items")
        if items_sting:
            basket, _ = Order.objects.get_or_create(
                    user_id=request.user.id, status="basket"
                )
            objects_updated = 0
            for order_item in items_sting:
                if (
                    type(order_item["id"]) == int
                    and type(order_item["quantity"]) == int
                ):
                    objects_updated += OrderItem.objects.filter(
                        order_id=basket.id, id=order_item["id"]
                    ).update(quantity=order_item["quantity"])

            return JsonResponse(
                {"Status": True, "Обновлено объектов": objects_updated}
            )
        
    def delete(self, request, *args, **kwargs):
        id_del = request.data.get("items")
        if id_del:
            items_list = id_del.split(',')
            basket, _ = Order.objects.get_or_create(user_id=request.user.id, status='basket')
            query = Q()
            objects_deleted = False
            for order_item_id in items_list:
                if order_item_id.isdigit():
                    query = query | Q(order_id=basket.id, id=order_item_id)
                    objects_deleted = True

            if objects_deleted:
                deleted_count = OrderItem.objects.filter(query).delete()[0]
                return JsonResponse({"Status": True, "Удалено объектов": deleted_count})
        return JsonResponse({"Status": False, "Errors": "Не указаны все необходимые аргументы"})


class OrderView(APIView):
    """
    Класс для получения и размешения заказов пользователями
    """
    permission_classes = (IsAuthenticated,)
    
    def get(self, request, *args, **kwargs):

        order = (
            Order.objects.filter(user_id=request.user.id)
            .exclude(status="basket")
            .prefetch_related(
                "ordered_items__product_info__product__category",
                "ordered_items__product_info__product_param__parameter",
            )
            .select_related("contact")
            .annotate(
                total_sum=Sum(
                    F("ordered_items__quantity")
                    * F("ordered_items__product_info__price")
                )
            )
            .distinct()
        )

        serializer = OrderSerializer(order, many=True)
        return JsonResponse({"status": True, "Orders": serializer.data})

    # разместить заказ из корзины
    def post(self, request, *args, **kwargs):
        if {"id", "contact"}.issubset(request.data):
            if request.data["id"].isdigit():
                try:
                    is_updated = Order.objects.filter(
                        user_id=request.user.id, id=request.data["id"]
                    ).update(contact_id=request.data["contact"], status="new")
                except IntegrityError as error:
                    print(error)
                    return JsonResponse(
                        {"Status": False, "Errors": "Неправильно указаны аргументы"}
                    )
                else:
                    if is_updated:
                        # new_order_signal.send(
                        #     sender=self.__class__, user_id=request.user.id
                        # )
                        return JsonResponse({"Status": True})

        return JsonResponse(
            {"Status": False, "Errors": "Не указаны все необходимые аргументы"}
        )


class ProductInfoView(APIView):
    def get(self, request, *args, **kwargs):

        query = Q(shop_id__state=True)
        shop_id = request.query_params.get("shop_id")
        category_id = request.query_params.get("category_id")

        if shop_id:
            query &= Q(shop_id=shop_id)
        if category_id:
            query &= Q(product__category_id=category_id)
        queryset = (
            ProductInfo.objects.filter(query)
            .select_related("shop", "product__category")
            .prefetch_related("product_param__parameter")
        )

        serializer = ProductInfoSerializer(queryset, many=True)
        return JsonResponse({"status": True, "data": serializer.data})

class PartnerOrders(APIView):
    """
    Класс для получения заказов поставщиками
    """
    def get(self, request, *args, **kwargs):

        if request.user.type != "shop":
            return JsonResponse({'Status': False, 'Error': 'Только для магазинов'}, status=403)

        order = Order.objects.filter(
            ordered_items__product_info__shop__user_id=request.user.id).exclude(state="basket").prefetch_related(
            "ordered_items__product_info__product__category",
            "ordered_items__product_info__product_param__parameter").select_related("contact").annotate(
            total_sum=Sum(F("ordered_items__quantity") * F("ordered_items__product_info__price"))).distinct()

        serializer = OrderSerializer(order, many=True)
        return Response(serializer.data)