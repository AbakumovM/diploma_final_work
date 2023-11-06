import base64
from distutils.util import strtobool
import os
from django.db import IntegrityError
from rest_framework.generics import ListAPIView
from django.http import JsonResponse
from django.contrib.auth.password_validation import validate_password
from requests import get
from django.contrib.auth.views import LoginView
from django.db.models import Q, Sum, F
from django.core.validators import URLValidator
from rest_framework.views import APIView
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
import yaml
from django.core.exceptions import ObjectDoesNotExist
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
    AvatarSerializer,
    CategorySerializer,
    ContactSerializer,
    OrderItemSerializer,
    OrderSerializer,
    PartnerOrderSerializer,
    ProductInfoSerializer,
    ProductSerializer,
    ShopSerializer,
    UserSerializer,
)
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema


from backend.tasks import (
    download_image,
    new_user_registered_task,
    new_order_task,
    upload_image,
)


class RegisterAccount(APIView):
    """
    Класс по созданию, удалению и получению всех пользователей(покупатель или продавец).
    """

    @extend_schema(summary="Получить список пользователей")
    def get(self, request, *args, **kwargs):
        users = CustomUser.objects.all().prefetch_related("avatars", "contacts")
        serializer = UserSerializer(users, many=True)
        return JsonResponse({"users": serializer.data})

    @extend_schema(summary="Создать пользователя")
    def post(self, request, *args, **kwargs):
        """Метод создания пользователя. Передаются данные first_name, last_name, email, password, company."""

        if {"first_name", "last_name", "email", "password", "company"}.issubset(
            request.data
        ):
            try:
                validate_password(request.data["password"])
            except Exception as er:
                errors = [error for error in er]
                return JsonResponse(
                    {"Status": False, "Errors": {"password": errors}}, status=400
                )
            else:
                user_serializer = UserSerializer(data=request.data)
                if user_serializer.is_valid():
                    user = user_serializer.save()
                    user.set_password(request.data["password"])
                    user.save()
                    new_user_registered_task.delay(user_id=user.id)
                    return JsonResponse(
                        {"Status": True, "user": user_serializer.data}, status=200
                    )
                else:
                    return JsonResponse(
                        {"Status": False, "Errors": user_serializer.errors}, status=400
                    )

        return JsonResponse(
            {"Status": False, "Errors": "Указаны не все аргументы"}, status=400
        )

    @extend_schema(summary="Удалить пользователя")
    def delete(self, request, *args, **kwargs):
        try:
            CustomUser.objects.get(id=request.data["id"]).delete()
            return JsonResponse(
                {"Status": True, "answer": "Пользователь удален"}, status=204
            )
        except ObjectDoesNotExist:
            return JsonResponse(
                {
                    "Status": False,
                    "Error": "Пользователь не найден. Проверьте введеный id!",
                }
            )


class AvatarUsers(APIView):
    serializer_class = AvatarSerializer

    def get_queryset(self):
        return AvatarUsers.objects.filter(user_id=self.kwargs["user_id"])

    def post(self, request, *args, **kwargs):
        avatar = request.FILES.get("avatar").read()

        byte = base64.b64encode(avatar)

        data = {
            "user_id": request.data["user_id"],
            "avatar": byte.decode("utf-8"),
            "name": request.FILES.get("avatar").name,
        }

        upload_image.delay(data=data)

        return JsonResponse(
            {
                "Status": True,
                "Error": "загрузка",
            }
        )


class AuthorizationUser(APIView, LoginView):
    """
    Класс для авторизации пользователя. Пользователь получает токен, если передал верные данные.
    """

    @extend_schema(summary="Получения токена после успешной авторизации")
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

            return JsonResponse(
                {"Status": False, "Errors": "Введён неверный email или пароль"}
            )

        return JsonResponse(
            {"Status": False, "Errors": "Укажите email и пароль от личного кабинета."}
        )


class ConfirmAccount(APIView):
    """
    Класс для подтверждения почтового адреса.
    """

    @extend_schema(summary="Подтверждение почты")
    def post(self, request, *args, **kwargs):
        if {"email", "token"}.issubset(request.data):
            token = ConfirmEmailToken.objects.filter(
                user__email=request.data["email"], key=request.data["token"]
            ).first()
            if token:
                token.user.is_active = True
                token.user.save()
                token.delete()
                return JsonResponse(
                    {"Status": True, "Answer": "Пользователь подтвержден."}
                )
            else:
                return JsonResponse(
                    {"Status": False, "Errors": "Неправильно указан токен или email"}
                )

        return JsonResponse(
            {"Status": False, "Errors": "Указаны не все необходимые аргументы"}
        )


