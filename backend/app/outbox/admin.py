from django.contrib import admin
from .models import NotificationLog


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ["template_name", "recipient", "status", "retry_count", "created_at", "sent_at"]
    list_filter = ["status", "template_name"]
    search_fields = ["recipient", "subject", "template_name"]
    readonly_fields = ["recipient", "subject", "template_name", "context_json", "retry_count", "error_message", "created_at", "sent_at"]
    ordering = ["-created_at"]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
