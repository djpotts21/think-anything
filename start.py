import os
from flask import (
    Flask,
    flash,
    render_template,
    redirect,
    request,
    session,
    url_for)
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from datetime import date, datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
if os.path.exists("env.py"):
    import env

app = Flask(__name__)

app.config["MONGO_DBNAME"] = os.environ.get("MONGO_DBNAME")
app.config["MONGO_URI"] = os.environ.get("MONGO_URI")
app.secret_key = os.environ.get("SECRET_KEY")

mongo = PyMongo(app)

today = date.today().strftime("%d %B, %Y")
tommorow = datetime.now() + timedelta(1)
tommorow_formated = tommorow.strftime("%d %B, %Y")


@app.route("/")
@app.route("/home", methods=["GET", "POST"])
def home():
    background = list(mongo.db.artwork.aggregate([{"$sample": {"size": 1}}]))
    reviews = list(mongo.db.reviews.find().sort("_id", -1).limit(3))
    # goals = list(mongo.db.goals.find(
    #     {"created_by": session["user"]},
    #     {"date": today.strftime("%d %B, %Y")}).limit(3))
    goals = list(mongo.db.goals.find(
        {"created_by": "daniel", "date": today, "done": False}).limit(3))
    return render_template(
        "home.html",
        reviews=reviews,
        goals=goals,
        background=background)


@app.route("/goal-done/<goal_id>", methods=["POST"])
def goal_done(goal_id):
    mongo.db.goals.update_one(
        {"_id": ObjectId(goal_id)},
        {'$set': {"done": True}})
    flash("Goal marked as done")
    return redirect(url_for("home"))


@app.route("/goal-move-tomorrow/<goal_id>", methods=["POST"])
def goal_move_tomorrow(goal_id):
    mongo.db.goals.update_one(
        {"_id": ObjectId(goal_id)},
        {'$set': {"date": tommorow_formated}})
    flash("Goal moved to tommorow")
    return redirect(url_for("home"))


@app.route("/login", methods=["GET", "POST"])
def login():
    background = list(mongo.db.artwork.aggregate([{"$sample": {"size": 1}}]))
    if request.method == "POST":
        # check if username exists #
        existing_user = mongo.db.users.find_one(
            {"username": request.form.get("username").lower()})

        if existing_user:
            # checks if hashed password matches #
            if check_password_hash(
                    existing_user["password"], request.form.get("password")):
                session["user"] = request.form.get("username").lower()
                flash("Hi, {}".format(existing_user["full_name"].title()))
                # return redirect(url_for("profile", username=session["user"]))
                return redirect(url_for("home"))
            else:
                # invalid password #
                flash("Incorrect Username and/or Password!")
                return redirect(url_for("login"))
        else:
            # username doesn't exist #
            flash("Incorrect Username and/or Password")
            return redirect(url_for("login"))

    return render_template("login.html", background=background)


@app.route("/logout")
def logout():
    # remove session cookie for user
    flash("You have been logged out!")
    session.pop("user")
    return redirect(url_for("login"))


@app.route("/share-your-art", methods=["GET", "POST"])
def share_your_art():
    background = list(mongo.db.artwork.aggregate([{"$sample": {"size": 1}}]))
    return render_template("share-your-art.html", background=background)


if __name__ == "__main__":
    app.run(
        host=os.environ.get("IP"),
        port=int(os.environ.get("PORT")),
        debug=True
    )