class PartnerUpdate(APIView):
    """
    Класс загрузки товаров от магазина. Магазин передает ссылку на файл с данными.
    Загрузку фото делаем через post и передаем image и external_id.
    """

    permission_classes = (IsAuthenticated,)

    @extend_schema(summary="Загрузка товаров магазина.")
    def post(self, request, *args, **kwargs):
        if request.user.type != "shop":
            return JsonResponse(
                {"Status": False, "Error": "Только для магазинов"}, status=403
            )

        if {"image", "external_id"}.issubset(request.data):
            url = request.data["image"]
            shop_id = Shop.objects.get(user_id=request.user.id).id
            product_id = request.data["external_id"]
            filename = os.path.basename(url)
            data = {
                "url": url,
                "filename": filename,
                "product_id": product_id,
                "shop_id": shop_id,
            }
            download_image.delay(data)
            return JsonResponse(
                {
                    "Status": True,
                }
            )

        url = request.data.get("url")
        if url:
            try:
                URLValidator(url)
            except Exception as url_errorы:
                return JsonResponse(
                    {
                        "Status": False,
                        "Errors": {"url": [error for error in url_errorы]},
                    }
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
                            parameter_id=parameter_object[0].id,
                            value=value,
                        )
        return JsonResponse({"Status": True, "Answer": "Информация успешно добавлена!"})


class ShopsView(ListAPIView):
    """
    Класс отражает список магазинов.
    """

    queryset = Shop.objects.all()
    serializer_class = ShopSerializer


class ProductView(ListAPIView):
    """
    Класс отражает список товаров.
    """

    queryset = Product.objects.all()
    serializer_class = ProductSerializer


class UserDetails(APIView):
    """
    Класс для изменения данных о пользователе. Только для авторизованных пользователей.
    """

    permission_classes = (IsAuthenticated,)

    @extend_schema(summary="Изменения данных пользователя")
    def post(self, request, *args, **kwargs):
        if {"password"}.issubset(request.data):
            try:
                validate_password(request.data["password"])
            except Exception as pass_error:
                return JsonResponse(
                    {
                        "Status": False,
                        "Errors": {"password": [error for error in pass_error]},
                    },
                    status=400,
                )
            else:
                request.user.set_password(request.data["password"])
        user_serializer = UserSerializer(request.user, data=request.data, partial=True)
        if user_serializer.is_valid():
            user_serializer.save()
            return JsonResponse(
                {
                    "Status": True,
                    "Answer": "Данные успешно изменены!",
                    "user": user_serializer.data,
                }
            )
        else:
            return JsonResponse(
                {"Status": False, "Errors": user_serializer.errors}, status=400
            )


class CategoryView(ListAPIView):
    """
    Класс для отражания всех категорий.
    """

    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class PartnerState(APIView):
    """
    Класс изменения статуса магазина.
    """

    permission_classes = (IsAuthenticated,)

    @extend_schema(summary="Получить статус магазина")
    def get(self, request, *args, **kwargs):
        if request.user.type != "shop":
            return JsonResponse(
                {"Status": False, "Errors": "Только для магазинов"}, status=403
            )

        state = request.user.shop
        serializer_shop = ShopSerializer(state)
        return JsonResponse({"Status": True, "Shop_info": serializer_shop.data})

    @extend_schema(summary="Изменить статус магазина")
    def post(self, request, *args, **kwargs):
        if request.user.type != "shop":
            return JsonResponse(
                {"Status": False, "Errors": "Только для магазинов"}, status=403
            )
        state = request.data.get("state")
        if state:
            try:
                Shop.objects.filter(user_id=request.user.id).update(
                    state=strtobool(request.data["state"])
                )
                return JsonResponse({"Status": True, "Answer": "Данные изменены"})
            except ValueError as e:
                return JsonResponse({"Status": False, "Error": str(e)}, status=400)
        else:
            return JsonResponse(
                {"Status": False, "Error": "Указаны не все необходимые аргументы"},
                status=400,
            )


