import uuid
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


class CustomerManager(BaseUserManager):

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_email_verified", True)
        return self.create_user(email, password, **extra_fields)


class Customer(AbstractBaseUser, PermissionsMixin):
    """
    Custom user model for Earth&You customers.

    Email is the unique identifier — no separate username field.
    Staff/superuser flags are kept for Django admin compatibility.
    is_email_verified gates access to order placement (Phase 4).
    """

    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_email_verified = models.BooleanField(default=False)

    date_joined = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = CustomerManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = "Customer"
        verbose_name_plural = "Customers"
        ordering = ["-date_joined"]

    def __str__(self):
        return self.email

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()


class CustomerProfile(models.Model):
    """
    Extended profile data for a customer.
    Created automatically on first access via get_or_create.
    """

    customer = models.OneToOneField(
        Customer,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    phone = models.CharField(max_length=30, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    newsletter_opt_in = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Customer Profile"
        verbose_name_plural = "Customer Profiles"

    def __str__(self):
        return f"Profile — {self.customer.email}"


class CustomerAddress(models.Model):

    class AddressType(models.TextChoices):
        SHIPPING = "shipping", "Shipping"
        BILLING = "billing", "Billing"

    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="addresses",
    )
    address_type = models.CharField(max_length=10, choices=AddressType.choices, default=AddressType.SHIPPING)
    label = models.CharField(max_length=100, blank=True, help_text="e.g. Home, Office")
    recipient_name = models.CharField(max_length=200)
    phone = models.CharField(max_length=30, blank=True)
    line1 = models.CharField(max_length=255)
    line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=2, help_text="ISO 3166-1 alpha-2 country code")
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Customer Address"
        verbose_name_plural = "Customer Addresses"
        ordering = ["-is_default", "-created_at"]

    def __str__(self):
        return f"{self.customer.email} — {self.label or self.address_type} ({self.city})"

    def save(self, *args, **kwargs):
        if self.is_default:
            # Unset any other default of the same type for this customer
            CustomerAddress.objects.filter(
                customer=self.customer,
                address_type=self.address_type,
                is_default=True,
            ).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)


class StaffProfile(models.Model):
    """
    Extended profile for staff/admin users.
    Attached to any Customer with is_staff=True.
    role drives permission group assignment via the setup_roles command.
    mfa_secret stores the TOTP seed (Phase 8 will complete the TOTP flow).
    """

    class Role(models.TextChoices):
        INVENTORY_MANAGER = "inventory_manager", "Inventory Manager"
        CATALOG_MANAGER = "catalog_manager", "Catalog Manager"
        ORDER_MANAGER = "order_manager", "Order Manager"
        SUPERADMIN = "superadmin", "Superadmin"

    customer = models.OneToOneField(
        Customer,
        on_delete=models.CASCADE,
        related_name="staff_profile",
        limit_choices_to={"is_staff": True},
    )
    role = models.CharField(max_length=30, choices=Role.choices)
    department = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    is_mfa_enabled = models.BooleanField(default=False)
    mfa_secret = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Staff Profile"
        verbose_name_plural = "Staff Profiles"

    def __str__(self):
        return f"{self.customer.email} — {self.get_role_display()}"


class EmailVerificationToken(models.Model):
    """
    Single-use token for verifying a customer's email address.

    Rules:
    - One active token per customer at a time — old tokens are invalidated
      when a new one is issued.
    - Token expires after EMAIL_VERIFICATION_EXPIRY_HOURS (default 24h).
    - is_used is set to True on successful verification — token cannot be reused.
    """

    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="verification_tokens",
    )
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Email Verification Token"
        verbose_name_plural = "Email Verification Tokens"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.customer.email} — {self.token}"

    @property
    def is_valid(self) -> bool:
        return not self.is_used and timezone.now() < self.expires_at
