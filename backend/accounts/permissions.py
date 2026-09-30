from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsAdminOrReadOnly(BasePermission):
    """
    Anyone may read, but only a staff administrator may write.

    This is the project-wide write rule. Teacher accounts are staff=False, so a
    token issued at /auth/teacher/token/ is good for reading the site but cannot
    create, edit or delete news, admissions, gallery, settings and so on. Without
    it any signed-in person could call every admin endpoint directly, no matter
    what the dashboard UI chose to show them.

    `is_staff` is the check rather than the role field so that the existing
    administrator accounts keep working untouched.
    """

    message = 'Only administrators can modify this content.'

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        user = request.user
        return bool(user and user.is_authenticated and user.is_staff)


class IsTeacherOrReadOnly(BasePermission):
    """
    Read for anyone signed in, writes for a teacher *or* an administrator.

    Used on the endpoints a teacher is meant to work with, such as entering
    student results for their own classes.
    """

    message = 'Only teachers can modify this.'

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        user = request.user
        return bool(user and user.is_authenticated and (user.is_staff or getattr(user, 'is_teacher', False)))
