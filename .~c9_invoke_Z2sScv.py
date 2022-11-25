import os
import sys
from bs4 import BeautifulSoup
import requests

from cs50 import SQL
from flask_session import Session
from tempfile import mkdtemp
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from functools import wraps

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///blog.db")

def login_required(f):
    """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/1.0/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return redirect("login.html")

        # Ensure password was submitted
        elif not request.form.get("password"):
            return redirect("login.html")

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username;",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["password"], request.form.get("password")):
            return redirect("login.html")

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

# LOGOUT
@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


# REGISTER
@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
        error = "REGISTER"
        # Ensure forms are filled
        if not request.form.get("username"):
            error = "Please enter a username!"
            return render_template("register.html", error=error)

        elif not request.form.get("password"):
            error = "Please enter a password!"
            return render_template("register.html", error=error)

        elif not request.form.get("verifypassword"):
            error = "Please re-enter your password!"
            return render_template("register.html", error=error)

        elif request.form.get("password") != request.form.get("verifypassword"):
            error = "Passwords do not match!"
            return render_template("register.html", error=error)

        else:
            taken_username = db.execute("SELECT username FROM users WHERE username = :username;", username=request.form.get("username"))
            listname = []
            for names in taken_username:
                listname.append(names["username"])
            if len(listname) > 0:
                error = "Username already taken!"
                return render_template("register.html", error=error)

        old_id = db.execute("SELECT id FROM users ORDER BY id;")
        values = []
        for ids in old_id:
            values.append(ids["id"])

        new_id = 0

        if len(values) > 0:
            new_id = int(values[len(values) - 1]) + 1
        else:
            new_id = int(1)


        final_id = new_id
        print(final_id, file = sys.stderr)
        new_username = request.form.get("username")
        hashed = generate_password_hash(request.form.get("password"))

        stored = [final_id, new_username, hashed]

        db.execute("INSERT INTO users (id, username, password) VALUES(?, ?, ?)", stored[:3])

        return redirect("/login")

    else:
        return render_template("register.html")

# POST

@app.route("/post", methods=["GET", "POST"])
@login_required
def post():
    if request.method == "GET":
        error = "Write a post!"
        return render_template("post.html", error = error)
    if request.method == "POST":
        title = request.form.get("title")
        body = request.form.get("post")

        print(title, file=sys.stderr)
        print(body, file=sys.stderr)

        if not title or not body:
            error = "Title/body cannot be empty!"
            return render_template("post.html", error = error)

        db.execute("INSERT INTO posts (user_id, title, post) VALUES (:id, :title, :body);", id=session["user_id"], title=title, body=body)

        return redirect("/myblog")



@app.route("/", methods=["GET", "POST"])
@login_required
def home():
    if request.method == "GET":
        getbio = db.execute("SELECT bio FROM profile WHERE user_id = :id;", id=session["user_id"])
        if not getbio:
            return render_template("home.html", bio = None)
        bio = getbio[0]["bio"]
        return render_template("home.html", bio = bio)


@app.route("/myblog", methods=["GET", "POST"])
@login_required
def myblog():
    bloginfo = db.execute("SELECT post, title, date, time FROM posts WHERE user_id = :id;", id=session["user_id"])
    length = []
    print(bloginfo[0]["post"], file=sys.stderr)
    print(len(bloginfo), file=sys.stderr)
    for i in range(len(bloginfo)):
        length.append(i)

    print(length, file=sys.stderr)
    return render_template("myblog.html", bloginfo = bloginfo, length = length)

@app.route("/edit", methods=["GET", "POST"])
@login_required
def edit():
    if request.method == "GET":
        return render_template("edit.html")
    if request.method == "POST":
        bio = request.form.get("bio")
        print(bio, file=sys.stderr)
        getcheck = db.execute("SELECT bio FROM profile WHERE user_id = :id;", id=session["user_id"])
        #check = getcheck[0]["bio"]
        if not getcheck:
            db.execute("INSERT INTO profile (user_id, bio) VALUES (:id, :bio);", id=session["user_id"], bio=bio)
            return redirect("/")
        db.execute(f"UPDATE profile SET bio = {bio} WHERE user_id = :id;", id=session["user_id"])
        return redirect("/")

# LOGIN REQUIRED        
@app.route("/recent", methods=["GET", "POST"])
@login_required
def recent():
    info = db.execute("SELECT username, title, post, date, time FROM users JOIN posts on posts.user_id = users.id ORDER BY time DESC, date DESC;")
    length = []
    for i in range(len(info)):
        length.append(i)
    return render_template("recent.html", info=info, length=length)


# NEWS    
@app.route("/news", methods=["GET", "POST"])
@login_required
def news():
    url = "http://feeds.bbci.co.uk/news/rss.xml?edition=uk"
    response = requests.get(url)
    soup = BeautifulSoup(response.content)
    items = soup.findAll('item')
    print(items, file=sys.stderr)
    return render_template("news.html", items=items)