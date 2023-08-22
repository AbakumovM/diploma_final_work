from typing import Optional
from django.db import models
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.validators import EmailValidator
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import BaseUserManager, AbstractUser

USER_TYPE_CHOICES = (("buyer", "Покупатель"), ("saler", "Продавец"))


class CustomAccountManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("Поле email не может быть пустым! ")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        extra_fields.setdefault("is_active", True)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Администратор должен иметь is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Администратор должен иметь is_superuser=True.")

        return self._create_user(email, password, **extra_fields)


class CustomUser(AbstractUser):
    email = models.EmailField(max_length=200, verbose_name="Email", unique=True)
    type = models.CharField(
        verbose_name="Тип пользователя",
        choices=USER_TYPE_CHOICES,
        max_length=5,
        default="buyer",
    )
    is_active = models.BooleanField(default=False)
    company = models.CharField(
        max_length=90, verbose_name="Название компании", blank=True
    )
    position = models.CharField(max_length=40, blank=True, verbose_name="Должность")
    username_validator = UnicodeUsernameValidator()
    username = models.CharField(
        _("username"),
        max_length=150,
        help_text=_(
            "Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only."
        ),
        validators=[username_validator],
        error_messages={
            "unique": _("A user with that username already exists."),
        },
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
    objects = CustomAccountManager()

    def __str__(self):
        return self.email

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Список пользователей"
        ordering = ("email",)


class Shop(models.Model):
    name = models.CharField(
        max_length=60, blank=False, verbose_name="Название магазина"
    )
    url = models.URLField(max_length=200, blank=False, verbose_name="Сылка")
    filename = models.CharField(
        max_length=60, blank=True, verbose_name="Название файла"
    )
    user = models.OneToOneField(
        CustomUser, verbose_name="Администратор магазина", on_delete=models.CASCADE
    )
    state = models.BooleanField(verbose_name="статус получения заказов", default=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Магазин"
        verbose_name_plural = "Список магазинов"
        ordering = ("-name",)


class Category(models.Model):
    shops = models.ManyToManyField(
        Shop, verbose_name="Магазины", related_name="categories", blank=True
    )
    name = models.CharField(
        max_length=70, blank=True, verbose_name="Название категории"
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Список категорий"
        ordering = ("-name",)


class Product(models.Model):
    category = models.ForeignKey(
        Category,
        related_name="products",
        blank=True,
        verbose_name="Название категории",
        on_delete=models.CASCADE,
    )
    name = models.CharField(
        max_length=100, null=False, blank=True, verbose_name="Название продукта"
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Товар"
        verbose_name_plural = "Список товаров"
        ordering = ("-name",)


class ProductInfo(models.Model):
    external_id = models.PositiveIntegerField(verbose_name="Внешний ID", blank=True)
    model = models.CharField(max_length=90, verbose_name="Модель", blank=True)
    product = models.ForeignKey(
        Product, related_name="products_info", blank=True, on_delete=models.CASCADE
    )
    shop = models.ForeignKey(
        Shop, related_name="products_info", blank=True, on_delete=models.CASCADE
    )
    quantity = models.PositiveIntegerField(verbose_name="Колличество")
    price = models.PositiveIntegerField(verbose_name="Цена")
    price_rrc = models.PositiveIntegerField(verbose_name="Рекомендуемая розничная цена")

    class Meta:
        verbose_name = "Информация о товаре"
        verbose_name_plural = "Список атрибутов продукта"


class Parameter(models.Model):
    name = models.CharField(
        max_length=60, null=False, blank=False, verbose_name="Название"
    )

    class Meta:
        verbose_name = "Название параметра"
        verbose_name_plural = "Список названия параметров"

    def __str__(self):
        return self.name


class ProductParameter(models.Model):
    product_info = models.ForeignKey(
        ProductInfo,
        verbose_name="Информация о продуктe",
        related_name="product_param",
        on_delete=models.CASCADE,
    )
    parametr = models.ForeignKey(
        Parameter,
        verbose_name="Параметр",
        related_name="product_param",
        on_delete=models.CASCADE,
    )
    value = models.CharField(verbose_name="Колличество", null=False, blank=False)

    class Meta:
        verbose_name = "Параметр"
        verbose_name_plural = "Список параметров"


class Contact(models.Model):
    user = models.ForeignKey(
        CustomUser,
        verbose_name="Пользователь",
        related_name="contacts",
        blank=True,
        on_delete=models.CASCADE,
    )

    city = models.CharField(max_length=50, verbose_name="Город")
    street = models.CharField(max_length=100, verbose_name="Улица")
    house = models.CharField(max_length=15, verbose_name="Дом", blank=True)
    structure = models.CharField(max_length=15, verbose_name="Корпус", blank=True)
    building = models.CharField(max_length=15, verbose_name="Строение", blank=True)
    apartment = models.CharField(max_length=15, verbose_name="Квартира", blank=True)
    phone = models.CharField(max_length=20, verbose_name="Телефон")

    class Meta:
        verbose_name = "Контакты пользователя"
        verbose_name_plural = "Список контактов пользователя"

    def __str__(self):
        return f"{self.city} {self.street} {self.house}"


class Order(models.Model):
    user = models.ForeignKey(
        CustomUser,
        verbose_name="Пользователь",
        related_name="orders",
        blank=True,
        null=False,
        on_delete=models.CASCADE,
    )
    dt = models.DateTimeField(auto_now_add=True)
    status = models.BooleanField(default=False, verbose_name="Статус", blank=True)
    contact = models.ForeignKey(
        Contact,
        verbose_name="Контакты",
        blank=True,
        null=True,
        on_delete=models.CASCADE,
    )

    class Meta:
        verbose_name = "Заказ"
        verbose_name_plural = "Список заказов"


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        verbose_name="Заказ",
        related_name="orderitems",
        blank=True,
        on_delete=models.CASCADE,
    )
    product = models.ForeignKey(
        ProductInfo,
        verbose_name="Продукт",
        blank=True,
        on_delete=models.CASCADE,
    )
    shop = models.ForeignKey(
        Shop, related_name="Магазин", blank=True, on_delete=models.CASCADE
    )
    quantity = models.PositiveIntegerField(
        verbose_name="Колличество",
        blank=True,
    )

    class Meta:
        verbose_name = "Заказ"
        verbose_name_plural = "Список заказов"
