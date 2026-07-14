from django import forms
from django.contrib.auth.forms import (
    PasswordChangeForm,
)

from .models import (
    BankSettings,
    Branch,
    CustomUser,
    UserPreference,
)


TEXT_INPUT_CLASS = "form-control"
CHECKBOX_CLASS = "form-check-input"


class ProfileSettingsForm(
    forms.ModelForm
):
    class Meta:
        model = CustomUser

        fields = (
            "first_name",
            "last_name",
            "email",
        )

        widgets = {
            "first_name": forms.TextInput(
                attrs={
                    "class": TEXT_INPUT_CLASS,
                    "placeholder": "First name",
                }
            ),

            "last_name": forms.TextInput(
                attrs={
                    "class": TEXT_INPUT_CLASS,
                    "placeholder": "Last name",
                }
            ),

            "email": forms.EmailInput(
                attrs={
                    "class": TEXT_INPUT_CLASS,
                    "placeholder": (
                        "name@example.com"
                    ),
                }
            ),
        }

    def clean_email(self):
        email = (
            self.cleaned_data
            .get("email", "")
            .strip()
            .lower()
        )

        if not email:
            return ""

        duplicate_exists = (
            CustomUser.objects
            .exclude(pk=self.instance.pk)
            .filter(email__iexact=email)
            .exists()
        )

        if duplicate_exists:
            raise forms.ValidationError(
                "Another account already uses "
                "this email address."
            )

        return email


class DashboardPreferenceForm(
    forms.ModelForm
):
    class Meta:
        model = UserPreference

        fields = (
            "default_date_range",
            "default_hourly_range",
            "default_branch",
            "auto_refresh_seconds",
            "compact_mode",
            "reduce_motion",
        )

    def __init__(
        self,
        *args,
        user,
        **kwargs,
    ):
        super().__init__(
            *args,
            **kwargs,
        )

        self.user = user

        branches = Branch.objects.filter(
            is_active=True
        ).select_related("bank")

        if user.is_superuser:
            pass

        elif user.branch_id:
            branches = branches.filter(
                pk=user.branch_id
            )

        elif user.bank_id:
            branches = branches.filter(
                bank_id=user.bank_id
            )

        else:
            branches = branches.none()

        self.fields[
            "default_branch"
        ].queryset = branches

        self.fields[
            "default_branch"
        ].required = False

    def clean_default_branch(self):
        branch = self.cleaned_data.get(
            "default_branch"
        )

        if not branch:
            return None

        if self.user.is_superuser:
            return branch

        if (
            self.user.branch_id
            and branch.id
            != self.user.branch_id
        ):
            raise forms.ValidationError(
                "You cannot select another branch."
            )

        if (
            self.user.bank_id
            and branch.bank_id
            != self.user.bank_id
        ):
            raise forms.ValidationError(
                "The branch does not belong "
                "to your bank."
            )

        return branch


class NotificationPreferenceForm(
    forms.ModelForm
):
    class Meta:
        model = UserPreference

        fields = (
            "email_weekly_summary",
            "notify_negative",
            "negative_threshold",
            "minimum_detections",
        )

        widgets = {
            "email_weekly_summary": (
                forms.CheckboxInput(
                    attrs={
                        "class": CHECKBOX_CLASS,
                    }
                )
            ),

            "notify_negative": (
                forms.CheckboxInput(
                    attrs={
                        "class": CHECKBOX_CLASS,
                    }
                )
            ),

            "negative_threshold": (
                forms.NumberInput(
                    attrs={
                        "class": TEXT_INPUT_CLASS,
                        "min": 1,
                        "max": 100,
                    }
                )
            ),

            "minimum_detections": (
                forms.NumberInput(
                    attrs={
                        "class": TEXT_INPUT_CLASS,
                        "min": 1,
                    }
                )
            ),
        }


class BankSettingsForm(
    forms.ModelForm
):
    TIMEZONE_CHOICES = (
        (
            "Africa/Accra",
            "Africa/Accra",
        ),
        (
            "UTC",
            "UTC",
        ),
        (
            "Europe/London",
            "Europe/London",
        ),
        (
            "America/New_York",
            "America/New York",
        ),
    )

    timezone = forms.ChoiceField(
        choices=TIMEZONE_CHOICES,
    )

    class Meta:
        model = BankSettings

        fields = (
            "timezone",
            "image_retention_days",
            "record_retention_days",
            "delete_images_after_retention",
            "offline_after_minutes",
        )

        widgets = {
            "image_retention_days": (
                forms.NumberInput(
                    attrs={
                        "class": TEXT_INPUT_CLASS,
                        "min": 1,
                    }
                )
            ),

            "record_retention_days": (
                forms.NumberInput(
                    attrs={
                        "class": TEXT_INPUT_CLASS,
                        "min": 1,
                    }
                )
            ),

            "delete_images_after_retention": (
                forms.CheckboxInput(
                    attrs={
                        "class": CHECKBOX_CLASS,
                    }
                )
            ),

            "offline_after_minutes": (
                forms.NumberInput(
                    attrs={
                        "class": TEXT_INPUT_CLASS,
                        "min": 1,
                    }
                )
            ),
        }


class BranchSettingsForm(
    forms.ModelForm
):
    class Meta:
        model = Branch

        fields = (
            "name",
            "code",
            "pc_prefix",
            "location",
            "is_active",
        )

        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": TEXT_INPUT_CLASS,
                }
            ),

            "code": forms.TextInput(
                attrs={
                    "class": TEXT_INPUT_CLASS,
                }
            ),

            "pc_prefix": forms.TextInput(
                attrs={
                    "class": TEXT_INPUT_CLASS,
                }
            ),

            "location": forms.TextInput(
                attrs={
                    "class": TEXT_INPUT_CLASS,
                }
            ),

            "is_active": forms.CheckboxInput(
                attrs={
                    "class": CHECKBOX_CLASS,
                }
            ),
        }

    def clean_code(self):
        return (
            self.cleaned_data["code"]
            .strip()
            .upper()
        )

    def clean_pc_prefix(self):
        return (
            self.cleaned_data["pc_prefix"]
            .strip()
            .upper()
        )


class StyledPasswordChangeForm(
    PasswordChangeForm
):
    def __init__(
        self,
        *args,
        **kwargs,
    ):
        super().__init__(
            *args,
            **kwargs,
        )

        for field in self.fields.values():
            field.widget.attrs.update(
                {
                    "class": TEXT_INPUT_CLASS,
                    "autocomplete": (
                        "new-password"
                    ),
                }
            )

        self.fields[
            "old_password"
        ].widget.attrs[
            "autocomplete"
        ] = "current-password"