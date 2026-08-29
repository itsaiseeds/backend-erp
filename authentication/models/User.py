import pyotp
from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import BaseUserManager, PermissionsMixin
from django.core.exceptions import ValidationError
from django.db import models

from common.models import TimeStampedModel

from ..validators import validate_phone_number

TOTP_ISSUER = "SaiSeeds"
TOTP_ISSUER_INTERNAL = "SaiSeeds Internal"


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, phone_number, name, password=None, **extra_fields):
        if not phone_number:
            raise ValueError("phone_number is required")
        if not name:
            raise ValueError("name is required")

        user = self.model(phone_number=phone_number, name=name, **extra_fields)
        if password:
            user.set_password(password)
        else:
            # Non-superusers authenticate via OTP; they must not have a usable password.
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_user(self, phone_number, name, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(phone_number, name, password, **extra_fields)

    def create_superuser(self, phone_number, name, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_verified", True)

        if not password:
            raise ValueError("Superusers must have a password.")
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        # A superuser must be able to log in via an authenticator app, so give
        # them a fresh TOTP secret (and activate it) unless one was supplied.
        if not extra_fields.get("totp_secret"):
            extra_fields["totp_secret"] = pyotp.random_base32()
            extra_fields["totp_enabled"] = True

        user = self._create_user(phone_number, name, password, **extra_fields)

        # Superusers are self-created / self-verified, satisfying the uniform
        # audit-field rules now that the row exists.
        user.created_by = user
        user.verified_by = user
        user.save(update_fields=["created_by", "verified_by"])
        return user


class User(TimeStampedModel, AbstractBaseUser, PermissionsMixin):
    """Base user for the whole application.

    - phone_number doubles as the username: a plain 10-digit numeric value with
      no country code (e.g. no +91).
    - password is only used by staff (Django admin login); everyone else logs
      in via OTP.
    - created_by is always required once the account exists: superusers
      reference themselves, everyone else references the admin who created
      them (the acting request.user).
    - verified_by is always required whenever is_verified=True; superusers
      self-verify.
    """

    phone_number = models.CharField(
        "phone number",
        max_length=10,
        unique=True,
        db_index=True,
        validators=[validate_phone_number],
        help_text="10-digit mobile number. Used as the login username.",
    )
    name = models.CharField("name", max_length=255)
    email = models.EmailField("email", blank=True, null=True)
    totp_secret = models.CharField(
        "TOTP secret",
        max_length=32,
        blank=True,
        null=True,
        help_text="Base32 secret for authenticator-app (TOTP) login.",
    )
    totp_enabled = models.BooleanField(
        "TOTP enabled",
        default=False,
        help_text="Whether the TOTP secret has been verified and is active.",
    )
    is_verified = models.BooleanField(
        "verified",
        default=False,
        help_text="Whether the phone number has been verified via a superuser or an admin.",
    )
    created_by = models.ForeignKey(
        "self",
        verbose_name="created by",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="created_users",
        help_text="User who created this account (PROTECTed from deletion while referenced); " \
        "superusers reference themselves.",
    )
    verified_by = models.ForeignKey(
        "self",
        verbose_name="verified by",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="verified_users",
        help_text="User who verified this account (PROTECTed from deletion while referenced); " \
        "superusers reference themselves.",
    )

    # Standard Django user fields.
    # A password is only required for staff (Django admin login); everyone else
    # authenticates via OTP, so the field is not required at the form level.
    password = models.CharField("password", max_length=128, blank=True)
    is_staff = models.BooleanField("staff status", default=False)
    is_active = models.BooleanField("active", default=True)
    date_joined = models.DateTimeField("date joined", auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = "phone_number"
    REQUIRED_FIELDS = ["name"]

    class Meta:
        verbose_name = "user"
        verbose_name_plural = "users"

    def __str__(self):
        return f"{self.name} ({self.phone_number})"

    def clean(self):
        super().clean()
        self._validate_user_fields()

    def save(self, *args, **kwargs):
        if kwargs.pop("skip_full_clean", False) is not True:
            self.full_clean(exclude=["password", "last_login", "groups", "user_permissions"])
        super().save(*args, **kwargs)

    def _validate_user_fields(self):
        errors = {}

        if self.is_staff:
            # Anyone who can reach the Django admin portal needs a usable
            # password (admin login is password-based, not OTP). Check both the
            # raw value (empty string) and the unusable "!" sentinel, because
            # has_usable_password() alone treats "" as usable.
            if not self.password or not self.has_usable_password():
                errors["password"] = "Password is required for staff (Django admin) access."  # noqa: S105

        # In-progress (never-saved) rows must not be checked yet: the audit
        # fields are assigned by whoever finishes creating the user. The add
        # form in the admin has no created_by field, so enforcing here during
        # ModelForm._post_clean would crash the view with "'UserForm' has no
        # field named 'created_by'". Both the admin add flow (request.user) and
        # create_superuser (self) set these before the final save.
        if self.pk is not None:
            # Every user — including superusers — must have a creator. Only
            # superusers self-reference; everyone else is created by an admin.
            if self.created_by_id is None:
                errors["created_by"] = "created_by is required for all users."

            # verified_by is required whenever the account is marked verified.
            if self.is_verified and self.verified_by_id is None:
                errors["verified_by"] = (
                    "verified_by is required when is_verified is True."
                )

        if errors:
            raise ValidationError(errors)

    # -- Convenience role helpers -------------------------------------------------
    @property
    def is_salesperson(self):
        if self.id is None:
            return False
        return hasattr(self, "salesperson_profile")

    @property
    def is_admin_user(self):
        """'Admin' = an Admin profile, NOT a Django superuser."""
        if self.id is None:
            return False
        return hasattr(self, "admin_profile")

    @property
    def role(self):
        """Highest-level role this user belongs to."""
        if self.is_superuser:
            return "superuser"
        if self.is_admin_user:
            return "admin"
        if self.is_salesperson:
            return "salesperson"
        return "user"

    @property
    def display_name(self):
        return self.name.strip() or self.phone_number

    @property
    def is_verified_user(self):
        """Whether this non-superuser account is verified (superusers always count)."""
        return self.is_superuser or self.is_verified

    @property
    def can_login_with_password(self):
        """Only staff log in with a password (Django admin); everyone else uses OTP."""
        return self.is_staff

    # -- TOTP (authenticator app) helpers --------------------------------------

    def generate_totp_secret(self) -> str:
        """Create and store a fresh base32 TOTP secret, deactivating it."""
        self.totp_secret = pyotp.random_base32()
        self.totp_enabled = False
        return self.totp_secret

    @property
    def has_totp_secret(self) -> bool:
        return bool(self.totp_secret)

    @property
    def totp(self) -> pyotp.TOTP | None:
        """Return a TOTP object for the stored secret, or None if not enrolled."""
        if not self.totp_secret:
            return None
        return pyotp.TOTP(self.totp_secret)

    def totp_provisioning_uri(self, issuer: str = TOTP_ISSUER) -> str:
        """Return the otpauth:// URI to render as a QR code for enrollment."""
        if self.totp is None:
            raise ValueError("User has no TOTP secret; enroll before provisioning.")
        return self.totp.provisioning_uri(name=self.phone_number, issuer_name=issuer)

    def verify_totp(self, code: str, valid_window: int = 1) -> bool:
        """Verify a TOTP code against the stored secret.

        ``valid_window`` accepts the current 30s window plus that many windows
        in either direction, tolerating minor clock drift.
        """
        if not code or self.totp is None:
            return False
        return self.totp.verify(code, valid_window=valid_window)

    def enable_totp(self) -> None:
        """Mark the verified secret as active for login."""
        self.totp_enabled = True
        self.save(update_fields=["totp_enabled"])
