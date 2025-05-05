from rest_framework import serializers
from .models import *
from django.contrib.auth import get_user_model

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'password', 'first_name', 'last_name' , 'phone_number', 'age', 'gender', 'role', 'settings', 'pic', 'premium_status', 'ai_tries')
        extra_kwargs = {'password': {'write_only': True}, 'email' : {'required': True, 'allow_blank': False}, 'username': {'required': True, 'allow_blank': False}, 'role': {'read_only': True}, 'premium_status': {'read_only': True}}

    def create(self, validated_data):
        validated_data.pop('ai_tries', None)
        validated_data.pop('role', None)  
        validated_data.pop('premium_status', None)  
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)  
        user.save()
        return user  
    def update(self, instance, validated_data):
        
        validated_data.pop('ai_tries', None)
        validated_data.pop('role', None)
        validated_data.pop('premium_status', None)

        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if password:
            instance.set_password(password)

        instance.save()
        return instance
    
class AppointmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointment
        fields = ['id', 'user', 'appointment_date', 'status', 'reference']
        extra_kwargs = {'user': {'read_only': True}, 'reference': {'read_only': True}}

class MedicalHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicalHistory
        fields = ['id', 'user', 'scan', 'ai_interpretation', 'appointment', 'record_date']
        extra_kwargs = {'user': {'read_only': True}}

class TicketSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = ['id', 'subject', 'description', 'reported_by', 'status', 'created_at']
        extra_kwargs = {'reported_by': {'read_only': True}}
    
class AIModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIModel
        fields = ['id', 'model_name', 'model_file', 'created_at', 'status', 'parameters']
        extra_kwargs = {'model_file': {'write_only': True}}

class PremiumSubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PremiumSubscription
        fields = ['id', 'user_id', 'expires_at']

class CouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = ['id', 'coupon_code', 'valid_until', 'description']

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ['id', 'user', 'amount', 'payment_date', 'payment_method', 'transaction_id', 'status']
        extra_kwargs = {'user': {'read_only': True}, 'transaction_id': {'read_only': True}, 'status': {'read_only': True}, 'payment_date': {'read_only': True}, 'amount': {'read_only': True}}

class AppointedDoctorSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppointedDoctor
        fields = [
            'id',
            'first_name',
            'last_name',
            'specialty',
            'wilaya',
            'license_number',
            'address',
            'phone_number',  
            'email',
            'external_id',
        ]