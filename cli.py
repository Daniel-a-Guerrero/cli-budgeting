import os
from sqlite3 import IntegrityError

import db
import analytics
import export
from datetime import datetime
from rich.console import Console
from rich.columns import Columns
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt
from rich import box
from rich import print as fprint
"""
    Main menu loop — Add / View / Delete / Quit
    rich gives you colored tables and a nice layout with zero effort
    Filter view by month, category, or type (income vs expense)

    
    Always .strip() — trailing newlines/spaces from copy-paste or fat fingers will silently break comparisons like choice == "1".
        `choice = input("Enter choice: ").strip()`
    The "press enter to keep current value" pattern — you'll want this for editing statements:
        `new_amount = input(f"Amount [{current_amount}]: ").strip()
        if new_amount:
            amount = int(new_amount)
        else:
            amount = current_amount`
    Don't validate once and give up. Loop until the input is good
        `while True:
        raw = input("Amount: ").strip()
        try:
            amount = int(raw)
            break
        except ValueError:
            print("Please enter a whole number.")` 
    
    Category input will likely come in as a name, not an id, since users don't memorize ids. 
    You'll need a name→id lookup step in cli.py before calling
    add_statement/change_statement with s_category
    get_statements() returns sqlite3.Row objects — 
        remember you can do row["amount"] or dict(row), but row.amount (attribute access) won't work. 
        Useful for Rich tables since you can iterate columns by name
"""
console = Console()
column=Columns()
def prompt_int(label, default=None, get_sid=False, get_cid=False):
    while True:
        raw = input(f"{label}{f' [{default}]' if default is not None else ''}: ").strip()
        if not raw and default is not None:
            return default
        try:
            x=int(raw)
            if get_sid:
                r = db.get_statements("id", x)
                if not r:
                    print(f"Statement {x} doesn't exist")
                    continue
            if get_cid:
                r = db.get_categories()
                if not any(category["id"] == x for category in r):
                    print(f"Category {x} doesn't exist")
                    continue
            return x

        except ValueError:
            print("Please enter a whole number.")

def prompt_date(label, default=None, format=None):
    if isinstance(format, str):
        format = format.lower().strip()
        if format not in db.VALID_DATES:
            format = None
            print(f"Note: '{format}' is not a valid format.")
    while True:
        raw = input(f"{label}{f' [{default}]' if default is not None else ''}: ").strip()
        if not raw and default is not None:
            raw = default
        kind = db.valid_date(raw)
        if kind == "invalid":
            print("Please enter a valid date.")
            continue
        if format is not None and kind != format:
            print(f"Please enter a date matching the '{format}' format.")
            continue
        return raw
def prompt_choice(label, choices, default=None):
    if not hasattr(choices, "__getitem__") or isinstance(choices,str):
        raise TypeError("Error: choices must be an indexable list, tuple, etc.")
    choices_str = " | ".join(choices)
    dmsg = f"\n[dim](Hit Enter for '{default}')[/dim]" if default is not None else ""
    #standardize to lowercase
    while True: 
        dmsg=f"(Hit `Enter` for '{default}')" if default is not None else ""
        console.print(Panel.fit(
            f"[cyan bold]{choices_str}[/cyan bold]\t{dmsg}",
            title=f"[bold purple]{label}[/bold purple]",
            title_align="center"
        ))
        raw = input("> ").strip().lower()
        #Multiple matches, single match, or no match
        matches = [v for v in choices if raw and v.strip().lower().startswith(raw)]
        #print(f"DEBUG: raw='{raw}', matches={matches}")
        if len(matches)==1:
            print(matches[0])
            return matches[0]
        elif len(matches)>1:
            print("Multiple matches found:", matches)
        else:
            if raw=="" and default is not None:
                return default.lower()
            elif default is None:
                return default
            print("Must enter an item in the list")
def type_choice():
    return prompt_choice("Type", ["expense", "income"])

