from django.urls import path

from backend.views import AutUser, PartnerUpdate, RegisterAccount, ShopsView


app_name = "backend"
urlpatterns = [
    path("partner/update", PartnerUpdate.as_view(), name="partner-update"),
    path("user/register", RegisterAccount.as_view(), name="user-register"),
    path("user/auth", AutUser.as_view(), name="user-auth"),
    path("user/auth/<int:pk>", RegisterAccount.as_view(), name="user-auth"),
    path('shops', ShopsView.as_view(), name='shops'),
]
