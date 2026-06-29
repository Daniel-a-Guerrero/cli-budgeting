"""
Entry point. Initializes the database, then starts the interactive CLI.
Run this file directly: `python main.py`
"""
import db
import cli
import random

if __name__ == "__main__":
    db.init_db()
    cli.main_menu()