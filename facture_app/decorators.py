from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.admin.views.decorators import user_passes_test
from django.contrib.auth.mixins import UserPassesTestMixin

def superuser_required(
    function=None, redirect_field_name=REDIRECT_FIELD_NAME, login_url=None
):
    """
    Décorateur pour les vues qui vérifie si l'utilisateur est connecté et superutilisateur,
    redirigeant vers la page de connexion si nécessaire.
    """
    actual_decorator = user_passes_test(
        lambda u: u.is_active and u.is_superuser,
        login_url=login_url,
        redirect_field_name=redirect_field_name,
    )
    if function:
        return actual_decorator(function)
    return actual_decorator

class LoginRequiredSuperuserMixin(UserPassesTestMixin):
    """Mixin pour vérifier que l'utilisateur est superutilisateur."""
    def test_func(self):
        return self.request.user.is_active and self.request.user.is_superuser