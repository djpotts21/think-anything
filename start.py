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

# set database name and uri
app.config["MONGO_DBNAME"] = os.environ.get("MONGO_DBNAME")
app.config["MONGO_URI"] = os.environ.get("MONGO_URI")
app.secret_key = os.environ.get("SECRET_KEY")

mongo = PyMongo(app)

# set today's date
today = date.today().strftime("%d %B, %Y")
# set tommorow's date
tommorow = datetime.now() + timedelta(1)
# set tommorow's date formated
tommorow_formated = tommorow.strftime("%d %B, %Y")


@app.route("/")
@app.route("/home", methods=["GET", "POST"])
def home():
    """Home page"""
    # get random background image
    background = list(mongo.db.artwork.aggregate([{"$sample": {"size": 1}}]))
    # check if user is logged in
    if session.get("logged-in") == "yes":
        # get last 3 goals
        goals = list(mongo.db.goals.find(
            {"created_by": session["user"],
             "date": today,
             "done": "no",
             "objective": "no"}).limit(3))
        # return homepage with goals and without reviews
        return render_template(
            "home.html",
            background=background,
            goals=goals)
    else:
        # get last 3 reviews
        reviews = list(mongo.db.reviews.find({"public": "yes"}).sort("_id", -1).limit(3))
        # return homepage with reviews and without goals
        return render_template(
            "home.html",
            reviews=reviews,
            background=background)


@app.route("/goal-done/<goal_id>", methods=["POST"])
def goal_done(goal_id):
    dateurl = request.args.get("dateurl")
    # check if date is passed in url
    if dateurl:
        selected_date = dateurl
    else:
        selected_date = today
    #Mark goal as done
    mongo.db.goals.update_one(
        {"_id": ObjectId(goal_id)},
        {'$set': {"done": "yes"}})
    # flash message
    flash("Goal marked as done")
    # reutrn to journal page with parameters
    return redirect(url_for("journal", date=selected_date))


@app.route("/goal-move-tomorrow/<goal_id>", methods=["POST"])
def goal_move_tomorrow(goal_id):
    """Move goal to tommorow"""
    dateurl = request.args.get("dateurl")
    # check if date is passed in url
    if dateurl:
        selected_date = dateurl
    else:
        selected_date = today
    # set next day
    next_day = datetime.strptime(selected_date, "%d %B, %Y") + timedelta(1)
    next_day_formated = next_day.strftime("%d %B, %Y")
    # update goal date
    mongo.db.goals.update_one(
        {"_id": ObjectId(goal_id)},
        {'$set': {"date": next_day_formated}})
    # flash message
    flash("Goal moved to tommorow")
    # reutrn to journal page with parameters
    return redirect(url_for("journal", date=next_day_formated))


@app.route("/login", methods=["GET", "POST"])
def login():
    """Login user"""
    # get random background image
    background = list(mongo.db.artwork.aggregate([{"$sample": {"size": 1}}]))
    if request.method == "POST":
        # check if username exists #
        existing_user = mongo.db.users.find_one(
            {"username": request.form.get("username").lower()})
        # if user exists check password #
        if existing_user:
            # checks if hashed password matches #
            if check_password_hash(
                    existing_user["password"], request.form.get("password")):
                # set session cookie
                session["user"] = request.form.get("username").lower()
                # set session cookie
                session["logged-in"] = "yes"
                # set profile image url in session cookie
                session["profile_image_url"] = existing_user[
                    "profile_image_url"]
                # update last login date
                mongo.db.users.update_one(
                 {"username": request.form.get("username").lower()},
                 {'$set': {"lldate": today}})
                # flash message
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
    #return login page
    return render_template("login.html", background=background)


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    # get random background image
    background = list(mongo.db.artwork.aggregate([{"$sample": {"size": 1}}]))
    if request.method == "POST":
        # check if username exists #
        existing_user = mongo.db.users.find_one(
            {"username": request.form.get("username").lower()})
        # if user exists flash message and redirect to register page otherwise register user
        if existing_user:
            flash("Username already exists! Try a diffrent one.")
            return redirect(url_for("register"))
        else:
            # build user object
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
            # insert user into database
            mongo.db.users.insert_one(register)
            # set session cookie
            session["user"] = request.form.get("username").lower()
            # flash message
            flash("Registration Successful")
            # return to profile page
            return redirect(url_for("profile"))

    return render_template("register.html", background=background)


