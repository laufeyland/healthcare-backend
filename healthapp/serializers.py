from rest_framework import serializers
from .models import *
from django.contrib.auth import get_user_model

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'password', 'name', 'age', 'gender', 'role', 'settings', 'premium_status')
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        validated_data.pop('role', None)  
        validated_data.pop('premium_status', None)  
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)  
        user.save()
        return user  

    
class AppointmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointment
        fields = ['id', 'user', 'appointment_date', 'status']
        read_only_fields = ['user'] 

class MedicalHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicalHistory
        fields = ['id', 'patient', 'scan', 'ai_interpretation', 'record_date']

class ReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = ['id', 'patient', 'report_date', 'report_details', 'status']

class AIModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIModel
        fields = ['id', 'model_name', 'version', 'status', 'parameters']

class PremiumSubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PremiumSubscription
        fields = ['id', 'user', 'premium_expiry']

class CouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = ['id', 'coupon_code', 'valid_until', 'description']
