#SQLite Layer

import sqlite3
from datetime import datetime
import os

class CategoryNotFoundError(Exception): pass
class InvalidFieldError(Exception): pass
db_name="tutorial.db"
sql_setup=[
    """CREATE TABLE IF NOT EXISTS categories(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS statements(
    id INTEGER PRIMARY KEY AUTOINCREMENT, 
    date TEXT NOT NULL, 
    amount INTEGER NOT NULL, --REAL has rounding errors
    category INTEGER, 
    description TEXT, 
    type TEXT NOT NULL, -- income or expense
    FOREIGN KEY(category) REFERENCES categories(id) ON DELETE SET NULL)
    """
]
sql_category={
    "select_all":"""SELECT * FROM categories""",
    "select_names":"""SELECT name FROM categories""",
    "select_one":"""SELECT * FROM categories WHERE id = ?""",
    "insert":"""INSERT INTO categories (name) VALUES (?)""",
    "modify":"""UPDATE categories SET name = ? WHERE id = ?""",
    "delete_id":"""DELETE FROM categories WHERE id = ?""",
    "delete_name":"""DELETE FROM categories WHERE name = ?"""}
sql_statement={
    "select_all":"""SELECT * FROM statements""",
    "select_all_cat":"""SELECT s.*, c.name
                        FROM statements as s
                        LEFT JOIN categories as c ON s.category = c.id""",
    "select_one":"""SELECT s.* FROM statements AS s WHERE s.id = ?""",
    "select_one_cat":"""SELECT s.*, c.name 
                        FROM statements as s
                        LEFT JOIN categories as c ON s.category = c.id
                        WHERE s.id = ?""",
    "select_by_type":  """SELECT s.*, c.name FROM statements AS s
                      LEFT JOIN categories AS c ON s.category = c.id
                      WHERE s.type = ?""",
    "select_by_month":  """SELECT s.*, c.name FROM statements AS s
                        LEFT JOIN categories AS c ON s.category = c.id
                        WHERE strftime('%Y-%m', s.date)  = ?""",
    "select_by_category": """SELECT s.*, c.* FROM statements AS s
                         LEFT JOIN categories AS c ON s.category = c.id
                         WHERE s.category = ?""",
     "select_by_category_null": """SELECT s.*, c.* FROM statements AS s
                         LEFT JOIN categories AS c ON s.category = c.id
                         WHERE s.category IS NULL""",
    "insert":"""INSERT INTO statements (date, amount, category, description, type) VALUES (?, ?, ?, ?, ?)""",
    "modify_date":        "UPDATE statements SET date = ? WHERE id = ?",
    "modify_amount":      "UPDATE statements SET amount = ? WHERE id = ?",
    "modify_category":    "UPDATE statements SET category = ? WHERE id = ?",
    "modify_description": "UPDATE statements SET description = ? WHERE id = ?",
    "modify_type":        "UPDATE statements SET type = ? WHERE id = ?",
    "delete":"""DELETE FROM statements WHERE id = ?""",

}
VALID_FIELDS = {"date", "amount", "category", "description", "type"} #For statements
VALID_TYPES=("expense", "income")
VALID_DATES=("datetime", "date", "month")
def get_connection(): #Establishes connection to sqlite database
    con = sqlite3.connect(db_name)
    con.row_factory=sqlite3.Row #Allows accessing columns by name
    con.execute("PRAGMA foreign_keys = ON") #Enforces data relationships, don't orphan transactions when you delete categories
    return con
#Initial connection
def init_db(): #Creates necessary tables on first run
    with get_connection() as con:
        cursor=con.cursor()
        for stmt in sql_setup:
            cursor.execute(stmt)
        con.commit()#Commit any pending transaction to the database. If autocommit is True, or there is no open transaction, this method does nothing.
def reset_db():
    if os.path.exists(db_name):
        os.remove(db_name)
    init_db()
    print(f"Database reset.")

#Category helpers

def valid_category(x):
    if not x:
        return False
    if x[0].isdigit() or x[0]==' ':
        return False
    return True

def get_categories():
    with get_connection() as con:
        cursor=con.cursor()
        cursor.execute(sql_category["select_all"])
        categories=cursor.fetchall()
    return categories
def get_categories_name():
    with get_connection() as con:
        cursor=con.cursor()
        cursor.execute(sql_category["select_names"])
        categories=cursor.fetchall()
    return categories

def add_category(c_name):
    #Must ensure category doesn't start with a number
    if not isinstance(c_name,str):
        raise TypeError("Error: Category name must be a string")
    if not valid_category(c_name):
        raise ValueError("Error: Category name must not start with a number or space")
    with get_connection() as con:
        cursor=con.cursor()
        try:
            #checks if the name already exists, if it does, it will raise an IntegrityError
            cursor.execute(sql_category["select_names"])
            categories=cursor.fetchall()
            if any(c_name == category["name"] for category in categories):
                raise sqlite3.IntegrityError("Category already exists.")
            cursor.execute(sql_category["insert"], (c_name,))
            con.commit()
        except sqlite3.IntegrityError:
            print(f"Category '{c_name}' already exists.")

def change_category(c_id, c_name):
    if not isinstance(c_name,str) or not isinstance(c_id,int):
        raise TypeError("Error: Category name must be a string and category ID must be an integer")
    with get_connection() as con:
        cursor=con.cursor()
        try:
            cursor.execute(sql_category["select_names"])
            categories=cursor.fetchall()
            if any(c_name == category["name"] for category in categories):
                raise sqlite3.IntegrityError("Category already exists.")
            cursor.execute(sql_category["modify"],(c_name,c_id,))
            con.commit()
        except sqlite3.IntegrityError:
            print(f"Category '{c_name}' already exists.")

