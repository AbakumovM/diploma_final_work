from django.urls import path
from django_rest_passwordreset.views import reset_password_request_token, reset_password_confirm

from backend.views import (
    AuthorizationUser,
    BasketView,
    ConfirmAccount,
    ContactView,
    OrderView,
    PartnerOrders,
    PartnerState,
    PartnerUpdate,
    ProductInfoView,
    ProductView,
    RegisterAccount,
    ShopsView,
    UserDetails,
    CategoryView
)
from diplom.settings import STATIC_ROOT, STATIC_URL
from django.conf.urls.static import static

app_name = "backend"
urlpatterns = [
    path("partner/update", PartnerUpdate.as_view(), name="partner-update"),
    path("partner/state", PartnerState.as_view(), name="partner-state"),
    path("user/register", RegisterAccount.as_view(), name="user-register"),
    path("user/auth", AuthorizationUser.as_view(), name="user-auth"),
    path("user/register/confirm", ConfirmAccount.as_view(), name="user-register-confirm"),
    path('user/password_reset', reset_password_request_token, name='password-reset'),
    path('user/password_reset/confirm', reset_password_confirm, name='password-reset-confirm'),
    path("users/details", UserDetails.as_view(), name="details"),
    path("contacts", ContactView.as_view(), name="contacts"),
    path("shops", ShopsView.as_view(), name="shops"),
    path("product/all", ProductView.as_view(), name="products"),
    path("category", CategoryView.as_view(), name="category"),
    path("basket", BasketView.as_view(), name="basket"),
    path("products", ProductInfoView.as_view(), name="products"),
    path("order", OrderView.as_view(), name="orders"),
    path("partner/orders", PartnerOrders.as_view(), name="partner-orders"),
    
]+ static(STATIC_URL, document_root=STATIC_ROOT)
