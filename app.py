from flask import Flask, render_template, request, redirect, url_for, session, flash
from contextlib import closing  # Import the closing utility
import sqlite3  # Import the sqlite3 module
from database import (
    init_db,
    get_db,
    add_user,
    get_user,
    add_score,
    get_scores,
    count_scores,
)
import questions

app = Flask(__name__)
app.secret_key = "73c89b341dd40a813a1bae5b0e08a4c1"

# Define the path to the SQLite database
DATABASE = "quiz_app.db"

# Initialize the database
init_db()


# Home page
@app.route("/")
def index():
    return render_template("index.html")


# Login page
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = get_user(username)
        if user and user["password"] == password:
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            flash("Login successful!", "success")
            if username == "admin":
                return redirect(url_for("admin"))
            else:
                return redirect(url_for("quiz"))
        else:
            flash("Invalid username or password", "error")
    return render_template("login.html")


# Registration page
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if get_user(username):
            flash("Username already exists", "error")
        else:
            add_user(username, password)
            flash("Registration successful! Please log in.", "success")
            return redirect(url_for("login"))
    return render_template("register.html")


# Quiz page with pagination
@app.route("/quiz", methods=["GET", "POST"])
def quiz():
    if "user_id" not in session:
        flash("Please log in to take the quiz", "error")
        return redirect(url_for("login"))

    total_questions = len(questions.questions)
    questions_per_page = 2  # Number of questions per page
    page = int(request.args.get("page", 1))  # Get the current page from the URL

    if request.method == "POST":
        # Store user answers in the session
        if "user_answers" not in session:
            session["user_answers"] = {}

        # Save the user's answers for the current page
        for key, value in request.form.items():
            if key.startswith("question_"):
                question_number = int(key.split("_")[1])
                session["user_answers"][str(question_number)] = value

        # Determine the next action
        if "next" in request.form:
            page += 1  # Move to the next page
        elif "previous" in request.form:
            page -= 1  # Move to the previous page
        elif "submit" in request.form:
            return redirect(url_for("results"))  # Submit the quiz

        # Redirect to the updated page
        return redirect(url_for("quiz", page=page))

    # Calculate the range of questions for the current page
    start = (page - 1) * questions_per_page
    end = start + questions_per_page
    current_questions = questions.questions[start:end]

    return render_template(
        "quiz.html",
        questions=current_questions,
        page=page,
        total_pages=(total_questions + questions_per_page - 1) // questions_per_page,
        total_questions=total_questions,
        questions_per_page=questions_per_page,
    )


# Results page
@app.route("/results")
def results():
    if "user_id" not in session:
        flash("Please log in to view your results", "error")
        return redirect(url_for("login"))

    total_questions = len(questions.questions)
    user_answers = session.get("user_answers", {})
    score = 0
    incorrect_questions = []

    for question in questions.questions:
        question_number = str(question["number"])
        user_answer = user_answers.get(question_number)

        if user_answer:
            correct_answer = question["correct_answer"]
            question_type = question.get(
                "type", "radio"
            )  # Default to "radio" if not specified

            if question_type == "checkbox":
                # For checkbox questions, user_answer is a list of selected indices
                user_answer = [int(ans) for ans in user_answer.split(",")]
                if isinstance(correct_answer, list):
                    if set(user_answer) == set(correct_answer):
                        score += 1
                    else:
                        incorrect_questions.append(question)
                else:
                    # Handle case where correct_answer is not a list (e.g., single correct answer for checkbox)
                    if user_answer == [correct_answer]:
                        score += 1
                    else:
                        incorrect_questions.append(question)
            else:
                # For radio questions, user_answer is a single value
                if isinstance(correct_answer, list):
                    if int(user_answer) in correct_answer:
                        score += 1
                    else:
                        incorrect_questions.append(question)
                else:
                    if int(user_answer) == correct_answer:
                        score += 1
                    else:
                        incorrect_questions.append(question)

    add_score(session["user_id"], score)
    session.pop("user_answers", None)  # Clear user answers from the session

    return render_template(
        "results.html",
        score=score,
        total_questions=total_questions,
        incorrect_questions=incorrect_questions,
    )


# User's previous scores with pagination
@app.route("/scores")
def scores():
    if "user_id" not in session:
        flash("Please log in to view your scores", "error")
        return redirect(url_for("login"))

    page = int(request.args.get("page", 1))  # Default to page 1
    per_page = 10  # Number of scores per page

    # Fetch scores for the current page
    user_scores = get_scores(session["user_id"], page, per_page)

    # Calculate total number of scores for the user
    total_scores = count_scores(session["user_id"])

    # Calculate total pages
    total_pages = (total_scores + per_page - 1) // per_page

    return render_template(
        "scores.html", scores=user_scores, page=page, total_pages=total_pages
    )


# Delete a score
@app.route("/delete_score/<int:score_id>", methods=["POST"])
def delete_score(score_id):
    if "user_id" not in session:
        flash("Please log in to delete scores", "error")
        return redirect(url_for("login"))

    with closing(sqlite3.connect(DATABASE)) as db:
        db.execute(
            "DELETE FROM scores WHERE id = ? AND user_id = ?",
            (score_id, session["user_id"]),
        )
        db.commit()

    flash("Score deleted successfully!", "success")
    return redirect(url_for("scores"))


# Admin page to add questions
@app.route("/admin", methods=["GET", "POST"])
def admin():
    if "user_id" not in session or session.get("username") != "admin":
        flash("You do not have permission to access this page", "error")
        return redirect(url_for("index"))

    if request.method == "POST":
        question = request.form["question"]
        options = request.form["options"].split(",")
        correct_answer = request.form["correct_answer"].split(",")
        question_type = request.form["type"]

        new_question = {
            "number": len(questions.questions) + 1,
            "question": question,
            "options": options,
            "correct_answer": [int(ans.strip()) for ans in correct_answer],
            "type": question_type,
        }

        questions.questions.append(new_question)
        flash("Question added successfully!", "success")
        return redirect(url_for("admin"))

    return render_template("admin.html")


# Logout
@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out", "success")
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)