def delete_category(c):
    with get_connection() as con:
        cursor=con.cursor()
        dX="delete_name"
        if isinstance(c, int):
            #Delete based on id
            dX="delete_id"
        elif not valid_category(c):
            raise InvalidFieldError("Invalid id/category name.")
        cursor.execute(sql_category[dX],(c,))
        con.commit()

#Statement helpers
def valid_date(date_str): #Determines if date is in proper format. Can be datetime or date. Later, if date is 
    try:
        datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        return "datetime"
    except ValueError:
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            return "date"
        except ValueError:
            try:
                datetime.strptime(date_str, "%Y-%m")
                return "month"
            except ValueError:
                return "invalid"

def get_statements(field="", value=None):
    fields={"id":"select_one_cat", "type":"select_by_type", "month":"select_by_month", "category":"select_by_category"}
    with get_connection() as con:
        cursor=con.cursor()
        query="select_all_cat"
        if field in fields:
            query=fields[field]
            if field=="id":
                if not isinstance(value,int):
                    raise TypeError("Error: Must enter integer for an id number")
                elif value<0:
                    raise ValueError("Error: must enter positive valid id number")
            elif field=="type":
                if not isinstance(value,str) or value.lower() not in VALID_TYPES:
                    raise ValueError("Error: Type must be 'income' or 'expense'")
                value = value.lower()
            elif field=="month":
                try:
                    datetime.strptime(value, "%Y-%m")
                except ValueError:
                    raise ValueError("Error: Month must fit format '%Y-%m'")
            elif field=="category":
                if value is None:
                    query='select_by_category_null'
                elif not isinstance(value,int):
                    raise TypeError(f"Error: Must enter integer for a category id number: {value}")
                elif value<0:
                    raise ValueError("Error: must enter positive valid category id number")
            value=(value,)
        else:
            value=()
        if query!='select_by_category_null':
            cursor.execute(sql_statement[query], value)
        else:
            cursor.execute(sql_statement[query])
        statements=cursor.fetchall()
    return statements
def add_statement(s_date=None, s_amount=0, s_category=None, s_desc=None, s_type="expense"):
    #Must ensure parameters are properly formatted
    if s_date is None:
        s_date=datetime.today().strftime("%Y-%m-%d %H:%M:%S")
    if valid_date(s_date)=="invalid":
        raise ValueError("Error: Date must fit format '%Y-%m-%d %H:%M:%S' or '%Y-%m-%d'")
    if not isinstance(s_amount, int):
        #Will convert float to int elsewhere
        raise TypeError("Error: Amount must be a number")
    if s_category is not None:
        if not isinstance(s_category,int):
            raise TypeError("Error: Must enter integer for a category id number")
        elif s_category<0:
            raise ValueError("Error: must enter positive valid category id number")
    if s_type.lower() not in VALID_TYPES:
        raise ValueError("Error: Type must be 'income' or 'expense'")
    
    with get_connection() as con:
        cursor=con.cursor()
        try:
            cursor.execute(sql_statement["insert"], (s_date, s_amount, s_category, s_desc, s_type,))
            con.commit()
        except sqlite3.IntegrityError:
            raise CategoryNotFoundError(f"Error: category id {s_category} does not exist.")
def change_statement(s_id, field, value):
    field=f"{field}".lower()
    if field not in VALID_FIELDS:
        raise KeyError(f"Error: '{field}' is not a modifiable field.")
    if field == "date" and valid_date(value)=="invalid":
        raise ValueError("Error: Date must fit format '%Y-%m-%d %H:%M:%S' or '%Y-%m-%d'.")
    elif field == "amount" and not isinstance(value, int):
        raise TypeError("Error: Amount must be a number.")
    elif field == "category" and value is not None:
        if not isinstance(value, int):
            raise TypeError("Error: Category must be a number.")
        elif value<0:
            raise ValueError("Error: Category must be positive.")
    elif field == "description" and not isinstance(value, str):
        raise TypeError("Error: Description must be a string")
    elif field == "type" and value.lower() not in VALID_TYPES:
        raise ValueError("Error: Type must be 'income' or 'expense'")
    with get_connection() as con:
        try:
            cursor=con.cursor()
            loc=f"modify_{field}"   #Changes dictionary location based on field
            cursor.execute(sql_statement[loc],(value,s_id,))
            con.commit()
        except sqlite3.IntegrityError:
            raise CategoryNotFoundError(f"Error: category id {value} does not exist.")

def delete_statement(s_id):
    if not isinstance(s_id,int):
        raise TypeError("Error: Must enter valid integer as an id")
    elif s_id<0:
        raise ValueError("Error: Must enter positive number as id")
    with get_connection() as con:
        cursor=con.cursor()
        s_id=int(s_id)
        cursor.execute(sql_statement["delete"],(s_id,))
        con.commit()
        

#Testing function
def mainer():
    init_db()
    y=get_statements()
    print(f"Statements: {[tuple(row) for row in y]}") #in accordance with the row functionality
    return
    x=get_categories_name()
    print(f"Categories: {[tuple(row) for row in x]}") #in accordance with the row functionality
    #add_category("Being awesome.")
    #add_category("Energy and security")
    #add_category("The mob")
    x=get_categories_name()
    print(f"Categories: {[tuple(row) for row in x]}")
    #add_statement(s_amount=50000, s_category=2, s_desc="Willie the Wop visited my house about the gambling debt", s_type="expense")
    #change_statement(s_id=1, field="date", value="1945-4-30 16:00:00")
    y=get_statements()
    print(f"Statements: {[tuple(row) for row in y]}") #in accordance with the row functionality
if __name__=="__main__":
    #Testing
    mainer()