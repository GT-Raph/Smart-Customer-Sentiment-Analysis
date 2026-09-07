from django import forms
from django.contrib.auth.forms import PasswordChangeForm

from .models import Branch, CustomUser, UserPreference


TEXT_INPUT_CLASS = "form-control"
CHECKBOX_CLASS = "form-check-input"


class ProfileSettingsForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ("first_name", "last_name", "email")
        widgets = {
            "first_name": forms.TextInput(
                attrs={"class": TEXT_INPUT_CLASS, "placeholder": "First name"}
            ),
            "last_name": forms.TextInput(
                attrs={"class": TEXT_INPUT_CLASS, "placeholder": "Last name"}
            ),
            "email": forms.EmailInput(
                attrs={"class": TEXT_INPUT_CLASS, "placeholder": "name@example.com"}
            ),
        }

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip().lower()
        if email and (
            CustomUser.objects.exclude(pk=self.instance.pk)
            .filter(email__iexact=email)
            .exists()
        ):
            raise forms.ValidationError("Another account already uses this email address.")
        return email


class DashboardPreferenceForm(forms.ModelForm):
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

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        branches = Branch.objects.filter(is_active=True)
        if not user.is_superuser:
            branches = (
                branches.filter(pk=user.branch_id)
                if user.branch_id
                else branches.none()
            )
        self.fields["default_branch"].queryset = branches
        self.fields["default_branch"].required = False


class NotificationPreferenceForm(forms.ModelForm):
    class Meta:
        model = UserPreference
        fields = (
            "email_weekly_summary",
            "notify_negative",
            "negative_threshold",
            "minimum_detections",
        )
        widgets = {
            "email_weekly_summary": forms.CheckboxInput(
                attrs={"class": CHECKBOX_CLASS}
            ),
            "notify_negative": forms.CheckboxInput(attrs={"class": CHECKBOX_CLASS}),
            "negative_threshold": forms.NumberInput(
                attrs={"class": TEXT_INPUT_CLASS, "min": 1, "max": 100}
            ),
            "minimum_detections": forms.NumberInput(
                attrs={"class": TEXT_INPUT_CLASS, "min": 1}
            ),
        }


class BranchSettingsForm(forms.ModelForm):
    class Meta:
        model = Branch
        fields = ("name", "pc_prefix", "location", "is_active")
        widgets = {
            "name": forms.TextInput(attrs={"class": TEXT_INPUT_CLASS}),
            "pc_prefix": forms.TextInput(attrs={"class": TEXT_INPUT_CLASS}),
            "location": forms.TextInput(attrs={"class": TEXT_INPUT_CLASS}),
            "is_active": forms.CheckboxInput(attrs={"class": CHECKBOX_CLASS}),
        }

    def clean_pc_prefix(self):
        return self.cleaned_data["pc_prefix"].strip().upper()


class StyledPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update(
                {"class": TEXT_INPUT_CLASS, "autocomplete": "new-password"}
            )
        self.fields["old_password"].widget.attrs["autocomplete"] = "current-password"
