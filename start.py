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

    reviews = list(mongo.db.reviews.find().sort("_id", -1).limit(3))
    # goals = list(mongo.db.goals.find(
    #     {"created_by": session["user"]},
    #     {"date": today.strftime("%d %B, %Y")}).limit(3))
    goals = list(mongo.db.goals.find(
        {"created_by": "daniel", "date": today, "done": False}).limit(3))
    return render_template(
        "home.html",
        reviews=reviews,
        goals=goals)


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


if __name__ == "__main__":
    app.run(
        host=os.environ.get("IP"),
        port=int(os.environ.get("PORT")),
        debug=True
    )