@app.route("/logout")
def logout():
    """Logout user"""
    # remove session cookie for user
    session.clear()
    # flash message
    flash("You have been logged out!")
    # return to login page
    return redirect(url_for("login"))


@app.route("/share-your-art", methods=["GET", "POST"])
def share_your_art():
    """Share your art"""
    if request.method == "POST":
        # upload image to imgbb
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
        # build artwork
        artwork = {
            "image_url": responsejson["data"]["url"],
            "creator": request.form.get("creator"),
            "creator_backlink": request.form.get("creator_backlink"),
            "source": request.form.get("source"),
            "source_backlink": request.form.get("source_backlink"),
        }
        # insert artwork
        mongo.db.artwork.insert_one(artwork)
        # flash message
        flash("Artwork Successfully Shared!")
        # return redirect(url_for("share_your_art"))
        return redirect(url_for("home"))
    # get random background image
    background = list(mongo.db.artwork.aggregate([{"$sample": {"size": 1}}]))
    # return share your art page
    return render_template("share-your-art.html", background=background)


@app.route("/profile", methods=["GET"])
def profile():
    ''''Profile page'''
    # get welcome message
    welcomemessage = list(
        mongo.db.welcome_messages.aggregate([{"$sample": {"size": 1}}]))
    # get user data
    user_data = mongo.db.users.find_one({"username": session["user"]})
    # get friends / blocked users
    friends = mongo.db.friends.find_one({"user": session["user"]})
    # set profile image url in session cookie
    session["profile_image_url"] = mongo.db.users.find_one(
        {"username": session["user"]})["profile_image_url"]
    #get review data
    review = mongo.db.reviews.find_one({"username": session["user"]})
    # return profile page with parameters
    return render_template(
        "profile.html",
        welcomemessage=welcomemessage,
        user_data=user_data,
        friends=friends,
        review=review)


@app.route("/delete_profile_photo/<user_id>", methods=["POST"])
def delete_profile_photo(user_id):
    """Delete user profile photo"""
    # delete profile photo
    mongo.db.users.update_one(
        {"_id": ObjectId(user_id)},
        {'$set': {"profile_image_url": "No Photo"}})
    # update session cookie
    session.pop("profile_image_url", None)
    # flash message
    flash("Profile photo deleted")
    # return to profile page
    return redirect(url_for("profile"))


@app.route("/upload_profile_photo/<user_id>", methods=["POST"])
def upload_profile_photo(user_id):
    """Upload Profile user profile photo"""
    # upload image to imgbb
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
    # update profile photo
    mongo.db.users.update_one(
        {"_id": ObjectId(user_id)},
        {'$set': {"profile_image_url": responsejson["data"]["url"]}})
    # flash message
    flash("Profile photo updated")
    # update session cookie
    session.pop("profile_image_url", None)
    # return to profile page
    return redirect(url_for("profile"))


@app.route("/update_email/<user_id>", methods=["POST"])
def update_email(user_id):
    """change user email"""
    # update email
    mongo.db.users.update_one(
        {"_id": ObjectId(user_id)},
        {'$set': {"email": request.form.get("email")}})
    # flash message
    flash("Email address updated")
    # return to profile page
    return redirect(url_for("profile"))


@app.route("/update_password/<user_id>", methods=["POST"])
def update_password(user_id):
    """change user password"""
    # update password
    mongo.db.users.update_one(
        {"_id": ObjectId(user_id)},
        {'$set': {"password": generate_password_hash(
            request.form.get("confpassword"))}})
    # flash message
    flash("Password updated")
    # return to profile page
    return redirect(url_for("profile"))


