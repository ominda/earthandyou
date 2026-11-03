from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Customer, EmailVerificationToken


@admin.register(Customer)
class CustomerAdmin(UserAdmin):
    list_display = ["email", "first_name", "last_name", "is_email_verified", "is_active", "date_joined"]
    list_filter = ["is_active", "is_email_verified", "is_staff"]
    search_fields = ["email", "first_name", "last_name"]
    ordering = ["-date_joined"]
    readonly_fields = ["date_joined", "created_at", "updated_at", "last_login"]
    fieldsets = [
        (None, {"fields": ["email", "password"]}),
        ("Personal info", {"fields": ["first_name", "last_name"]}),
        ("Status", {"fields": ["is_active", "is_email_verified", "is_staff", "is_superuser"]}),
        ("Timestamps", {"fields": ["date_joined", "last_login", "created_at", "updated_at"]}),
    ]
    add_fieldsets = [
        (None, {
            "classes": ["wide"],
            "fields": ["email", "first_name", "last_name", "password1", "password2"],
        }),
    ]


@admin.register(EmailVerificationToken)
class EmailVerificationTokenAdmin(admin.ModelAdmin):
    list_display = ["customer", "token", "expires_at", "is_used", "is_valid", "created_at"]
    list_filter = ["is_used"]
    search_fields = ["customer__email"]
    readonly_fields = ["token", "created_at"]

    def is_valid(self, obj):
        return obj.is_valid
    is_valid.boolean = True
    is_valid.short_description = "Valid"
