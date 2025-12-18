from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "sqlite:///./expenses.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

Base = declarative_base()

# Initialize the database and create tables
def init_db():
    with open("db/schema.sql", "r") as f:
        conn = sqlite3.connect(DB_FILE)
        conn.executescript(f.read())
        conn.commit()
        conn.close()

# Add a new user and return user_id
def add_user(name: str, email: str) -> int:
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO Users (name, email) VALUES (?, ?)", (name, email))
    conn.commit()
    user_id = cursor.lastrowid
    conn.close()
    return user_id

# Add category if not exists and return category_id
def add_category(name: str) -> int:
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO Categories (name) VALUES (?)", (name,))
    conn.commit()
    cursor.execute("SELECT category_id FROM Categories WHERE name = ?", (name,))
    category_id = cursor.fetchone()[0]
    conn.close()
    return category_id

# Add a new expense and return expense_id
def add_expense(user_id: int, description: str, amount: float, category_name: str) -> int:
    category_id = add_category(category_name)
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO Expenses (user_id, category_id, amount, description) VALUES (?, ?, ?, ?)",
        (user_id, category_id, amount, description)
    )
    conn.commit()
    expense_id = cursor.lastrowid
    conn.close()
    return expense_id

# Retrieve all expenses with category names
def get_expenses():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT e.expense_id, e.amount, e.description, c.name as category, e.created_at
        FROM Expenses e
        JOIN Categories c ON e.category_id = c.category_id
    """)
    results = cursor.fetchall()
    conn.close()
    return results