@app.route("/update_privacy/<user_id>", methods=["POST"])
def update_privacy(user_id):
    """change user privacy"""
    # update privacy settings
    mongo.db.users.update_one(
        {"_id": ObjectId(user_id)},
        {'$set': {
            "makefriends": request.form.get("makefriends"),
            "publicreview": request.form.get("publicreview"),
            "showprofilephoto": request.form.get("showprofilephoto"),
            }})
    if request.form.get("publicreview") != "on":
        # make all reviews private
        mongo.db.reviews.update_many(
            {"username": session["user"]},
            {'$set': {"public": "no"}})
    else:
        # make all reviews public
        mongo.db.reviews.update_many(
            {"username": session["user"]},
            {'$set': {"public": "yes"}})
        
    if request.form.get("showprofilephoto") != "on":
        # remove profile from public reviews
        mongo.db.reviews.update_many(
            {"username": session["user"]},
            {'$set': {"user_photo": ""}})
    else:
        # add profile to public reviews
        mongo.db.reviews.update_many(
            {"username": session["user"]},
            {'$set': {"user_photo": mongo.db.users.find_one(
                {"username": session["user"]})["profile_image_url"]}})
    # flash message
    flash("Privacy updated")
    # return to profile page
    return redirect(url_for("profile"))


@app.route("/delete_account/<user_id>", methods=["POST"])
def delete_account(user_id):
    # delete user account
    mongo.db.users.delete_one({"_id": ObjectId(user_id)})
    # delete user goals
    mongo.db.goals.delete_many({"created_by": session["user"]})
    # delete user water log
    mongo.db.water_log.delete_many({"created_by": session["user"]})
    # delete user sleep log
    mongo.db.sleep_log.delete_many({"created_by": session["user"]})
    # delete user exercise log
    mongo.db.exercise_log.delete_many({"created_by": session["user"]})
    # delete user food log
    mongo.db.food_log.delete_many({"created_by": session["user"]})
    # delete user mind exercises log
    mongo.db.brain_train_log.delete_many({"created_by": session["user"]})
    # delete user hygiene log
    mongo.db.hygiene_log.delete_many({"created_by": session["user"]})
    # delete user reviews
    mongo.db.reviews.delete_many({"username": session["user"]})
    # delete user messages
    mongo.db.messages.delete_many({"$or": [{"to": session["user"]}, {"from": session["user"]} ]})
    # delete user from friends list
    mongo.db.friends.delete_many({"$or": [{"user": session["user"]}, {"friend_list": session["user"]}, {"pending_friends": session["user"]}, {"blocked": session["user"]} ]})
    # delete user from friends list
    mongo.db.friends.delete_one({"user": session["user"]})

    # clear session cookie
    session.clear()

    # flash message
    flash("Account deleted")
    # return to home page
    return redirect(url_for("home"))


@app.route("/journal", methods=["GET", "POST"])
def journal():
    # get welcome message
    welcomemessage = list(
        mongo.db.welcome_messages.aggregate([{"$sample": {"size": 1}}]))
    # get user data
    user_data = mongo.db.users.find_one({"username": session["user"]})
    # get profile image url
    session["profile_image_url"] = mongo.db.users.find_one(
        {"username": session["user"]})["profile_image_url"]
    # set today's date
    selected_date = today
    # check if date is passed in url
    if request.args.get("date"):
        selected_date = request.args.get("date")
    else:
        selected_date = today
    # set previous day
    previous_day = datetime.strptime(selected_date, "%d %B, %Y") - timedelta(1)
    previous_day_formated = previous_day.strftime("%d %B, %Y")
    # set next day
    next_day = datetime.strptime(selected_date, "%d %B, %Y") + timedelta(1)
    next_day_formated = next_day.strftime("%d %B, %Y")
    # get objectives
    objectives = list(mongo.db.goals.find(
        {"created_by": session["user"],
         "date": selected_date,
         "objective": "yes"}))
    # get goals
    goals = list(mongo.db.goals.find(
        {"created_by": session["user"],
         "date": selected_date,
         "objective": "no"}))
    # get water log
    water_log = mongo.db.water_log.find(
        {"created_by": session["user"],
         "date": selected_date})
    # get sleep log
    sleep_log = mongo.db.sleep_log.find(
        {"created_by": session["user"],
         "date": selected_date})
    # get exercise log
    exercise_log = mongo.db.exercise_log.find(
        {"created_by": session["user"],
         "date": selected_date})
    # get food log
    food_log = mongo.db.food_log.find(
        {"created_by": session["user"],
         "date": selected_date})
    # get mind exercises log
    brain_train_log = mongo.db.brain_train_log.find(
        {"created_by": session["user"],
         "date": selected_date})
    # get hygiene log
    hygiene_log = mongo.db.hygiene_log.find(
        {"created_by": session["user"],
         "date": selected_date})
    # return journal page with parameters
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
    # check if goal exists
    if request.form.get("_id"):
        # update goal
        mongo.db.goals.update_one(
            {"created_by": session["user"]},
            {'$set': {"description": request.form.get("description"),
                      "title": request.form.get("title")}})
        # flash message
        flash("Goal Updated")
    else:
        # build goal
        goal = {
            "title": request.form.get("title"),
            "date": request.form.get("date"),
            "created_by": session["user"],
            "done": "no",
            "objective": request.form.get("objective"),
            "description": request.form.get("description")
        }
        # insert goal
        mongo.db.goals.insert_one(goal)
        # flash message
        flash("Goal Set")
    # return to journal page with parameters
    return redirect(url_for("journal", date=request.form.get("url_date")))