def prompt_category():
    rows=db.get_categories()
    names=[(row["id"], row["name"]) for row in rows]
    while True:
        rChoices=[row["name"] for row in rows]
        x=prompt_choice("Categories:\nSelect one (by name), or leave blank for none", choices=rChoices, default=None)
        if not x:
            return None
        for tup in names:
            if tup[1].lower() == x.lower():
                return int(tup[0])

def prompt_string(label, default=None, file_path=False):
    while True:
        printBracket=default is not None and default.strip() != ""
        raw = input(f"{label}{f' [{default}]' if printBracket else ''}: ").strip()
        if not raw and default is not None:
            return default
        try:
            if not raw:
                raise ValueError("Input cannot be empty.")
            if file_path:
                if os.path.exists(raw):
                    overwrite = input(f"File '{raw}' already exists. Overwrite? (y/n): ").strip().lower()
                    if overwrite != "y":
                        continue
                return os.path.abspath(raw)
            return str(raw)
        except ValueError:
            print("Please enter a valid string.")


# Handle pattern: gather input → try/except call db.py → report result
def handle_stmt_view():
    filter=prompt_choice("Enter a filter",["id", "type", "month", "category"],"n/a")
    value=None
    match filter:
        case "id":
            value=prompt_int("Enter ID number", get_sid=True)
        case "type":
            value=type_choice()
        case "month":
            value=prompt_date("Enter Date", datetime.today().strftime("%Y-%m"),"month")
        case "category":
            value=prompt_category()
    try:
        rows=db.get_statements(filter, value)
        printRows(rows)
        return(rows)
    except (TypeError, ValueError, IndexError) as e:
        print(e)
def handle_stmt_add():
    #Gather input
    date=prompt_date("Date", default=datetime.today().strftime("%Y-%m-%d"))
    amount=prompt_int("Amount (in cents):")
    s_type=type_choice()
    category_id = prompt_category()          # see below — needs its own helper
    desc = prompt_string("Enter description", default="")
    #Call db.py
    try:
        db.add_statement(s_date=date, s_amount=amount, s_category=category_id, s_desc=desc, s_type=s_type)
        #Report Result
        print("Statement added.")
    except (TypeError, ValueError, IndexError) as e:
        print(e)
def handle_stmt_edit():
    try:
        id=prompt_int("Enter an ID")
        field=None
        while field not in db.VALID_FIELDS:
            #field=input(f"Enter a field to modify: {list(db.VALID_FIELDS)}: ").strip().lower()
            field=prompt_choice("Enter a field to modify", [f for f in db.VALID_FIELDS])
        match field:
            case "date":
                value=prompt_date("Enter Date", datetime.today().strftime("%Y-%m-%d %H:%M:%S"))
            case "amount":
                value=prompt_int("Enter amount in cents")
            case "category":
                value=prompt_category()
            case "description":
                value=prompt_string("Enter new description")
            case "type":
                value=type_choice()
        x=db.change_statement(id, field, value)
        print("Statement edited.")
    except (KeyError, ValueError, TypeError) as e:
        print(e)
def handle_stmt_del():
    s_id = prompt_int("Statement ID to delete")
    rows = db.get_statements(field="id", value=s_id)
    if not rows:
        print("No statement with that ID.")
        return
    printRows(rows)
    
    confirm = Prompt.ask("Delete this? (y/n)", ).strip().lower()
    if confirm == "y":
        try:
            db.delete_statement(s_id)
            print("Deleted.")
        except (TypeError, ValueError, IntegrityError) as e:
            print(e)
    elif confirm != "n":
        print("Please enter 'y' or 'n'.")
def handle_analytics():
    rows = db.get_statements()
    if not rows:
        print("No statements to analyze.")
        return
    summary = analytics.monthly_summary(rows)
    print(f"Monthly Summary:")
    print(f"  Income: ${summary['income']/100:.2f}")
    print(f"  Expense: ${summary['expense']/100:.2f}")
    print(f"  Net: ${summary['net']/100:.2f}")

    sc = analytics.spending_by_category(rows)
    for s in sc:
        fprint(f"{s:<20} --> [red]-${sc[s]/100:.2f}[/red]")
