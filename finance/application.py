import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

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

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    stocks = db.execute("SELECT symbol, shares FROM porfolio WHERE user_id = :user_id ORDER BY symbol DESC", user_id = session["user_id"])

    if not stocks:
        return render_template("index.html", message = "No Stocks Purchased Yet")

    total = 0

    for stock in stocks:
       name = price = lookup(stock["symbol"])["name"]
       stock.update({"name": name})
       price = lookup(stock["symbol"])["price"]
       stock.update({"price": usd(price)})
       value = price * stock["shares"]
       stock.update({"value": usd(value)})
       total = total + value

    balance = db.execute("SELECT cash FROM users WHERE id = :id_user", id_user = session["user_id"])[0]["cash"]

    total = total + balance


    return render_template("index.html", stocks = stocks, balance = usd(balance), value = usd(total))

@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "GET":
        return render_template("buy.html")
    elif request.method == "POST":
        symbolInp = lookup(request.form.get("txtBuySymbol"))['symbol']
        sharesInp = request.form.get("txtShare")

        if not lookup(symbolInp):
            return render_template("buy.html", message="Enter a valid symbol")

        elif not isinstance(int(sharesInp)):
            return render_template("buy.html", message="Field must be numeric")

        elif int(sharesInp) <= 0:
           return render_template("buy.html", message="insufficient funds")

        balance = db.execute("SELECT cash FROM users where id = :user_id", user_id = session["user_id"])[0]['cash']
        totalPrice = lookup(symbolInp)['price'] * int(sharesInp);

        if totalPrice > balance:
            return apology("Insufficient funds", 403)

        db.execute("INSERT INTO transactions(user_id, type, symbol, shares, price) VALUES(:user_id, :type, :symbol, :shares, :price)",
        user_id = session['user_id'], type = "purchase", symbol = symbolInp, shares = sharesInp, price = usd(totalPrice) )

        balance = balance - totalPrice

        db.execute("UPDATE users SET cash = :balance WHERE id = :user_id", balance = balance, user_id = session["user_id"])

        porfolio = db.execute("SELECT shares FROM porfolio WHERE user_id = :user_id and symbol = :symbol", user_id = session["user_id"], symbol = symbolInp)

        if len(porfolio) == 1:

            shares = porfolio[0]["shares"] + int(sharesInp)

            db.execute("UPDATE porfolio SET shares = :shares WHERE user_id = :user_id and symbol = :symbol", shares = shares, user_id = session["user_id"], symbol = symbolInp)

        else:

            db.execute("INSERT INTO porfolio (user_id, symbol, shares) VALUES(:user_id, :symbol, :shares)", user_id = session["user_id"], symbol = symbolInp, shares = sharesInp)

        name = lookup(symbolInp)['name']

        flash(f"Purchased {sharesInp} of {name}")

        return redirect("/")



@app.route("/history")
@login_required
def history():
    transactions = db.execute("SELECT symbol, type, shares, price, date FROM transactions Where user_id = :user_id", user_id = session["user_id"])

    for trans in transactions:
         trans["symbol"]
         trans["type"]
         trans["shares"]
         trans["price"]
         trans["date"]


    return render_template("history.html", transactions = transactions)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "GET":
        return render_template("quote.html")
    else:
        quote = request.form.get("txtSymbol")

        NewQuote = lookup(quote)

        if not NewQuote:
            return render_template("quote.html", message="Must enter a valid symbol")

        NewQuote["price"] = usd(NewQuote["price"])

        return render_template("quoted.html", NewQuote = NewQuote)





@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "GET":
        return render_template("register.html")

    elif request.method == "POST":
        username = request.form.get("username")
        if not username:
            return apology("must provide username", 403)

        password = request.form.get("password")
        if not password:
            return apology("must provide password", 403)

        configPass = request.form.get("ConfPassword")

        if password != configPass:
            return apology("Password must match", 403)

        else:
            confPass = generate_password_hash(password, "sha256")

            db.execute("INSERT INTO users (username, hash) VALUES(:username, :password)", username = username, password = confPass)

            return redirect("/login")



@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""

    if request.method == "POST":
        symbolInp = request.form.get("symbol")
        sharesInp = request.form.get("shares")

        if not symbolInp:
            return render_template("sell.html", message="Must Provide a symbol")

        elif not isinstance(int(sharesInp)):
            return render_template("sell.html", message="Only numericals are accepted in these fields")

        elif int(sharesInp) <= 0:
            return render_template("sell.html", message="Must Provide a positive numerical")



        stocks = db.execute("SELECT shares FROM porfolio WHERE user_id = :user_id and symbol =:symbol", user_id = session["user_id"], symbol = symbolInp)


        price = lookup(symbolInp)["price"] * int(sharesInp)


        db.execute("INSERT INTO transactions (user_id, type, symbol, shares, price) VALUES(:user, :type, :symbol, :shares, :price)"
        ,user = session["user_id"], type = "sell", symbol = symbolInp, shares = sharesInp, price = usd(price))

        balance = db.execute("SELECT cash FROM users WHERE id = :user_id", user_id = session["user_id"])[0]['cash']

        balance = balance + price

        db.execute("UPDATE users SET cash = :balance Where id = :user_id ", balance = balance, user_id = session["user_id"])

        shares = stocks[0]["shares"] * int(sharesInp)

        if stocks[0]["shares"] > int(sharesInp):
            newShare = stocks[0]["shares"] - int(sharesInp)

            db.execute("UPDATE porfolio SET shares = :newShare WHERE user_id =:user_id", newShare = newShare, user_id = session["user_id"] )
        elif stocks[0]["shares"] == int(sharesInp):
            db.execute("DELETE FROM porfolio WHERE symbol = :symbol and user_id = :user_id", symbol = symbolInp, user_id = session["user_id"])

        elif stocks[0]["shares"] < int(sharesInp):
            return apology("Insufficient number of shares",403)

        name = lookup(symbolInp)["name"]

        flash(f"Sold {sharesInp} of {name}")

        return redirect("/")

    else:
        stocks = db.execute("SELECT symbol FROM porfolio WHERE user_id = :user_id ORDER BY symbol ASC", user_id = session["user_id"])

        return render_template("sell.html", stocks = stocks)




def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
