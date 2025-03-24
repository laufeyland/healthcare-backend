from django.urls import path
from . import views
from django.conf import settings
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    path('users/', views.getUsers, name='get_user'),
    path('users/create/', views.createUser, name='create_user'),
    path('users/<int:pk>/', views.userDetail, name='user_detail'),
    path('users/<int:pk>/update/', views.userDetail, name='user_update'),
    path('users/<int:pk>/delete/', views.userDetail, name='user_delete'),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]