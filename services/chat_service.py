import uuid
import pyodbc


class ChatService:
    def __init__(self, conn_str: str):
        self.conn_str = conn_str

    def _connect(self):
        return pyodbc.connect(self.conn_str)

    def create_session(self, user_id: str, business_id: str, title: str | None = None):
        session_id = str(uuid.uuid4())

        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO dbo.ChatSessions (
                    ChatSessionId, UserId, BusinessId, Title
                )
                VALUES (?, ?, ?, ?)
                """,
                session_id,
                user_id,
                business_id,
                title,
            )
            conn.commit()

        return session_id

    def get_sessions(self, user_id: str):
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT ChatSessionId, BusinessId, Title, CreatedAt, UpdatedAt
                FROM dbo.ChatSessions
                WHERE UserId = ?
                ORDER BY UpdatedAt DESC
                """,
                user_id,
            )
            rows = cursor.fetchall()

        return [
            {
                "chat_session_id": str(row.ChatSessionId),
                "business_id": str(row.BusinessId),
                "title": row.Title,
                "created_at": str(row.CreatedAt),
                "updated_at": str(row.UpdatedAt),
            }
            for row in rows
        ]

    def get_messages(self, chat_session_id: str, user_id: str):
        with self._connect() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM dbo.ChatSessions
                WHERE ChatSessionId = ?
                  AND UserId = ?
                """,
                chat_session_id,
                user_id,
            )

            if cursor.fetchone()[0] == 0:
                return None

            cursor.execute(
                """
                SELECT Role, Content, CreatedAt
                FROM dbo.ChatMessages
                WHERE ChatSessionId = ?
                ORDER BY CreatedAt
                """,
                chat_session_id,
            )

            rows = cursor.fetchall()

        return [
            {
                "role": row.Role,
                "content": row.Content,
                "created_at": str(row.CreatedAt),
            }
            for row in rows
        ]

    def add_message(self, chat_session_id: str, role: str, content: str):
        message_id = str(uuid.uuid4())

        with self._connect() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO dbo.ChatMessages (
                    ChatMessageId, ChatSessionId, Role, Content
                )
                VALUES (?, ?, ?, ?)
                """,
                message_id,
                chat_session_id,
                role,
                content,
            )

            cursor.execute(
                """
                UPDATE dbo.ChatSessions
                SET UpdatedAt = SYSUTCDATETIME()
                WHERE ChatSessionId = ?
                """,
                chat_session_id,
            )

            conn.commit()

        return message_id