@app.route("/water_log", methods=["POST"])
def water_log_update():
    """Update water log"""
    selected_date = today
    # check if date is passed in url
    if request.args.get("dateurl"):
        selected_date = request.args.get("dateurl")
    else:
        selected_date = today
    # check if water log exists
    if mongo.db.water_log.find_one(
            {"created_by": session["user"],
             "date": selected_date}):
        # update water log data if exists
        mongo.db.water_log.update_one(
            {"created_by": session["user"],
             "date": selected_date},
            {'$set': {"water": int(request.form.get("water_log"))}})
    else:
        # build water log data
        water_log = {
            "water": int(request.form.get("water_log")),
            "date": selected_date,
            "created_by": session["user"]
        }
        # insert water log data
        mongo.db.water_log.insert_one(water_log)
    # flash message
    flash("Water log updated")
    # return to journal page with parameters
    return redirect(url_for("journal", date=selected_date))


@app.route("/sleep_log", methods=["POST"])
def sleep_log_update():
    """Update sleep log"""
    selected_date = today
    # check if date is passed in url
    if request.args.get("dateurl"):
        selected_date = request.args.get("dateurl")
    else:
        selected_date = today
    # check if sleep log exists
    if mongo.db.sleep_log.find_one(
            {"created_by": session["user"],
             "date": selected_date}):
        # update sleep log data if exists
        mongo.db.sleep_log.update_one(
            {"created_by": session["user"],
             "date": selected_date},
            {'$set': {"sleep": int(request.form.get("sleep_log"))}})
    else:
        # build sleep log data
        sleep_log = {
            "sleep": int(request.form.get("sleep_log")),
            "date": selected_date,
            "created_by": session["user"]
        }
        # insert sleep log data
        mongo.db.sleep_log.insert_one(sleep_log)
    # flash message
    flash("Sleep log updated")
    # return to journal page with parameters
    return redirect(url_for("journal", date=selected_date))


@app.route("/exercise_log", methods=["POST"])
def exercise_log_update():
    """Update Exercise log"""
    selected_date = today
    # check if date is passed in url
    if request.args.get("dateurl"):
        selected_date = request.args.get("dateurl")
    else:
        selected_date = today
    # check if exercise log exists
    if mongo.db.exercise_log.find_one(
            {"created_by": session["user"],
             "date": selected_date}):
        # update exercise log data if exists
        mongo.db.exercise_log.update_one(
            {"created_by": session["user"],
             "date": selected_date},
            {'$set': {"mins": int(request.form.get("exercise_log"))}})
    else:
        # build exercise log data
        exercise_log = {
            "mins": int(request.form.get("exercise_log")),
            "date": selected_date,
            "created_by": session["user"]
        }
        # insert exercise log data
        mongo.db.exercise_log.insert_one(exercise_log)
    # flash message
    flash("Exercise log updated")
    # return to journal page with parameters
    return redirect(url_for("journal", date=selected_date))