def handle_export():
    rows = db.get_statements()
    if not rows:
        print("No statements to save to a CSV.")
        return
    #get valid user filepath
    filepath = prompt_string("Enter file path to save CSV", file_path=True)
    export.export_csv(rows, filepath)

def handle_categories():
    while True:
        #fprint("[bold purple]Options:[/bold purple]\n\t1: View Categories\n\t2: Add Category\n\t3: Edit Category\n\t4: Delete Category\n\t5: Back")
        printMenus(items=["View Categories", "Add Categories", "Edit Categories", "Delete Category", "Back"])
        choice=input(">").strip()
        match choice:
            case "1":
                rows = db.get_categories()
                printRows(rows, "categories")
            case "2":
                name=prompt_string("Enter category name")
                try:
                    db.add_category(name)
                except (TypeError, ValueError, IntegrityError) as e:
                    print(e)
            case "3":
                id=prompt_int("Enter category ID to edit", get_cid=True)
                #Allow user to enter a category name or go back to handle_categories menu
                new_name=prompt_string("Enter new category name")
                try:
                    db.change_category(id, new_name)
                except (TypeError, ValueError, IntegrityError) as e:
                    print(e)
            case "4":
                id=prompt_int("Enter category ID to delete", get_cid=True)
                try:
                    db.delete_category(id)
                except (TypeError, ValueError, IntegrityError) as e:
                    print(e)
            case "5":
                break
            case _:
                print("Please enter a valid number.")
def printRows(rows, format="Statements"):
    if rows==None:
        raise TypeError("Row value is `None`.")
    if format.lower().strip()=="statements":
        table=Table(title=format, title_style="bold magenta")
        table.add_column("ID", justify="right", style="cyan")
        table.add_column("Date")
        table.add_column("Amount", justify="right")
        table.add_column("Type")
        table.add_column("Category", justify="center")
        table.add_column("Description")
        for row in rows:
            amount_style = "green" if row["type"] == "income" else "red"
            table.add_row(
                str(row["id"]),
                row["date"],
                f"[{amount_style}]${row['amount']/100:.2f}[/{amount_style}]",
                f"[{amount_style}]{row['type']}[/{amount_style}]",
                row["name"] or "-",
                row["description"] or "",
            )
        console.print(table)
    elif format.lower().strip()=="categories":
        table=Table(title=format)
        table.add_column("ID", justify="right", style="cyan")
        table.add_column("Name")
        for row in rows:
            table.add_row(str(row["id"]), row["name"])
        console.print(table)
    else:
        print([tuple(row) for row in rows])
def printMenus(title="Options", items=[]):
    c=[f"[bold blue]#{i+1}:[/bold blue][right]{item}[/right]\n" for i, item in enumerate(items)]
    fprint(Panel.fit("".join(c), title=f"[bold purple]{title}[/bold purple]", title_align="center"))
#Main loop
def main_menu():
    while True:
        #fprint("""Options:\n\t1: View Statements\n\t2: Add Statement\n\t3: Edit Statement\n\t4: Delete Statement" \
        #\n\t5: Categories\n\t6: Analytics\n\t7: Export to CSV\n\t8: Quit""")
        printMenus(items=["View Statements", "Add Statement", "Edit Statement", "Delete Statement", "Categories", "Analytics", "Export to CSV", "Quit"])
        choice=input(">").strip()
        match choice:
            case "1":
                handle_stmt_view()
            case "2":
                handle_stmt_add()
            case "3":
                handle_stmt_edit()
            case "4":
                handle_stmt_del()
            case "5":
                handle_categories()
            case "6":
                handle_analytics()
            case "7":
                handle_export()
            case "8":
                break
            case _:
                print("Please enter a valid number.")

if __name__=="__main__":
    main_menu()