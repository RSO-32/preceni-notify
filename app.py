from flask import Flask, request
from flask_cors import CORS
from dotenv import load_dotenv
from os.path import join, dirname
import logging
import sys
from database import Database
from os import environ
from models.notification import Notification
from models.users import User
import requests

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

dotenv_path = join(dirname(__file__), ".env")
load_dotenv(dotenv_path)

Database.connect()


def verify_user(user_id, token):
    url = environ.get("AUTH_SERVICE_URL") + "/user-by-token"
    request = requests.get(url, params={"token": token, "user_id": user_id})

    if request.status_code != 200:
        return None

    data = request.json()
    id = data["id"]
    first_name = data["first_name"]
    last_name = data["last_name"]
    email = data["email"]
    return User(id, first_name, last_name, email)


@app.route("/notifications", methods=["POST"])
def notifications():
    data = request.get_json()

    user_id = data["user_id"]
    token = data["token"]
    product_id = data["product_id"]
    price = data["price"]

    user = verify_user(user_id, token)

    if user is None:
        return {"message": "Unauthorized"}, 401

    notification = Notification.create(user.id, product_id, price)

    if notification is None:
        return {"message": f"Notification for product {product_id} already exists"}, 409

    return notification.to_json(), 201


@app.route("/notify", methods=["POST"])
def notify():
    data = request.get_json()
    product_id = data["product_id"]
    product_name = data["product_name"]
    current_price = data["current_price"]
    previous_price = data["previous_price"]
    seller = data["seller"]

    notifications = Notification.find(product_id, current_price)

    for notification in notifications:
        requests.post(
            notification.discord_webhook,
            json={
                "content": f"Price of {product_name} dropped from {previous_price} to {current_price} on {seller}!",
            },
        )


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=environ.get("NOTIFY_SERVICE_PORT"),
        debug=environ.get("NOTIFY_SERVICE_DEBUG"),
    )