@app.route("/food_log", methods=["POST"])
def food_log_update():
    """Update Food log"""
    selected_date = today
    # check if date is passed in url
    if request.args.get("dateurl"):
        selected_date = request.args.get("dateurl")
    else:
        selected_date = today
    # check if food log exists
    if mongo.db.food_log.find_one(
            {"created_by": session["user"],
             "date": selected_date}):
        # update food log data if exists
        mongo.db.food_log.update_one(
            {"created_by": session["user"],
             "date": selected_date},
            {'$set': {"meals": int(request.form.get("food_log"))}})
    else:
        # build food log data
        food_log = {
            "meals": int(request.form.get("food_log")),
            "date": selected_date,
            "created_by": session["user"]
        }
        # insert food log data
        mongo.db.food_log.insert_one(food_log)
    # flash message
    flash("Food log updated")
    # return to journal page with parameters
    return redirect(url_for("journal", date=selected_date))


@app.route("/brain_train_log", methods=["POST"])
def brain_train_log_update():
    """Update mind exercises log"""
    selected_date = today
    # check if date is passed in url
    if request.args.get("dateurl"):
        selected_date = request.args.get("dateurl")
    else:
        selected_date = today
    # check if mind exercises log exists
    if mongo.db.brain_train_log.find_one(
            {"created_by": session["user"],
             "date": selected_date}):
        # update mind exercises log data if exists
        mongo.db.brain_train_log.update_one(
            {"created_by": session["user"],
             "date": selected_date},
            {'$set': {"mins": int(request.form.get("brain_train_log"))}})
    else:
        # build mind exercises log data
        brain_train_log = {
            "mins": int(request.form.get("brain_train_log")),
            "date": selected_date,
            "created_by": session["user"]
        }
        # insert mind exercises log data
        mongo.db.brain_train_log.insert_one(brain_train_log)
    # flash message
    flash("Mind Exercises log updated")
    # return to journal page with parameters
    return redirect(url_for("journal", date=selected_date))


@app.route("/hygiene_log_log", methods=["POST"])
def hygiene_log_update():
    """Update mind exercises log"""
    selected_date = today
    # check if date is passed in url
    if request.args.get("dateurl"):
        selected_date = request.args.get("dateurl")
    else:
        selected_date = today
    # check if hygiene log exists
    if mongo.db.hygiene_log.find_one(
            {"created_by": session["user"],
             "date": selected_date}):
        # update hygiene log data if exists
        mongo.db.hygiene_log.update_one(
            {"created_by": session["user"],
             "date": selected_date},
            {'$set': {"done": request.form.get("hygiene")}})
    else:
        # build hygiene log data
        hygiene_log_log = {
            "done": request.form.get("hygiene"),
            "date": selected_date,
            "created_by": session["user"]
        }
        # insert hygiene log data
        mongo.db.hygiene_log.insert_one(hygiene_log_log)
    # flash message
    flash("Hygiene log updated")
    # return to journal page with parameters
    return redirect(url_for("journal", date=selected_date))


@app.route("/social", methods=["GET"])
def social():
    """Social page"""
    # get all users
    users = list(mongo.db.users.find())
    # get current user's friends
    current_user = mongo.db.friends.find_one(
        {"user": session["user"]})
    # get session user
    session_user = session["user"]
    selected_user = None
    selected_user = request.args.get("selected_user")
    # get messages to detect new messages for session user
    message_alert = list(mongo.db.messages.find(
            {"$or": [{"to": session_user}, {"from": session_user}]}))
    # get messages for selected user
    messages = "None"
    if selected_user:
        sent_messages = mongo.db.messages.find(
            {"$and": [{"to": selected_user}, {"from": session_user}]})
        received_messages = mongo.db.messages.find(
            {"$and": [{"to": session_user}, {"from": selected_user}]})
        messages = list(sent_messages) + list(received_messages)
        messages.sort(key=lambda x: x["timestamp"])
        # mark message as read for session user
        mongo.db.messages.update_many(
            {"$and": [{"to": session_user}, {"from": selected_user}]},
            {'$set': {"read": "yes"}})
    else:
        messages = "None"
    # return social page with parameters
    return render_template("social.html",
                           users=users,
                           current_user=current_user,
                           messages=messages,
                           selected_user=selected_user,
                           message_alert=message_alert)


