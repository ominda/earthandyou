from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand


# Maps role name -> list of (app_label, model, codename_suffix) tuples
ROLE_PERMISSIONS = {
    "inventory_manager": [
        ("inventory", "inventoryitem", "view_inventoryitem"),
        ("inventory", "inventoryitem", "change_inventoryitem"),
        ("inventory", "inventoryauditlog", "view_inventoryauditlog"),
        ("catalog", "physicalgemstone", "view_physicalgemstone"),
        ("catalog", "physicalgemstone", "change_physicalgemstone"),
    ],
    "catalog_manager": [
        ("catalog", "product", "view_product"),
        ("catalog", "product", "add_product"),
        ("catalog", "product", "change_product"),
        ("catalog", "productmedia", "view_productmedia"),
        ("catalog", "productmedia", "add_productmedia"),
        ("catalog", "productmedia", "change_productmedia"),
        ("catalog", "productmedia", "delete_productmedia"),
        ("certification", "certificationreport", "view_certificationreport"),
        ("certification", "certificationreport", "add_certificationreport"),
        ("certification", "certificationreport", "change_certificationreport"),
    ],
    "order_manager": [
        ("customers", "customer", "view_customer"),
        ("inventory", "inventoryitem", "view_inventoryitem"),
        ("catalog", "product", "view_product"),
    ],
    "superadmin": [],  # superadmin uses is_superuser — no group permissions needed
}


class Command(BaseCommand):
    help = "Create staff role groups with appropriate permissions."

    def handle(self, *args, **options):
        for role, perm_list in ROLE_PERMISSIONS.items():
            group, created = Group.objects.get_or_create(name=role)
            action = "Created" if created else "Updated"

            permissions = []
            for app_label, model_name, codename in perm_list:
                try:
                    perm = Permission.objects.get(codename=codename)
                    permissions.append(perm)
                except Permission.DoesNotExist:
                    self.stdout.write(self.style.WARNING(
                        f"  Permission not found: {codename} (skipped)"
                    ))

            group.permissions.set(permissions)
            self.stdout.write(self.style.SUCCESS(
                f"{action} group '{role}' with {len(permissions)} permission(s)."
            ))
