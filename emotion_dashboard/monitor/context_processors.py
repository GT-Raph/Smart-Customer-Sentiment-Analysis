from .models import UserPreference


def user_preferences(request):
    if not request.user.is_authenticated:
        return {
            "ui_preferences": None
        }

    preferences = (
        UserPreference.objects
        .filter(
            user=request.user
        )
        .first()
    )

    return {
        "ui_preferences": preferences
    }