class ContactView(APIView):
    """
    Класс создания, изменения и удаления контактных данных для заказа.
    """

    permission_classes = (IsAuthenticated,)

    @extend_schema(summary="Получить контакты пользователя")
    def get(self, request, *args, **kwargs):
        if request.user.type != "buyer":
            return JsonResponse(
                {"Status": False, "Error": "Только для покупателей"}, status=403
            )

        contacts = Contact.objects.filter(user_id=request.user.id)
        if contacts:
            serializer = ContactSerializer(contacts, many=True)
            return JsonResponse({"Status": True, "Answer": serializer.data})
        return JsonResponse(
            {"Status": False, "Answer": "Контактных данных нет по данному пользователю"}
        )

    @extend_schema(summary="Добавить контакты пользователя")
    def post(self, request, *args, **kwargs):
        if request.user.type != "buyer":
            return JsonResponse(
                {"Status": False, "Error": "Только для покупателей"}, status=403
            )

        if {"city", "street", "house", "phone"}.issubset(request.data):
            request.data.update({"user": request.user.id})
            serializer_contacts = ContactSerializer(data=request.data)
            if serializer_contacts.is_valid():
                serializer_contacts.save()
                return JsonResponse(
                    {
                        "Status": True,
                        "Answer": "Данные добавлены!",
                        "contact": serializer_contacts.data,
                    }
                )
            else:
                return JsonResponse(
                    {"Status": False, "Errors": serializer_contacts.errors}
                )
        return JsonResponse(
            {"Status": False, "Error": "Указаны не все необходимые аргументы"},
            status=400,
        )

    @extend_schema(summary="Изменить контакты пользователя")
    def put(self, request, *args, **kwargs):
        if request.user.type != "buyer":
            return JsonResponse(
                {"Status": False, "Error": "Только для покупателей"}, status=403
            )

        contact_id = request.data.get("id")
        if contact_id:
            contact = Contact.objects.filter(id=contact_id, user_id=request.user.id)[0]
            if contact:
                serializer = ContactSerializer(contact, data=request.data, partial=True)
                if serializer.is_valid():
                    serializer.save()
                    return JsonResponse(
                        {"Status": True, "contact": serializer.data}, status=200
                    )
                else:
                    return JsonResponse(
                        {"Status": False, "Errors": serializer.errors}, status=400
                    )
            return JsonResponse(
                {"Status": False, "Error": "Контакты не найдены. Проверьте id!"},
                status=400,
            )
        return JsonResponse(
            {"Status": False, "Error": "Указаны не все необходимые аргументы"},
            status=400,
        )

    @extend_schema(summary="Удалить контакты пользователя")
    def delete(self, request, *args, **kwargs):
        if request.user.type != "buyer":
            return JsonResponse(
                {"Status": False, "Error": "Только для покупателей"}, status=403
            )

        contact_id = request.data.get("id")
        if (contact_id and type(contact_id) == int) or contact_id.isdigit():
            try:
                Contact.objects.get(id=contact_id).delete()
                return JsonResponse(
                    {"Status": True, "Answer": "Контактные данные удалены!"}, status=204
                )
            except Exception as error:
                return JsonResponse({"Status": False, "Error": str(error)}, status=400)
        return JsonResponse(
            {"Status": False, "Error": "Указан неверный формат данных"}, status=400
        )


class BasketView(APIView):
    """
    Класс для создания, изменения и удаления заказов пользователей
    """

    permission_classes = (IsAuthenticated,)

    @extend_schema(summary="Получить корзину пользователя")
    def get(self, request, *args, **kwargs):
        basket = (
            Order.objects.filter(user_id=request.user.id, status="basket")
            .prefetch_related(
                "ordered_items__product_info__product__category",
                "ordered_items__product_info__product_param__parameter",
            )
            .annotate(
                total_sum=Sum(
                    F("ordered_items__quantity")
                    * F("ordered_items__product_info__price")
                )
            )
            .distinct()
        )

        serializer = OrderSerializer(basket, many=True)
        return JsonResponse({"status": True, "answer": serializer.data}, status=200)

    @extend_schema(summary="Добавить товар в корзину")
    def post(self, request, *args, **kwargs):
        items = request.data.get("items")
        if items:
            basket, _ = Order.objects.get_or_create(
                user_id=request.user.id, status="basket"
            )
            objects_created = 0
            for order_item in items:
                order_item.update({"order": basket.id})
                serializer = OrderItemSerializer(data=order_item)
                if serializer.is_valid():
                    try:
                        serializer.save()
                    except IntegrityError as error:
                        return JsonResponse(
                            {"Status": False, "Erorr": str(error)}, status=400
                        )
                    else:
                        objects_created += 1

                else:
                    return JsonResponse(
                        {"Status": False, "Errors": serializer.errors}, status=400
                    )

                return JsonResponse(
                    {"Status": True, "Created_objects": objects_created}, status=201
                )
        return JsonResponse(
            {"Status": False, "Errors": "Не указаны все необходимые аргументы"},
            status=400,
        )

    @extend_schema(summary="Изменить количество товаров в корзине")
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

            return JsonResponse({"Status": True, "Обновлено объектов": objects_updated})

    @extend_schema(summary="Удалить товар из корзины")
    def delete(self, request, *args, **kwargs):
        id_del = request.data.get("items")
        if id_del:
            items_list = id_del.split(",")
            basket, _ = Order.objects.get_or_create(
                user_id=request.user.id, status="basket"
            )
            query = Q()
            objects_deleted = False
            for order_item_id in items_list:
                if order_item_id.isdigit():
                    query = query | Q(order_id=basket.id, id=order_item_id)
                    objects_deleted = True

            if objects_deleted:
                deleted_count = OrderItem.objects.filter(query).delete()[0]
                return JsonResponse(
                    {"Status": True, "Удалено объектов": deleted_count}, status=204
                )
        return JsonResponse(
            {"Status": False, "Errors": "Не указаны все необходимые аргументы"},
            status=400,
        )


