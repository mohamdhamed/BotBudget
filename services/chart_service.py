"""
services/chart_service.py
--------------------------
Generates chart images for expense analysis.
Uses matplotlib to create pie/bar charts and returns them as BytesIO buffers.
"""

import io
from datetime import date, timedelta

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend for server use
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

from repositories.expense_repo import ExpenseRepository
from utils.logger import get_logger

logger = get_logger(__name__)

# Try to use a font that supports Arabic
_ARABIC_FONTS = ["Noto Sans Arabic", "Arial", "DejaVu Sans", "Tahoma"]
_font_found = False
for _f in _ARABIC_FONTS:
    if any(_f.lower() in f.name.lower() for f in fm.fontManager.ttflist):
        plt.rcParams["font.family"] = _f
        _font_found = True
        break

if not _font_found:
    plt.rcParams["font.family"] = "DejaVu Sans"

plt.rcParams["figure.facecolor"] = "#1a1a2e"
plt.rcParams["text.color"] = "#e0e0e0"
plt.rcParams["axes.facecolor"] = "#1a1a2e"


class ChartService:
    """Generates visual charts for expense data."""

    def __init__(self):
        self.repo = ExpenseRepository()

    def generate_monthly_pie(self, user_id: int, year: int = None,
                              month: int = None) -> io.BytesIO | None:
        """
        Generate a pie chart of expenses by category for a given month.

        Returns:
            BytesIO buffer with PNG image, or None if no data.
        """
        today = date.today()
        y = year or today.year
        m = month or today.month

        start = date(y, m, 1)
        end = date(y, m + 1, 1) - timedelta(days=1) if m < 12 else date(y, 12, 31)

        categories = self.repo.get_category_summary(user_id, start, end)
        if not categories:
            return None

        labels = [c["category"] for c in categories]
        values = [c["total"] for c in categories]
        total = sum(values)

        # Color palette
        colors = [
            "#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4",
            "#FFEAA7", "#DDA0DD", "#98D8C8", "#F7DC6F",
            "#BB8FCE", "#85C1E9", "#F1948A", "#82E0AA",
            "#F8C471", "#AED6F1", "#D2B4DE", "#A3E4D7",
            "#FAD7A0", "#FADBD8",
        ]

        fig, ax = plt.subplots(figsize=(8, 6))

        wedges, texts, autotexts = ax.pie(
            values,
            labels=None,
            autopct=lambda pct: f"{pct:.1f}%",
            colors=colors[:len(values)],
            startangle=90,
            pctdistance=0.82,
            wedgeprops=dict(width=0.5, edgecolor="#1a1a2e", linewidth=2),
        )

        for autotext in autotexts:
            autotext.set_color("white")
            autotext.set_fontsize(10)
            autotext.set_fontweight("bold")

        # Legend
        legend_labels = [f"{l}: {v:.2f}€" for l, v in zip(labels, values)]
        ax.legend(
            wedges, legend_labels,
            loc="center left",
            bbox_to_anchor=(1, 0, 0.5, 1),
            fontsize=10,
            frameon=False,
        )

        ax.set_title(
            f"📊 توزيع المصاريف - {m}/{y}\nالإجمالي: {total:.2f}€",
            fontsize=14,
            fontweight="bold",
            pad=20,
        )

        plt.tight_layout()

        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=150, bbox_inches="tight",
                    facecolor=fig.get_facecolor())
        buf.seek(0)
        plt.close(fig)

        logger.info(f"Generated pie chart for user {user_id}, {m}/{y}")
        return buf

    def generate_weekly_bar(self, user_id: int) -> io.BytesIO | None:
        """
        Generate a bar chart of daily expenses for the last 7 days.

        Returns:
            BytesIO buffer with PNG image, or None if no data.
        """
        today = date.today()
        week_start = today - timedelta(days=6)

        expenses = self.repo.get_by_date_range(user_id, week_start, today)
        if not expenses:
            return None

        # Group by day
        daily = {}
        for d in range(7):
            day = week_start + timedelta(days=d)
            daily[day] = 0.0

        for e in expenses:
            if e.is_expense() and e.date in daily:
                daily[e.date] += e.amount

        days = list(daily.keys())
        amounts = list(daily.values())
        day_labels = [d.strftime("%a\n%d/%m") for d in days]

        fig, ax = plt.subplots(figsize=(9, 5))

        bars = ax.bar(
            range(len(days)), amounts,
            color=["#FF6B6B" if a > 0 else "#4ECDC4" for a in amounts],
            edgecolor="#1a1a2e",
            linewidth=1.5,
            width=0.6,
            zorder=3,
        )

        # Add value labels on bars
        for bar, amount in zip(bars, amounts):
            if amount > 0:
                ax.text(
                    bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                    f"{amount:.0f}€",
                    ha="center", va="bottom",
                    color="#e0e0e0", fontsize=10, fontweight="bold",
                )

        ax.set_xticks(range(len(days)))
        ax.set_xticklabels(day_labels, fontsize=9, color="#e0e0e0")
        ax.set_ylabel("المبلغ (€)", fontsize=11, color="#e0e0e0")
        ax.set_title(
            f"📈 المصاريف اليومية - آخر ٧ أيام\nالإجمالي: {sum(amounts):.2f}€",
            fontsize=13, fontweight="bold", pad=15,
        )

        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color("#444")
        ax.spines["bottom"].set_color("#444")
        ax.tick_params(colors="#e0e0e0")
        ax.grid(axis="y", alpha=0.2, color="#888")
        ax.set_axisbelow(True)

        plt.tight_layout()

        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=150, bbox_inches="tight",
                    facecolor=fig.get_facecolor())
        buf.seek(0)
        plt.close(fig)

        logger.info(f"Generated weekly bar chart for user {user_id}")
        return buf
