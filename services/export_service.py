"""
services/export_service.py
---------------------------
Generates CSV and Excel exports of financial data.
"""

import io
from datetime import date, timedelta

import pandas as pd

from repositories.expense_repo import ExpenseRepository
from utils.logger import get_logger

logger = get_logger(__name__)


class ExportService:
    """Generates downloadable financial reports in CSV and Excel formats."""

    def __init__(self):
        self.repo = ExpenseRepository()

    def export_month_csv(self, user_id: int, year: int, month: int) -> io.BytesIO:
        """
        Export a month's transactions as a CSV file.

        Args:
            user_id: Telegram user ID.
            year: Year number.
            month: Month number (1-12).

        Returns:
            A BytesIO buffer containing the CSV data.
        """
        start = date(year, month, 1)
        end = date(year, month + 1, 1) - timedelta(days=1) if month < 12 else date(year, 12, 31)
        expenses = self.repo.get_by_date_range(user_id, start, end)

        data = [
            {
                "التاريخ": e.date.isoformat(),
                "النوع": "مصروف" if e.is_expense() else "دخل",
                "المبلغ": e.amount,
                "العملة": e.currency,
                "الفئة": e.category,
                "الوصف": e.description or "",
            }
            for e in expenses
        ]

        df = pd.DataFrame(data)
        buffer = io.BytesIO()
        df.to_csv(buffer, index=False, encoding="utf-8-sig")
        buffer.seek(0)
        logger.info(f"Exported {len(data)} records as CSV for user {user_id}")
        return buffer

    def export_month_excel(self, user_id: int, year: int, month: int) -> io.BytesIO:
        """
        Export a month's transactions as an Excel (.xlsx) file.

        Args:
            user_id: Telegram user ID.
            year: Year number.
            month: Month number (1-12).

        Returns:
            A BytesIO buffer containing the Excel data.
        """
        start = date(year, month, 1)
        end = date(year, month + 1, 1) - timedelta(days=1) if month < 12 else date(year, 12, 31)
        expenses = self.repo.get_by_date_range(user_id, start, end)

        data = [
            {
                "التاريخ": e.date.isoformat(),
                "النوع": "مصروف" if e.is_expense() else "دخل",
                "المبلغ": e.amount,
                "العملة": e.currency,
                "الفئة": e.category,
                "الوصف": e.description or "",
            }
            for e in expenses
        ]

        df = pd.DataFrame(data)

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="المعاملات", index=False)

            # Add summary sheet
            if data:
                summary = df.groupby("الفئة")["المبلغ"].sum().reset_index()
                summary.columns = ["الفئة", "الإجمالي"]
                summary.to_excel(writer, sheet_name="ملخص", index=False)

        buffer.seek(0)
        logger.info(f"Exported {len(data)} records as Excel for user {user_id}")
        return buffer
