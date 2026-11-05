from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from .models import Customer, CustomerProfile, CustomerAddress, StaffProfile


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = Customer
        fields = ["email", "first_name", "last_name", "password", "password_confirm"]

    def validate(self, data):
        if data["password"] != data.pop("password_confirm"):
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})
        return data

    def create(self, validated_data):
        return Customer.objects.create_user(**validated_data)


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(username=data["email"], password=data["password"])
        if not user:
            raise serializers.ValidationError("Invalid email or password.")
        if not user.is_active:
            raise serializers.ValidationError("This account has been deactivated.")
        data["user"] = user
        return data


class CustomerSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = Customer
        fields = ["id", "email", "first_name", "last_name", "full_name", "is_email_verified", "date_joined"]
        read_only_fields = ["id", "email", "is_email_verified", "date_joined"]


class CustomerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerProfile
        fields = ["phone", "date_of_birth", "newsletter_opt_in", "updated_at"]
        read_only_fields = ["updated_at"]


class CustomerAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerAddress
        fields = [
            "id", "address_type", "label", "recipient_name", "phone",
            "line1", "line2", "city", "state", "postal_code", "country",
            "is_default", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class StaffProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="customer.email", read_only=True)
    full_name = serializers.CharField(source="customer.full_name", read_only=True)
    is_mfa_enabled = serializers.BooleanField(read_only=True)

    class Meta:
        model = StaffProfile
        fields = ["email", "full_name", "role", "department", "is_mfa_enabled"]


class TokenSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()
    user = CustomerSerializer()
