from django.urls import path
from . import views
from django.conf import settings
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    path('users/create/', views.UserListCreateView.as_view(), name='create_user'),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    # for admin
    path('admin/users/', views.UserListView.as_view(), name='get_users'),
    path('admin/<int:pk>/', views.UserDetailView.as_view(), name='user_detail'),
    path('admin/appointments/', views.AppointmentsView.as_view(), name='appointments-list'),
    path('admin/appointments/<int:pk>/', views.AppointmentEditView.as_view(), name='appointment-detail-admin'),
    path('admin/appointments/status/<str:status>/', views.AppointmentsStatusView.as_view(), name='appointment-by-status-admin'),
    path('admin/premium/', views.PremiumSubscriptionView.as_view(), name='premium-subscription-list'),
    path('admin/premium/list/', views.PremiumSubscriptionListView.as_view(), name='premium-subscription-detail'),
    path('admin/premium/<int:pk>/revoke/', views.RevokePremiumView.as_view(), name='revoke-premium-subscription'),
    path('admin/coupons/create/', views.CouponCreateView.as_view(), name='coupon-list-create'),
    path('admin/coupons/', views.CouponListView.as_view(), name='coupon-list'),
    path('admin/coupons/<int:pk>/', views.CouponEditView.as_view(), name='coupon-detail'),
    path('admin/history/', views.MedicalHistoryAdminView.as_view(), name='medical-history-list-admin'),
    path('admin/history/<int:pk>/', views.MedicalHistoryDetailView.as_view(), name='medical-history-detail-admin'),
    path('admin/history/user/<int:pk>/', views.MedicalHistoryByUserView.as_view(), name='medical-history-filter-by-user'),
    path('admin/history/upload', views.MedicalRecordUploadView.as_view(), name='upload-medical-history-record'),
    path('admin/ai/', views.AIModelListView.as_view(), name='ai-model-list'),
    path('admin/ai/<int:pk>/', views.AIModelDetailView.as_view(), name='ai-model-detail'),
    path('admin/ai/upload/', views.AIModelCreateView.as_view(), name='upload-ai-model'),
    #untested
    path('admin/ticket/', views.TicketListView.as_view(), name='ticket-list'),
    path('admin/ticket/<int:pk>/', views.TicketDetailView.as_view(), name='ticket-detail'),
    path("admin/sync-doctors/", views.SyncAppointedDoctorsView.as_view(), name="sync-appointed-doctors"),

    # for authenticated user
    path('users/me/', views.AccountView.as_view(), name='account'),
    path('users/me/password/', views.ChangePasswordView.as_view(), name='change-password'),
    path('users/appointments/', views.AppointmentListView.as_view(), name='appointment-list'),
    path('users/appointments/create/', views.AppointmentListCreateView.as_view(), name='appointment-list-create'),
    path('users/appointments/<int:pk>/', views.AppointmentDetailView.as_view(), name='appointment-detail'),
    path('users/appointments/status/<str:status>/', views.AppointmentByStatusView.as_view(), name='appointment-by-status'),
    path('users/redeem/', views.RedeemCouponView.as_view(), name='redeem-coupon'),
    path('users/history/', views.MedicalHistoryView.as_view(), name='medical-history'),
    path('users/ai/', views.DeployedAIModelView.as_view(), name='view-ai-models-user'),
    path('users/ai/infer/', views.AiInferenceView.as_view(), name='ai-inference'),
    path('users/history/infer/', views.AiInferenceHView.as_view(), name='ai-inference-from-history'),
    #untested
    path('users/ticket/create/', views.TicketCreateView.as_view(), name='ticket-create'),
]