@app.route("/accept-friend", methods=["GET"])
def accept_friend():
    '''Accept friend request'''
    # friend's username
    username = request.args.get("f_un")
    # current user 
    sessionuser = session["user"]       
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


@app.route("/decline-friend", methods=["GET"])
def decline_friend(): 
    '''Decline friend request'''
    # friend's username
    username = request.args.get("f_un") 
    # current user
    sessionuser = session["user"]       
    # remove from pending request list
    mongo.db.friends.update_one(
                 {"user": sessionuser},
                 {"$pull": {"pending_friends": username}})
    flash("Removed " + username + " from pending request list")

    return redirect(url_for("social"))


@app.route("/block-friend", methods=["GET"])
def block_friend():
    '''Block friend'''
    # friend's username from url
    username = request.args.get("f_un")
    # current user
    sessionuser = session["user"]
    # remove from pending request list
    mongo.db.friends.update_one(
                 {"user": sessionuser},
                 {"$pull": {"pending_friends": username}})
    flash("Removed " + username + " from pending request list")
    # remove from friend list
    mongo.db.friends.update_one(
                 {"user": sessionuser},
                 {"$pull": {"friend_list": username}})
    flash("Removed " + username + " from friend list")
    # remove from friend's friend list
    mongo.db.friends.update_one(
                 {"user": username},
                 {"$pull": {"friend_list": sessionuser}})
    # remove from friend's pending list
    mongo.db.friends.update_one(
                 {"user": username},
                 {"$pull": {"pending_friends": sessionuser}})
    # add to blocked list
    mongo.db.friends.update_one(
                 {"user": sessionuser},
                 {"$push": {"blocked": username}})
    flash("Added " + username + " to blocked list")
    return redirect(url_for("social"))



@app.route("/send-message", methods=["POST"])
def send_message():
    """Send message"""
    # build message data
    message = {
        "from": session["user"],
        "to": request.form.get("to"),
        "message": request.form.get("message"),
        "timestamp": datetime.now()
    }
    # insert message
    mongo.db.messages.insert_one(message)
    # redirect to social page with selected user
    return redirect(url_for("social", selected_user=request.form.get("to")))


@app.route("/add-friend", methods=["POST"])
def add_friend():
    """Add friend"""
    # get username from form
    username = request.form.get("username")
    # remove @ from username if present
    if username.startswith("@"):
        username = username.replace("@", "")
    else:
        username = username
    # get session user
    sessionuser = session["user"]
    # check if username exists
    usermatch = mongo.db.users.find_one(
            {"username": username})
    # check if username is session user
    if sessionuser == username:
        flash("You can't add yourself as a friend")
        return redirect(url_for("social"))
    # check if user is blocked by the session user
    if mongo.db.friends.find_one(
                    {"user": sessionuser,
                     "blocked": [username]}):
        flash("You have blocked this user")
        return redirect(url_for("social")) 
    # check if user is blocked by the friend request receiver
    if mongo.db.friends.find_one(
                    {"user": username,
                     "blocked": [sessionuser]}):
        flash("Sorry, you can not contact this user")
        return redirect(url_for("social"))
    # check if user is already in pending request list
    if mongo.db.friends.find_one(
                    {"user": sessionuser,
                     "friend_list": [username]}):
        flash("You are already friends")
        return redirect(url_for("social"))
    # check if username exists in database and add friend
    if usermatch is None:
        flash("User doesn't exist " + username)
        return redirect(url_for("social"))
    else:
        if username == usermatch["username"]:
            #Check if record exists and add friend to friend list
            if mongo.db.friends.find_one(
                    {"user": session["user"]}):
                mongo.db.friends.update_one(
                 {"user": session["user"]},
                 {"$push": {"friend_list": username}})
                flash("Update Record - Added friend" +
                      username + "to user inserted in user " + session["user"])
            else:
                # insert friend list
                mongo.db.friends.insert_one(
                    {"user": session["user"],
                     "friend_list": [username]})
                flash("New Record - Added friend" +
                      username + "to user inserted in user " + session["user"])
            #Check if record exists and add friend to friend's pending request list
            if mongo.db.friends.find_one(
                    {"user": username}):
                mongo.db.friends.update_one(
                 {"user": username},
                 {"$push": {"pending_friends": sessionuser}})
                flash("Update Record - Pending request inserted for user " +
                      username)
            else:
                # insert friend's pending request list
                mongo.db.friends.insert_one(
                    {"user": username,
                     "pending_friends": [sessionuser]})
                flash("New Record - Pending request inserted in user " +
                      username)
    # redirect to social page
    return redirect(url_for("social"))

