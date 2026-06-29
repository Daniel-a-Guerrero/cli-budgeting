"""
Analytics layer — computes summaries and generates charts from statement data.
Consumes db.get_statements() output; does not query SQLite directly.

Planned functions:
- monthly_summary(rows) -> dict of {total_income, total_expense, net}
- spending_by_category(rows) -> dict of {category_name: total}
- plot_category_breakdown(rows) -> matplotlib bar chart
- plot_spending_over_time(rows) -> matplotlib line chart, cumulative or daily

Called by CLI layer
"""
import matplotlib.pyplot as plt
from collections import defaultdict

def monthly_summary(rows):
    income = sum(r["amount"] for r in rows if r["type"] == "income")
    expense = sum(r["amount"] for r in rows if r["type"] == "expense")
    return {"income": income, "expense": expense, "net": income - expense}

def spending_by_category(rows):
    totals = defaultdict(int)
    for r in rows:
        if r["type"] == "expense":
            totals[r["name"] or "Uncategorized"] += r["amount"]
    return dict(totals)