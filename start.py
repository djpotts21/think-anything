import os
import base64
import requests
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
from werkzeug.security import (
    generate_password_hash,
    check_password_hash)
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
    """Home page"""
    background = list(mongo.db.artwork.aggregate([{"$sample": {"size": 1}}]))
    if session.get("logged-in") == "yes":
        goals = list(mongo.db.goals.find(
            {"created_by": session["user"],
             "date": today,
             "done": "no"}).limit(3))
        return render_template(
            "home.html",
            background=background,
            goals=goals)
    else:
        reviews = list(mongo.db.reviews.find().sort("_id", -1).limit(3))
        return render_template(
            "home.html",
            reviews=reviews,
            background=background)


@app.route("/goal-done/<goal_id>", methods=["POST"])
def goal_done(goal_id):
    """Mark goal as done"""
    mongo.db.goals.update_one(
        {"_id": ObjectId(goal_id)},
        {'$set': {"done": "yes"}})
    flash("Goal marked as done")
    return redirect(url_for("home"))


@app.route("/goal-move-tomorrow/<goal_id>", methods=["POST"])
def goal_move_tomorrow(goal_id):
    """Move goal to tommorow"""
    mongo.db.goals.update_one(
        {"_id": ObjectId(goal_id)},
        {'$set': {"date": tommorow_formated}})
    flash("Goal moved to tommorow")
    return redirect(url_for("home"))


@app.route("/login", methods=["GET", "POST"])
def login():
    """Login user"""
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
                session["logged-in"] = "yes"
                mongo.db.users.update_one(
                 {"username": request.form.get("username").lower()},
                 {'$set': {"lldate": today}})
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
    """Logout user"""
    # remove session cookie for user
    session.clear()
    flash("You have been logged out!")
    return redirect(url_for("login"))


@app.route("/share-your-art", methods=["GET", "POST"])
def share_your_art():
    """Share your art"""
    if request.method == "POST":
        uploaded_file = request.files['file']
        if uploaded_file.filename != '':
            with uploaded_file.stream as image_file:
                url = "https://api.imgbb.com/1/upload"
                payload = {
                    "key": os.environ.get("IMGBB_API_KEY"),
                    "image": base64.b64encode(image_file.read()),
                }
        res = requests.post(url, payload)
        responsejson = res.json()
        artwork = {
            "image_url": responsejson["data"]["url"],
            "creator": request.form.get("creator"),
            "creator_backlink": request.form.get("creator_backlink"),
            "source": request.form.get("source"),
            "source_backlink": request.form.get("source_backlink"),
        }
        mongo.db.artwork.insert_one(artwork)
        flash("Artwork Successfully Shared!")
        return redirect(url_for("home"))
    background = list(mongo.db.artwork.aggregate([{"$sample": {"size": 1}}]))
    return render_template("share-your-art.html", background=background)


@app.route("/profile", methods=["GET", "POST"])
def profile():
    ''''Profile page'''
    displayname = mongo.db.users.find_one(
        {"username": session["user"]})["full_name"].title()
    welcomemessage = list(
        mongo.db.welcome_messages.aggregate([{"$sample": {"size": 1}}]))
    lastlogindate = mongo.db.users.find_one(
        {"username": session["user"]})["lldate"]
    profilepicture = mongo.db.users.find_one(
        {"username": session["user"]})["profile_image_url"]
    if request.method == "POST":
        print("Profile")

    return render_template(
        "profile.html",
        displayname=displayname,
        welcomemessage=welcomemessage,
        lastlogindate=lastlogindate,
        profilepicture=profilepicture)


if __name__ == "__main__":

    app.run(
        host=os.environ.get("IP"),
        port=int(os.environ.get("PORT")),
        debug=True
    )
