import pyodbc
from langchain_core.tools import tool


class SqlTools:
    def __init__(self, conn_str: str):
        self.conn_str = conn_str

    def _connect(self):
        return pyodbc.connect(self.conn_str)

    def get_top_merchants_tool(self):
        @tool
        def get_top_merchants(
            business_id: str,
            month: str,
            limit: int = 5,
        ) -> str:
            """
            Get top merchants for a business and month.

            Args:
                business_id: Business GUID.
                month: Month in YYYY-MM format.
                limit: Number of merchants to return.
            """
            month_date = normalize_month_to_date(month)
            with self._connect() as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    EXEC dbo.spGetTopMerchants
                        @BusinessId = ?,
                        @Month = ?,
                        @Limit = ?
                    """,
                    business_id,
                    month_date,
                    limit,
                )

                rows = cursor.fetchall()

            if not rows:
                return "No top merchant data found."

            lines = []

            for row in rows:
                lines.append(
                    f"{row.MerchantName}: ${float(row.TotalSpend):,.2f}"
                )

            return "\n".join(lines)

        return get_top_merchants

    def get_monthly_summary_tool(self):
        @tool
        def get_monthly_summary(
            business_id: str,
            month: str,
        ) -> str:
            """
            Get monthly financial summary for a business.

            Args:
                business_id: Business GUID.
                month: Month in YYYY-MM format.
            """
            month_date = normalize_month_to_date(month)
            with self._connect() as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    EXEC dbo.spGetFinancialSummary
                        @BusinessId = ?,
                        @Month = ?
                    """,
                    business_id,
                    month_date,
                )

                row = cursor.fetchone()

            if not row:
                return "No monthly summary found."

            return (
                f"Total spending: ${float(row.TotalSpend):,.2f}\n"
                f"Transaction count: {row.TransactionCount}\n"
                # f"Top category: {row.TopCategory}"
            )

        return get_monthly_summary


from datetime import datetime

def normalize_month_to_date(month: str):
    """
    Convert '2026-03' to a Python date: 2026-03-01.
    """
    return datetime.strptime(month, "%Y-%m").date()