class OrderView(APIView):
    """
    Класс для получения и размешения заказов пользователями.
    """

    permission_classes = (IsAuthenticated,)

    @extend_schema(summary="Получить список заказов пользователя")
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
        return JsonResponse({"Status": True, "Orders": serializer.data}, status=200)

    @extend_schema(summary="Разместить заказ, добавив контакты")
    def post(self, request, *args, **kwargs):
        if {"id", "contact"}.issubset(request.data):
            if request.data["id"]:
                try:
                    is_updated = Order.objects.filter(
                        user_id=request.user.id, id=request.data["id"]
                    ).update(contact_id=request.data["contact"], status="new")
                except IntegrityError as error:
                    return JsonResponse(
                        {"Status": False, "Errors": "Неправильно указаны аргументы"},
                        status=400,
                    )
                else:
                    if is_updated:
                        new_order_task.send(
                            sender=self.__class__, user_id=request.user.id
                        )
                        return JsonResponse({"Status": True}, status=201)

        return JsonResponse(
            {"Status": False, "Errors": "Не указаны все необходимые аргументы"},
            status=400,
        )


class ProductInfoView(APIView):
    """
    Класс по отражению всех товаров или по магазину или по категории.
    """

    @extend_schema(summary="Получить список товаров по магазину или по категориям")
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
        return JsonResponse({"Status": True, "Data": serializer.data}, status=200)


class PartnerOrders(APIView):
    """
    Класс для получения заказов поставщиками
    """

    @extend_schema(summary="Получить список заказов для магазина")
    def get(self, request, *args, **kwargs):
        if request.user.type != "shop":
            return JsonResponse(
                {"Status": False, "Error": "Только для магазинов"}, status=403
            )
        id_order = request.data.get("id")
        if id_order:
            orders = (
                Order.objects.filter(
                    ordered_items__product_info__shop__user_id=request.user.id,
                    id=id_order,
                )
                .exclude(status="basket")
                .prefetch_related(
                    "ordered_items__product_info__product",
                    "ordered_items__product_info__product_param__parameter",
                )
                .annotate(
                    total=Sum(
                        F("ordered_items__quantity")
                        * F("ordered_items__product_info__price")
                    )
                )
                .distinct()
                .values()
            )

            for order in orders:
                prod = OrderItem.objects.filter(
                    product_info__shop__user_id=request.user.id, order_id=order["id"]
                )
                order.update({"ordered_items": prod})
            serializer = PartnerOrderSerializer(orders, many=True)
            return JsonResponse({"Orders": serializer.data}, status=200)
        else:
            orders = (
                Order.objects.filter(
                    ordered_items__product_info__shop__user_id=request.user.id
                )
                .exclude(status="basket")
                .prefetch_related(
                    "ordered_items__product_info__product",
                    "ordered_items__product_info__product_param__parameter",
                )
                .annotate(
                    total=Sum(
                        F("ordered_items__quantity")
                        * F("ordered_items__product_info__price")
                    )
                )
                .distinct()
                .values()
            )
            for order in orders:
                prod = OrderItem.objects.filter(
                    product_info__shop__user_id=request.user.id, order_id=order["id"]
                )
                order.update({"ordered_items": prod})
            serializer = PartnerOrderSerializer(orders, many=True)
            return JsonResponse({"Orders": serializer.data}, status=200)