# unblock friend
@app.route("/unblock-friend", methods=["POST"])
def unblock_friend():
    """Unblock friend"""
    # get username from form
    username = request.form.get("blockeduser")
    # get session user
    sessionuser = session["user"]
    # remove from blocked list
    mongo.db.friends.update_one(
                 {"user": sessionuser},
                 {"$pull": {"blocked": username}})
    flash("Removed " + username + " from blocked list")
    return redirect(url_for("social"))


# new or update review 
@app.route("/add-edit-review", methods=["POST"])
def add_edit_review():
    """add or edit review"""
    # set stars value
    if request.form.get("stars") == "":
        stars = 0
    else:
        stars = int(request.form.get("stars"))

    # check if review exists
    if request.form.get("_id"):
        # update review
        mongo.db.reviews.update_one(
            {"_id": ObjectId(request.form.get("_id"))},
            {'$set': {"description": request.form.get("review"),
                      "name": request.form.get("name").title(),
                      "stars": stars,
                      "user_photo" : request.form.get("user-photo"),
                      "public" : request.form.get("publicreview"),
                      "username" : session["user"],
                      }})
        # flash message
        flash("Review Updated  - Thank you!")
    else:
        # build review
        review = {
            "description": request.form.get("review"),
            "name": request.form.get("name").title(),
            "stars": stars,
            "user_photo" : request.form.get("user-photo"),
            "public" : request.form.get("publicreview"),
            "username" : session["user"],
        }
        # insert review
        mongo.db.reviews.insert_one(review)
        # flash message
        flash("Review Added - Thank you!")
    # return to home page
    return redirect(url_for("profile"))


# about page
@app.route("/about", methods=["GET"])
def about():
    """About page"""
    # get random background image
    image = list(mongo.db.artwork.aggregate([{"$sample": {"size": 1}}]))
    # return about page
    return render_template("about.html", image=image)


# contact page
@app.route("/contact", methods=["GET", "POST"])
def contact():
    """Contact page"""
    if request.method == "POST":
        # build message data
        message = {
            "from": session["user"],
            "message": request.form.get("message"),
            "timestamp": datetime.now(),
            "to": "admin"
        }
        # insert message
        mongo.db.messages.insert_one(message)
        # flash message
        flash("Message Sent")
        # return to contact page
        return redirect(url_for("contact"))
    
    # get random background image
    image = list(mongo.db.artwork.aggregate([{"$sample": {"size": 1}}]))
    # check if user is logged in
    if session.get("logged-in") == "yes":
        # get user data
        user_data = mongo.db.users.find_one({"username": session["user"]})
        # get profile image url
        session["profile_image_url"] = mongo.db.users.find_one(
            {"username": session["user"]})["profile_image_url"]
        # return contact page with parameters
        return render_template("contact.html",
                               image=image,
                               user_data=user_data)
    else:
        # return contact page
        return render_template("contact.html", image=image)

# Bootup App Params
if __name__ == "__main__":

    app.run(
        host=os.environ.get("IP"),
        port=int(os.environ.get("PORT")),
        debug=True
    )
