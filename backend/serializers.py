from rest_framework import serializers
from .models import (
    Contact,
    CustomUser,
    Order,
    OrderItem,
    Parameter,
    Product,
    ProductInfo,
    ProductParameter,
    Shop,
    Category,
)


class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = (
            "id",
            "city",
            "street",
            "house",
            "structure",
            "building",
            "apartment",
            "user",
            "phone",
        )
        read_only_fields = ("id",)
        extra_kwargs = {"user": {"write_only": True}}


class UserSerializer(serializers.ModelSerializer):
    contacts = ContactSerializer(read_only=True, many=True)

    class Meta:
        model = CustomUser
        fields = (
            "id",
            "first_name",
            "last_name",
            "email",
            "company",
            "position",
            "contacts",
        )
        read_only_fields = ("id",)


class ShopSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shop
        fields = ("name", "id", "state")


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = (
            "name",
            "shops",
        )


class ProductSerializer(serializers.ModelSerializer):
    category = serializers.StringRelatedField()

    class Meta:
        model = Product
        fields = (
            "category",
            "name",
        )


class ProductParameterSerializer(serializers.ModelSerializer):
    parametr = serializers.StringRelatedField()

    class Meta:
        model = ProductParameter
        fields = ("product_info", "parametr", "value")


class ProductInfoSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    product_parameters = ProductParameterSerializer(read_only=True, many=True)

    class Meta:
        model = ProductInfo
        fields = (
            "external_id",
            "model",
            "product",
            "shop",
            "quantity",
            "price",
            "price_rrc",
            "product_parameters",
        )


class ParameterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Parameter
        fields = ("name",)


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = (
            "id",
            "product_info",
            "quantity",
            "order",
        )
        extra_kwargs = {"order": {"write_only": True}}


class OrderItemCreateSerializer(OrderItemSerializer):
    product_info = ProductInfoSerializer(read_only=True)


class OrderSerializer(serializers.ModelSerializer):
    ordered_items = OrderItemCreateSerializer(read_only=True, many=True)

    total_sum = serializers.IntegerField()
    contact = ContactSerializer(read_only=True)

    class Meta:
        model = Order
        fields = (
            "id",
            "ordered_items",
            "state",
            "dt",
            "total_sum",
            "contact",
        )
        read_only_fields = ("id",)
