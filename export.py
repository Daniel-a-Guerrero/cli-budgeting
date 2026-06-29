"""
Export layer — writes statement data to CSV files.

Planned functions:
- export_csv(rows, filepath) -> writes rows to filepath, returns success/failure

Called by CLI layer
"""
import csv

def export_csv(rows, filepath):
    with open(filepath, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "date", "amount", "category", "description", "type"])
        for r in rows:
            writer.writerow([r["id"], r["date"], r["amount"], r["name"] or "", r["description"] or "", r["type"]])