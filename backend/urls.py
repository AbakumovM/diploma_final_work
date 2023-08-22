from django.urls import path

from backend.views import (
    AutUser,
    ContactView,
    PartnerState,
    PartnerUpdate,
    ProductView,
    RegisterAccount,
    ShopsView,
    UserDetails,
)


app_name = "backend"
urlpatterns = [
    path("partner/update", PartnerUpdate.as_view(), name="partner-update"),
    path("partner/state", PartnerState.as_view(), name="partner-state"),
    path("user/register", RegisterAccount.as_view(), name="user-register"),
    path("user/auth", AutUser.as_view(), name="user-auth"),
    path("user/auth/<int:pk>", RegisterAccount.as_view(), name="user-auth"),
    path("shops", ShopsView.as_view(), name="shops"),
    path("product/all", ProductView.as_view(), name="products"),
    path("users/details", UserDetails.as_view(), name="details"),
    path("contacts", ContactView.as_view(), name="contacts"),
]
