from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from config.settings import Settings


class AuthService:
    def __init__(self):
        self.password_context = CryptContext(
            schemes=["bcrypt"],
            deprecated="auto",
        )

        self.users = {
            "demo": {
                "user_id": "demo-user",
                "username": "demo",
                "name": "Demo User",
                # password: demo123
                "hashed_password": self.password_context.hash("demo123"),
                "businesses": [
                    {
                        "business_id": "BE90356D-20A8-439A-AADE-FD96E970652C",
                        "name": "Demo Business",
                    }
                ],
            }
        }

    def authenticate_user(self, username: str, password: str):
        user = self.users.get(username)

        if not user:
            return None

        if not self.password_context.verify(
            password,
            user["hashed_password"],
        ):
            return None

        return user

    def create_access_token(self, user: dict):
        expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=Settings.JWT_EXPIRE_MINUTES
        )

        payload = {
            "sub": user["user_id"],
            "username": user["username"],
            "exp": expires_at,
        }

        return jwt.encode(
            payload,
            Settings.JWT_SECRET_KEY,
            algorithm=Settings.JWT_ALGORITHM,
        )

    def decode_access_token(self, token: str):
        try:
            return jwt.decode(
                token,
                Settings.JWT_SECRET_KEY,
                algorithms=[Settings.JWT_ALGORITHM],
            )
        except JWTError:
            return None

    def get_user_by_id(self, user_id: str):
        for user in self.users.values():
            if user["user_id"] == user_id:
                return user

        return None

    def get_allowed_businesses(self, user_id: str):
        user = self.get_user_by_id(user_id)

        if not user:
            return []

        return user["businesses"]

    def user_can_access_business(self, user_id: str, business_id: str) -> bool:
        businesses = self.get_allowed_businesses(user_id)

        return any(
            b["business_id"].lower() == business_id.lower()
            for b in businesses
        )