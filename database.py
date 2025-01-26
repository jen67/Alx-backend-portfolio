import json
import sqlite3
from contextlib import closing

DATABASE = "quiz_app.db"


def init_db():
    with closing(sqlite3.connect(DATABASE)) as db:
        with open("schema.sql", "r") as f:
            db.executescript(f.read())
        db.commit()


def get_db():
    return sqlite3.connect(DATABASE)


def add_user(username, password):
    with closing(sqlite3.connect(DATABASE)) as db:
        db.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)", (username, password)
        )
        db.commit()


def get_user(username):
    with closing(sqlite3.connect(DATABASE)) as db:
        db.row_factory = sqlite3.Row  # Convert rows to dictionaries
        cursor = db.execute("SELECT * FROM users WHERE username = ?", (username,))
        return cursor.fetchone()


def add_score(user_id, score):
    with closing(sqlite3.connect(DATABASE)) as db:
        db.execute(
            "INSERT INTO scores (user_id, score) VALUES (?, ?)", (user_id, score)
        )
        db.commit()


def get_scores(user_id, page=1, per_page=10):
    with closing(sqlite3.connect(DATABASE)) as db:
        db.row_factory = sqlite3.Row  # Convert rows to dictionaries
        offset = (page - 1) * per_page
        cursor = db.execute(
            "SELECT * FROM scores WHERE user_id = ? ORDER BY id DESC LIMIT ? OFFSET ?",
            (user_id, per_page, offset),
        )
        return cursor.fetchall()


def count_scores(user_id):
    with closing(sqlite3.connect(DATABASE)) as db:
        cursor = db.execute("SELECT COUNT(*) FROM scores WHERE user_id = ?", (user_id,))
        return cursor.fetchone()[0]
    
    def add_question(number, question, options, correct_answer, question_type):
        with closing(sqlite3.connect(DATABASE)) as db:
            db.execute(
                """INSERT INTO questions 
                (number, question, options, correct_answer, type) 
                VALUES (?, ?, ?, ?, ?)""",
                (
                    number,
                    question,
                    json.dumps(options),  # Store options as JSON array
                    json.dumps(correct_answer),  # Store answers as JSON array
                    question_type
                )
            )
            db.commit()

def get_questions():
    with closing(sqlite3.connect(DATABASE)) as db:
        db.row_factory = sqlite3.Row
        cursor = db.execute("SELECT * FROM questions ORDER BY number")
        questions = []
        for row in cursor.fetchall():
            questions.append({
                "number": row["number"],
                "question": row["question"],
                "options": json.loads(row["options"]),  # Convert JSON to list
                "correct_answer": json.loads(row["correct_answer"]),  # Convert JSON to list/int
                "type": row["type"]
            })
        return questions
