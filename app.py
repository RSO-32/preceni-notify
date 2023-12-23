from flask import request, jsonify
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
from flask_openapi3 import OpenAPI, Info, Tag
from pydantic import BaseModel

info = Info(title="Preceni notify", version="1.0.0", description="Preceni notify API")
app = OpenAPI(__name__, info=info)
CORS(app)  # Enable CORS for all routes

# Logging
graylog_handler = graypy.GELFUDPHandler("logs.meteo.pileus.si", 12201)
environment = "dev" if environ.get("NOTIFY_SERVICE_DEBUG") else "prod"
graylog_handler.setFormatter(
    logging.Formatter(f"preceni-notify {environment} %(asctime)s %(levelname)s %(name)s %(message)s")
)
app.logger.addHandler(graylog_handler)
app.logger.setLevel(logging.INFO)

dotenv_path = join(dirname(__file__), ".env")
load_dotenv(dotenv_path)

Database.connect()
app.logger.info("Connected to database")

notify_tag = Tag(name="notify", description="Notifications")
health_tag = Tag(name="health", description="Health and metrics")


class NotificationResponse(BaseModel):
    id: int
    user_id: int
    product_id: int
    price: float


class NotificationsResponse(BaseModel):
    notifications: list[NotificationResponse]


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


@app.post(
    "/notify/notifications", tags=[notify_tag], summary="Create notification", responses={201: NotificationResponse}
)
def create_notification():
    uuid = uuid4()
    app.logger.info(f"START: POST /notification [{uuid}]")
    data = request.get_json()

    user_id = data["user_id"]
    token = data["token"]
    product_id = data["product_id"]
    price = data["price"]
    discord_webhook = data["discord_webhook"]

    user = verify_user(user_id, token)

    if user is None:
        app.logger.info("user is not verified")
        app.logger.info(f"END: POST /notification [{uuid}]")
        return {"message": "Unauthorized"}, 401

    notification = Notification.create(user.id, product_id, price, discord_webhook)

    if notification is None:
        app.logger.info(f"Notification for product {product_id} already exists")
        app.logger.info(f"END: POST /notification [{uuid}]")
        return {"message": f"Notification for product {product_id} already exists"}, 409

    app.logger.info(f"Notification for product {product_id} created")
    app.logger.info(f"END: POST /notification [{uuid}]")
    return notification.to_json(), 201


@app.get(
    "/notify/notifications", tags=[notify_tag], summary="Get all notifications", responses={200: NotificationsResponse}
)
def list_notifications():
    uuid = uuid4()
    app.logger.info(f"START: GET /notification [{uuid}]")
    notifications = Notification.get_all()

    app.logger.info(f"END: GET /notification [{uuid}]")
    return jsonify([notification.to_json() for notification in notifications])


@app.post("/notify/notify", tags=[notify_tag], summary="Notify users")
def notify():
    uuid = uuid4()
    app.logger.info(f"START: POST /notify [{uuid}]")
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
            json={"content": f"Price of {product_name} dropped from {previous_price} € to {current_price} € on {seller}!"},
        )

    app.logger.info(f"END: POST /notify [{uuid}]")

    return jsonify({"message": "Notifications sent"})


@app.get("/notify/metrics", tags=[health_tag], summary="Get metrics")
def metrics():
    app.logger.info("GET: Metrics")
    metrics = Metrics.get_metrics()

    response = ""
    for metric in metrics:
        response += f"{metric.name} {metric.value}\n"

    return response


@app.get("/notify/health/live", tags=[health_tag], summary="Health live check")
def health_live():
    app.logger.info("GET: Health live check")
    status, checks = Health.check_health()
    code = 200 if status == "UP" else 503

    return jsonify({"status": status, "checks": checks}), code


@app.put("/notify/health/test/toggle", tags=[health_tag], summary="Health test toggle")
def health_test():
    app.logger.info("PUT: Health test toggle")
    Health.force_fail = not Health.force_fail

    return Health.checkTest()


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=environ.get("NOTIFY_SERVICE_PORT"),
        debug=environ.get("NOTIFY_SERVICE_DEBUG"),
    )
