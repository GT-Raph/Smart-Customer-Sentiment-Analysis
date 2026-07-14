from .models import UserPreference


def user_preferences(request):
    if not request.user.is_authenticated:
        return {
            "ui_preferences": None
        }

    preferences, _ = (
        UserPreference.objects
        .get_or_create(
            user=request.user
        )
    )

    return {
        "ui_preferences": preferences
    }