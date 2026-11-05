from rest_framework.permissions import BasePermission


class IsStaff(BasePermission):
    """Allows access only to users with is_staff=True."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)


class HasRole(BasePermission):
    """
    Allows access only to staff users whose StaffProfile.role is in the
    view's required_roles list.

    Usage on a view:
        permission_classes = [HasRole]
        required_roles = ["inventory_manager", "superadmin"]
    """

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated and request.user.is_staff):
            return False
        required_roles = getattr(view, "required_roles", [])
        if not required_roles:
            return True
        try:
            return request.user.staff_profile.role in required_roles
        except Exception:
            return False
