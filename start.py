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
             "done": "no",
             "objective": "no"}).limit(3))
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
    dateurl = request.args.get("dateurl")
    if dateurl:
        selected_date = dateurl
    else:
        selected_date = today
    """Mark goal as done"""
    mongo.db.goals.update_one(
        {"_id": ObjectId(goal_id)},
        {'$set': {"done": "yes"}})
    flash("Goal marked as done")
    return redirect(url_for("journal", date=selected_date))


@app.route("/goal-move-tomorrow/<goal_id>", methods=["POST"])
def goal_move_tomorrow(goal_id):
    """Move goal to tommorow"""
    dateurl = request.args.get("dateurl")

    if dateurl:
        selected_date = dateurl
    else:
        selected_date = today

    next_day = datetime.strptime(selected_date, "%d %B, %Y") + timedelta(1)
    next_day_formated = next_day.strftime("%d %B, %Y")

    mongo.db.goals.update_one(
        {"_id": ObjectId(goal_id)},
        {'$set': {"date": next_day_formated}})
    flash("Goal moved to tommorow")
    return redirect(url_for("journal", date=next_day_formated))


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
                session["profile_image_url"] = existing_user[
                    "profile_image_url"]
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


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    background = list(mongo.db.artwork.aggregate([{"$sample": {"size": 1}}]))
    if request.method == "POST":
        # check if username exists #
        existing_user = mongo.db.users.find_one(
            {"username": request.form.get("username").lower()})

        if existing_user:
            flash("Username already exists! Try a diffrent one.")
            return redirect(url_for("register"))

        register = {
            "username": request.form.get("username").lower(),
            "full_name": request.form.get("full_name"),
            "password": generate_password_hash(request.form.get("password")),
            "lldate": today,
            "profile_image_url": "No Photo",
            "email": request.form.get("email"),
            "makefriends": "on",
            "publicreview": "on",
            "showprofilephoto": "on",
            "water": 0
        }

        mongo.db.users.insert_one(register)

        # put the new user into 'session cookie
        session["user"] = request.form.get("username").lower()
        flash("Registration Successful")
        return redirect(url_for("profile"))

    return render_template("register.html", background=background)


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


@app.route("/profile", methods=["GET"])
def profile():
    ''''Profile page'''
    welcomemessage = list(
        mongo.db.welcome_messages.aggregate([{"$sample": {"size": 1}}]))
    user_data = mongo.db.users.find_one({"username": session["user"]})
    session["profile_image_url"] = mongo.db.users.find_one(
        {"username": session["user"]})["profile_image_url"]

    return render_template(
        "profile.html",
        welcomemessage=welcomemessage, user_data=user_data)


@app.route("/delete_profile_photo/<user_id>", methods=["POST"])
def delete_profile_photo(user_id):
    """Delete user profile photo"""
    mongo.db.users.update_one(
        {"_id": ObjectId(user_id)},
        {'$set': {"profile_image_url": "No Photo"}})
    session.pop("profile_image_url", None)
    flash("Profile photo deleted")
    return redirect(url_for("profile"))


@app.route("/upload_profile_photo/<user_id>", methods=["POST"])
def upload_profile_photo(user_id):
    """Upload Profile user profile photo"""
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
    mongo.db.users.update_one(
        {"_id": ObjectId(user_id)},
        {'$set': {"profile_image_url": responsejson["data"]["url"]}})
    flash("Profile photo updated")
    session.pop("profile_image_url", None)
    return redirect(url_for("profile"))


@app.route("/update_email/<user_id>", methods=["POST"])
def update_email(user_id):
    """change user email"""
    mongo.db.users.update_one(
        {"_id": ObjectId(user_id)},
        {'$set': {"email": request.form.get("email")}})
    flash("Email address updated")
    return redirect(url_for("profile"))


@app.route("/update_password/<user_id>", methods=["POST"])
def update_password(user_id):
    """change user password"""
    mongo.db.users.update_one(
        {"_id": ObjectId(user_id)},
        {'$set': {"password": generate_password_hash(
            request.form.get("confpassword"))}})
    flash("Password updated")
    return redirect(url_for("profile"))


@app.route("/update_privacy/<user_id>", methods=["POST"])
def update_privacy(user_id):
    """change user privacy"""
    mongo.db.users.update_one(
        {"_id": ObjectId(user_id)},
        {'$set': {
            "makefriends": request.form.get("makefriends"),
            "publicreview": request.form.get("publicreview"),
            "showprofilephoto": request.form.get("showprofilephoto"),
            }})
    flash("Privacy updated")
    return redirect(url_for("profile"))


@app.route("/delete_account/<user_id>", methods=["POST"])
def delete_account(user_id):
    mongo.db.users.delete_one({"_id": ObjectId(user_id)})
    session.clear()
    flash("Account deleted")
    return redirect(url_for("home"))


@app.route("/journal", methods=["GET", "POST"])
def journal():
    welcomemessage = list(
        mongo.db.welcome_messages.aggregate([{"$sample": {"size": 1}}]))
    user_data = mongo.db.users.find_one({"username": session["user"]})
    session["profile_image_url"] = mongo.db.users.find_one(
        {"username": session["user"]})["profile_image_url"]

    selected_date = today
    if request.args.get("date"):
        selected_date = request.args.get("date")
    else:
        selected_date = today

    previous_day = datetime.strptime(selected_date, "%d %B, %Y") - timedelta(1)
    previous_day_formated = previous_day.strftime("%d %B, %Y")

    next_day = datetime.strptime(selected_date, "%d %B, %Y") + timedelta(1)
    next_day_formated = next_day.strftime("%d %B, %Y")

    objectives = list(mongo.db.goals.find(
        {"created_by": session["user"],
         "date": selected_date,
         "objective": "yes"}))

    goals = list(mongo.db.goals.find(
        {"created_by": session["user"],
         "date": selected_date,
         "objective": "no"}))

    return render_template("journal.html",
                           welcomemessage=welcomemessage,
                           user_data=user_data,
                           today=today,
                           selected_date=selected_date,
                           previous_day_formated=previous_day_formated,
                           next_day_formated=next_day_formated,
                           goals=goals,
                           objectives=objectives)


@app.route("/add-edit-goal", methods=["POST"])
def add_edit_goal():
    """add or edit goal"""
    if request.form.get("_id"):
        mongo.db.goals.update_one(
            {"_id": ObjectId(request.form.get("_id"))},
            {'$set': {"description": request.form.get("description"),
                      "title": request.form.get("title")}})
        flash("Goal Updated")
    else:
        goal = {
            "title": request.form.get("title"),
            "date": request.form.get("date"),
            "created_by": session["user"],
            "done": "no",
            "objective": request.form.get("objective"),
            "description": request.form.get("description")
        }
        mongo.db.goals.insert_one(goal)
        flash("Goal Set")

    return redirect(url_for("journal", date=request.form.get("url_date")))


@app.route("/water_log", methods=["POST"])
def water_log_update():
    """Update water log"""
    mongo.db.users.update_one(
        {"_id": ObjectId(request.args.get("user"))},
        {'$set': {"water": int(request.form.get("water_log"))}})
 
    selected_date = today
    if request.args.get("date"):
        selected_date = request.args.get("date")
    else:
        selected_date = today

    return redirect(url_for("journal", selected_date=selected_date))


if __name__ == "__main__":

    app.run(
        host=os.environ.get("IP"),
        port=int(os.environ.get("PORT")),
        debug=True
    )
