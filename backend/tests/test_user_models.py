import pytest
from pydantic import ValidationError

from app.schemas.user import (
    LoginRequest,
    SetupRequest,
    UserCreate,
    ChangePasswordRequest,
    PasswordField,
)


class TestPasswordValidation:
    def test_valid_password(self):
        """Mot de passe >= 12 caractères accepté."""
        req = SetupRequest(username="admin", password="securepassword")
        assert req.password == "securepassword"

    def test_short_password_rejected(self):
        """Mot de passe < 12 caractères refusé."""
        with pytest.raises(ValidationError, match="12"):
            SetupRequest(username="admin", password="short")

    def test_login_no_length_check(self):
        """Login n'applique pas de validation de longueur."""
        req = LoginRequest(username="admin", password="any")
        assert req.password == "any"

    def test_change_password_validates_new(self):
        """Le nouveau mot de passe doit faire >= 12 caractères."""
        with pytest.raises(ValidationError, match="12"):
            ChangePasswordRequest(current_password="old", new_password="short")

    def test_change_password_accepts_valid(self):
        req = ChangePasswordRequest(current_password="old", new_password="newlongpassword")
        assert req.new_password == "newlongpassword"


class TestUserSchemas:
    def test_user_create(self):
        u = UserCreate(username="newuser", password="longpassword12", role="operator")
        assert u.role == "operator"

    def test_user_create_invalid_role(self):
        with pytest.raises(ValidationError):
            UserCreate(username="u", password="longpassword12", role="superadmin")

    def test_user_create_short_password(self):
        with pytest.raises(ValidationError, match="12"):
            UserCreate(username="u", password="short", role="admin")
