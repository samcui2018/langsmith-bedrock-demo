from dotenv import load_dotenv
load_dotenv()

import uuid

import pyodbc

from config.settings import Settings
from services.auth_sql_service import AuthSqlService
import time

USER_ID = "36E1AC91-4622-46D5-8116-B81566340B38"
EMAIL = "demo@example.com"
PASSWORD = "demo123"
FIRST_NAME = "Demo User"
LAST_NAME = ""

BUSINESS_ID = "BE90356D-20A8-439A-AADE-FD96E970652C"
BUSINESS_NAME = "Demo Business"
ROLE = "Admin"
CURRENT_TIMESTAMP = time.strftime("%Y-%m-%d %H:%M:%S")
IS_ACTIVE = 1


def main():
    auth_service = AuthSqlService(Settings.SQL_CONN_STR)
    password_hash = auth_service.hash_password(PASSWORD)

    with pyodbc.connect(Settings.SQL_CONN_STR) as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            IF NOT EXISTS (
                SELECT 1 FROM dbo.Users WHERE email = ?
            )
            BEGIN
                INSERT INTO dbo.Users (                                    
                    UserId,
                    Email,
                    FirstName,
                    LastName,
                    role,               
                    PasswordHash,
                    CreatedAt,
                    IsActive
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            END
            """,           
            EMAIL,
            USER_ID,
            EMAIL,
            FIRST_NAME,
            LAST_NAME,
            ROLE,
            password_hash,
            CURRENT_TIMESTAMP,
            IS_ACTIVE
        )

        cursor.execute(
            """
            IF NOT EXISTS (
                SELECT 1
                FROM dbo.UserBusinesses
                WHERE UserId = ?
                  AND BusinessId = ?
            )
            BEGIN
                INSERT INTO dbo.UserBusinesses (
                    UserId,
                    BusinessId,
                    RoleName,
                    IsDefault,
                    CreatedAt,
                    UserBusinessId
                )
                VALUES (?, ?, ?, ?, ?, ?)
            END
            """,
            USER_ID,
            BUSINESS_ID,
            USER_ID,
            BUSINESS_ID,
            ROLE,
            1,  # IsDefault
            CURRENT_TIMESTAMP,
            str(uuid.uuid4())
        )

        conn.commit()

    print("Seeded demo user and business.")
    print("Email: demo@example.com")
    print("Password: demo123")


if __name__ == "__main__":
    main()