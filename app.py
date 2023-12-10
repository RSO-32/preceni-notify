from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from os.path import join, dirname
from database import Database
from os import environ
from models.notification import Notification
from models.users import User
import requests
from health import Health
from metrics import Metrics
import logging, graypy
from uuid import uuid4

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Logging
graylog_handler = graypy.GELFUDPHandler("logs.meteo.pileus.si", 12201)
environment = "dev" if environ.get("NOTIFY_SERVICE_DEBUG") else "prod"
graylog_handler.setFormatter(
    logging.Formatter(f"preceni-notify {environment} %(asctime)s %(levelname)s %(name)s %(message)s [{uuid4()}]")
)
app.logger.addHandler(graylog_handler)
app.logger.setLevel(logging.INFO)

dotenv_path = join(dirname(__file__), ".env")
load_dotenv(dotenv_path)

Database.connect()
app.logger.info("Connected to database")


def verify_user(user_id, token):
    app.logger.info(f"Verifying user {user_id}")
    url = environ.get("AUTH_SERVICE_URL") + "/user-by-token"
    request = requests.get(url, params={"token": token, "user_id": user_id})

    if request.status_code != 200:
        app.logger.info(f"User {user_id} not verified")
        return None

    app.logger.info(f"User {user_id} verified")

    data = request.json()
    id = data["id"]
    first_name = data["first_name"]
    last_name = data["last_name"]
    email = data["email"]
    return User(id, first_name, last_name, email)


@app.route("/notification", methods=["POST"])
def create_notification():
    app.logger.info("START: POST /notification")
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

    app.logger.info("END: POST /notification")
    return notification.to_json(), 201


@app.route("/notification", methods=["GET"])
def list_notifications():
    app.logger.info("START: GET /notification")
    notifications = Notification.get_all()

    app.logger.info("END: GET /notification")
    return jsonify([notification.to_json() for notification in notifications])


@app.route("/notify", methods=["POST"])
def notify():
    app.logger.info("START: POST /notify")
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
            json={"content": f"Price of {product_name} dropped from {previous_price} to {current_price} on {seller}!"}
        )

    app.logger.info("END: POST /notify")


@app.route("/metrics")
def metrics():
    app.logger.info("GET: Metrics")
    metrics = Metrics.get_metrics()

    response = ""
    for metric in metrics:
        response += f"{metric.name} {metric.value}\n"

    return response


@app.route("/health/live")
def health_live():
    app.logger.info("GET: Health live check")
    status, checks = Health.check_health()
    code = 200 if status == "UP" else 503

    return jsonify({"status": status, "checks": checks}), code


@app.route("/health/test/toggle", methods=["PUT"])
def health_test():
    app.logger.info("PUT: Health test toggle")
    Health.force_fail = not Health.force_fail

    return Health.checkTest()


if __name__ == "__main__":
    Metrics.init()
    app.run(
        host="0.0.0.0",
        port=environ.get("NOTIFY_SERVICE_PORT"),
        debug=environ.get("NOTIFY_SERVICE_DEBUG"),
    )
