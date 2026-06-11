from datetime import datetime, timedelta, timezone

import pyodbc
from jose import JWTError, jwt
from passlib.context import CryptContext

from config.settings import Settings


class AuthSqlService:
    def __init__(self, conn_str: str):
        self.conn_str = conn_str
        self.password_context = CryptContext(
            schemes=["bcrypt"],
            deprecated="auto",
        )

    def _connect(self):
        return pyodbc.connect(self.conn_str)

    def hash_password(self, password: str) -> str:
        return self.password_context.hash(password)

    def verify_password(self, password: str, hashed_password: str) -> bool:
        return self.password_context.verify(password, hashed_password)

    def authenticate_user(self, email: str, password: str):
        with self._connect() as conn:
            cursor = conn.cursor()


            cursor.execute(
                """
                SELECT UserId, Email, CONCAT(FirstName, ' ', LastName) AS DisplayName, PasswordHash
                FROM dbo.Users
                WHERE Email = ?
                  AND IsActive = 1
                """,
                email,
            )

            row = cursor.fetchone()

        if not row:
            return None

        if not self.verify_password(password, row.PasswordHash):
            return None

        return {
            "user_id": str(row.UserId),
            "email": row.Email,
            "name": row.DisplayName.strip() if row.DisplayName else row.Email
        }

    def create_access_token(self, user: dict):
        expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=Settings.JWT_EXPIRE_MINUTES
        )

        payload = {
            "sub": user["user_id"],
            "email": user["email"],
            "name": user["name"],
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
        with self._connect() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT UserId, Email, CONCAT(FirstName, ' ', LastName) AS DisplayName
                FROM dbo.Users
                WHERE UserId = ?
                  AND IsActive = 1
                """,
                user_id,
            )

            row = cursor.fetchone()

        if not row:
            return None

        return {
            "user_id": str(row.UserId),
            "email": row.Email,
            "name": row.DisplayName.strip() if row.DisplayName else row.Email
        }

    def get_allowed_businesses(self, user_id: str):
        with self._connect() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT b.BusinessId, b.BusinessName
                FROM dbo.UserBusinesses a join dbo.Businesses b on a.BusinessId = b.BusinessId
                WHERE UserId = ?
                ORDER BY BusinessName
                """,
                user_id,
            )

            rows = cursor.fetchall()

        return [
            {
                "business_id": str(row.BusinessId),
                "name": row.BusinessName,
            }
            for row in rows
        ]

    def user_can_access_business(self, user_id: str, business_id: str) -> bool:
        with self._connect() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM dbo.UserBusinesses
                WHERE UserId = ?
                  AND BusinessId = ?
                """,
                user_id,
                business_id,
            )

            count = cursor.fetchone()[0]

        return count > 0
    def get_user_businesses(self, user_id: str):
        with pyodbc.connect(self.conn_str) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT 
                    b.BusinessId,
                    b.BusinessName,
                    ub.RoleName,
                    ub.IsDefault
                FROM dbo.UserBusinesses ub
                JOIN dbo.Businesses b
                    ON b.BusinessId = ub.BusinessId
                WHERE ub.UserId = ?
                ORDER BY ub.IsDefault DESC, b.BusinessName
                """,
                user_id,
            )

            return [
                {
                    "business_id": str(row.BusinessId),
                    "business_name": row.BusinessName,
                    "role": row.RoleName,
                    "is_default": bool(row.IsDefault),
                }
                for row in cursor.fetchall()
            ]