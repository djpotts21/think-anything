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

    water_log = mongo.db.water_log.find(
        {"created_by": session["user"],
         "date": selected_date})

    sleep_log = mongo.db.sleep_log.find(
        {"created_by": session["user"],
         "date": selected_date})

    exercise_log = mongo.db.exercise_log.find(
        {"created_by": session["user"],
         "date": selected_date})

    food_log = mongo.db.food_log.find(
        {"created_by": session["user"],
         "date": selected_date})

    brain_train_log = mongo.db.brain_train_log.find(
        {"created_by": session["user"],
         "date": selected_date})

    hygiene_log = mongo.db.hygiene_log.find(
        {"created_by": session["user"],
         "date": selected_date})

    return render_template("journal.html",
                           welcomemessage=welcomemessage,
                           user_data=user_data,
                           today=today,
                           selected_date=selected_date,
                           previous_day_formated=previous_day_formated,
                           next_day_formated=next_day_formated,
                           goals=goals,
                           objectives=objectives,
                           water_log=water_log,
                           sleep_log=sleep_log,
                           exercise_log=exercise_log,
                           food_log=food_log,
                           brain_train_log=brain_train_log,
                           hygiene_log=hygiene_log)


@app.route("/add-edit-goal", methods=["POST"])
def add_edit_goal():
    """add or edit goal"""
    if request.form.get("_id"):
        mongo.db.goals.update_one(
            {"created_by": session["user"]},
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

    selected_date = today
    if request.args.get("dateurl"):
        selected_date = request.args.get("dateurl")
    else:
        selected_date = today

    if mongo.db.water_log.find_one(
            {"created_by": session["user"],
             "date": selected_date}):
        mongo.db.water_log.update_one(
            {"created_by": session["user"],
             "date": selected_date},
            {'$set': {"water": int(request.form.get("water_log"))}})
    else:
        water_log = {
            "water": int(request.form.get("water_log")),
            "date": selected_date,
            "created_by": session["user"]
        }
        mongo.db.water_log.insert_one(water_log)
    flash("Water log updated")
    return redirect(url_for("journal", date=selected_date))


@app.route("/sleep_log", methods=["POST"])
def sleep_log_update():
    """Update sleep log"""

    selected_date = today
    if request.args.get("dateurl"):
        selected_date = request.args.get("dateurl")
    else:
        selected_date = today

    if mongo.db.sleep_log.find_one(
            {"created_by": session["user"],
             "date": selected_date}):
        mongo.db.sleep_log.update_one(
            {"created_by": session["user"],
             "date": selected_date},
            {'$set': {"sleep": int(request.form.get("sleep_log"))}})
    else:
        sleep_log = {
            "sleep": int(request.form.get("sleep_log")),
            "date": selected_date,
            "created_by": session["user"]
        }
        mongo.db.sleep_log.insert_one(sleep_log)
    flash("Sleep log updated")
    return redirect(url_for("journal", date=selected_date))


@app.route("/exercise_log", methods=["POST"])
def exercise_log_update():
    """Update Exercise log"""

    selected_date = today
    if request.args.get("dateurl"):
        selected_date = request.args.get("dateurl")
    else:
        selected_date = today

    if mongo.db.exercise_log.find_one(
            {"created_by": session["user"],
             "date": selected_date}):
        mongo.db.exercise_log.update_one(
            {"created_by": session["user"],
             "date": selected_date},
            {'$set': {"mins": int(request.form.get("exercise_log"))}})
    else:
        exercise_log = {
            "mins": int(request.form.get("exercise_log")),
            "date": selected_date,
            "created_by": session["user"]
        }
        mongo.db.exercise_log.insert_one(exercise_log)
    flash("Exercise log updated")
    return redirect(url_for("journal", date=selected_date))


@app.route("/food_log", methods=["POST"])
def food_log_update():
    """Update Food log"""

    selected_date = today
    if request.args.get("dateurl"):
        selected_date = request.args.get("dateurl")
    else:
        selected_date = today

    if mongo.db.food_log.find_one(
            {"created_by": session["user"],
             "date": selected_date}):
        mongo.db.food_log.update_one(
            {"created_by": session["user"],
             "date": selected_date},
            {'$set': {"meals": int(request.form.get("food_log"))}})
    else:
        food_log = {
            "meals": int(request.form.get("food_log")),
            "date": selected_date,
            "created_by": session["user"]
        }
        mongo.db.food_log.insert_one(food_log)
    flash("Food log updated")
    return redirect(url_for("journal", date=selected_date))


@app.route("/brain_train_log", methods=["POST"])
def brain_train_log_update():
    """Update mind exercises log"""

    selected_date = today
    if request.args.get("dateurl"):
        selected_date = request.args.get("dateurl")
    else:
        selected_date = today

    if mongo.db.brain_train_log.find_one(
            {"created_by": session["user"],
             "date": selected_date}):
        mongo.db.brain_train_log.update_one(
            {"created_by": session["user"],
             "date": selected_date},
            {'$set': {"mins": int(request.form.get("brain_train_log"))}})
    else:
        brain_train_log = {
            "mins": int(request.form.get("brain_train_log")),
            "date": selected_date,
            "created_by": session["user"]
        }
        mongo.db.brain_train_log.insert_one(brain_train_log)
    flash("Mind Exercises log updated")
    return redirect(url_for("journal", date=selected_date))


@app.route("/hygiene_log_log", methods=["POST"])
def hygiene_log_update():
    """Update mind exercises log"""

    selected_date = today
    if request.args.get("dateurl"):
        selected_date = request.args.get("dateurl")
    else:
        selected_date = today

    if mongo.db.hygiene_log.find_one(
            {"created_by": session["user"],
             "date": selected_date}):
        mongo.db.hygiene_log.update_one(
            {"created_by": session["user"],
             "date": selected_date},
            {'$set': {"done": request.form.get("hygiene")}})
    else:
        hygiene_log_log = {
            "done": request.form.get("hygiene"),
            "date": selected_date,
            "created_by": session["user"]
        }
        mongo.db.hygiene_log.insert_one(hygiene_log_log)
    flash("Hygiene log updated")
    return redirect(url_for("journal", date=selected_date))


@app.route("/social", methods=["GET"])
def social():
    """Social page"""
    messages = "None"
    users = list(mongo.db.users.find())
    current_user = mongo.db.friends.find_one(
        {"user": session["user"]})
    session_user = session["user"]
    selected_user = None
    selected_user = request.args.get("selected_user")
    if selected_user:
        sent_messages = mongo.db.messages.find(
            {"$and": [{"to": selected_user}, {"from": session_user}]})
        received_messages = mongo.db.messages.find(
            {"$and": [{"to": session_user}, {"from": selected_user}]})
        messages = list(sent_messages) + list(received_messages)
        messages.sort(key=lambda x: x["timestamp"])
    else:
        messages = "None"

    return render_template("social.html",
                           users=users,
                           current_user=current_user,
                           messages=messages,
                           selected_user=selected_user)


@app.route("/accept-friend", methods=["GET"])
def accept_friend():
    '''Accept friend request'''
    username = request.args.get("f_un") # friend's username
    sessionuser = session["user"]       # current user
    # add friend to current user's friend list
    mongo.db.friends.update_one(
                 {"user": sessionuser},
                 {"$push": {"friend_list": username}})
    flash("Accepted friend request from " + username)
    # remove from pending request list
    mongo.db.friends.update_one(
                 {"user": sessionuser},
                 {"$pull": {"pending_friends": username}})
    flash("Removed " + username + " from pending request list")
    return redirect(url_for("social", selected_user=username))



@app.route("/send-message", methods=["POST"])
def send_message():
    """Send message"""
    message = {
        "from": session["user"],
        "to": request.form.get("to"),
        "message": request.form.get("message"),
        "timestamp": datetime.now()
    }
    mongo.db.messages.insert_one(message)
    return redirect(url_for("social", selected_user=request.form.get("to")))


@app.route("/add-friend", methods=["POST"])
def add_friend():
    """Add friend"""

    username = request.form.get("username")
    if username.startswith("@"):
        username = username.replace("@", "")
    else:
        username = username

    sessionuser = session["user"]

    usermatch = mongo.db.users.find_one(
            {"username": username})

    '''Check for own user request'''
    if sessionuser == username:
        flash("You can't add yourself as a friend")
        return redirect(url_for("social"))

    '''Check for duplicate friend request'''
    if mongo.db.friends.find_one(
                    {"user": sessionuser,
                     "friend_list": [username]}):
        flash("You are already friends")
        return redirect(url_for("social"))

    if usermatch is None:
        flash("User doesn't exist " + username)
        return redirect(url_for("social"))
    else:
        if username == usermatch["username"]:
            '''Check if record exists and add friend to friend list'''
            if mongo.db.friends.find_one(
                    {"user": session["user"]}):
                mongo.db.friends.update_one(
                 {"user": session["user"]},
                 {"$push": {"friend_list": username}})
                flash("Update Record - Added friend" +
                      username + "to user inserted in user " + session["user"])
            else:
                mongo.db.friends.insert_one(
                    {"user": session["user"],
                     "friend_list": [username]})
                flash("New Record - Added friend" +
                      username + "to user inserted in user " + session["user"])

            '''Check if record exists and add friend
                to friend's pending request list'''
            if mongo.db.friends.find_one(
                    {"user": username}):
                mongo.db.friends.update_one(
                 {"user": username},
                 {"$push": {"pending_friends": sessionuser}})
                flash("Update Record - Pending request inserted for user " +
                      username)
            else:
                mongo.db.friends.insert_one(
                    {"user": username,
                     "pending_friends": [sessionuser]})
                flash("New Record - Pending request inserted in user " +
                      username)

    return redirect(url_for("social"))


if __name__ == "__main__":

    app.run(
        host=os.environ.get("IP"),
        port=int(os.environ.get("PORT")),
        debug=True
    )
