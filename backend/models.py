from django.db import models
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.validators import EmailValidator
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import BaseUserManager, AbstractUser
from django_rest_passwordreset.tokens import get_token_generator


USER_TYPE_CHOICES = (("buyer", "Покупатель"), ("shop", "Магазин"))
STATE_CHOICES = (
    ("basket", "Статус корзины"),
    ("new", "Новый"),
    ("confirmed", "Подтвержден"),
    ("assembled", "Собран"),
    ("sent", "Отправлен"),
    ("delivered", "Доставлен"),
    ("canceled", "Отменен"),
)


class CustomAccountManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password, **extra_fields):
        """
        Create and save a User with the given email and password.
        """
        if not email:
            raise ValueError(_("The Email must be set"))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Superuser must have is_staff=True."))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Superuser must have is_superuser=True."))
        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractUser):
    email = models.EmailField(max_length=200, verbose_name="Email", unique=True)
    type = models.CharField(
        verbose_name="Тип пользователя",
        choices=USER_TYPE_CHOICES,
        max_length=5,
        default="buyer",
    )
    is_active = models.BooleanField(default=True)

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
    url = models.URLField(max_length=200, blank=True, null=True)

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
    external_id = models.PositiveIntegerField(verbose_name="Внешний ID")
    model = models.CharField(max_length=90, verbose_name="Модель")
    product = models.ForeignKey(
        Product, related_name="products_info", blank=True, on_delete=models.CASCADE
    )
    shop = models.ForeignKey(
        Shop, related_name="products_info", blank=True, on_delete=models.CASCADE
    )
    description = models.TextField(blank=True)
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
    parameter = models.ForeignKey(
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
    status = models.CharField(choices=STATE_CHOICES, verbose_name="Статус", blank=True)
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
        related_name="ordered_items",
        blank=True,
        on_delete=models.CASCADE,
    )
    product_info = models.ForeignKey(
        ProductInfo,
        verbose_name="Продукт",
        related_name="ordered_items",
        blank=True,
        on_delete=models.CASCADE,
    )

    quantity = models.PositiveIntegerField(
        verbose_name="Колличество",
        blank=True,
    )

    class Meta:
        verbose_name = "Заказ"
        verbose_name_plural = "Список заказов"


class ConfirmEmailToken(models.Model):
    user = models.ForeignKey(
        CustomUser,
        related_name="confirm_email_tokens",
        on_delete=models.CASCADE,
        verbose_name=_("The User which is associated to this password reset token"),
    )

    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name=_("When was this token generated")
    )
    key = models.CharField(_("Key"), max_length=64, db_index=True, unique=True)

    class Meta:
        verbose_name = "Токен подтверждения Email"
        verbose_name_plural = "Токены подтверждения Email"

    @staticmethod
    def generate_key():
        """generates a pseudo random code using os.urandom and binascii.hexlify"""
        return get_token_generator().generate_token()

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = self.generate_key()
        return super(ConfirmEmailToken, self).save(*args, **kwargs)

    def __str__(self):
        return "Password reset token for user {user}".format(user=self.user)
