from django.urls import path
from . import views
from django.conf import settings
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    path('users/', views.UserListView.as_view(), name='get_users'),
    path('users/create/', views.UserListCreateView.as_view(), name='create_user'),
    # for admin
    path('users/<int:pk>/', views.UserDetailView.as_view(), name='user_detail'),
    path('users/<int:pk>/update/', views.UserDetailView.as_view(), name='user_update'),
    path('users/<int:pk>/delete/', views.UserDetailView.as_view(), name='user_delete'),
    # for authenticated user
    path('users/me/', views.AccountView.as_view(), name='account'),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('users/appointments/create', views.AppointmentListCreateView.as_view(), name='appointment-list-create'),
    path('users/appointments/<int:pk>/', views.AppointmentDetailView.as_view(), name='appointment-detail'),
    path('users/appointments/status/<str:status>/', views.AppointmentByStatusView.as_view(), name='appointment-by-status'),
]