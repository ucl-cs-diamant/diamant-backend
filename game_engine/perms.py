from rest_framework import permissions

from game_engine.models import User, UserCode


class UserOwnsCode(permissions.BasePermission):
    message = "You do not have permission to perform this action."

    def has_permission(self, request, view):
        # print(request.session.get('github_username', None))
        if (github_username := request.session.get('github_username', None)) is None:
            return False
        return User.objects.filter(github_username=github_username).exists()

    def has_object_permission(self, request, view, obj: UserCode):
        self.message = f"You do not have permission to update UserCode {obj.pk}."
        return obj.user.github_username == request.session.get('github_username', None)
