from config import Config
import logging
import sys
from dataclasses import dataclass

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)


@dataclass
class Notification:
    id: int
    user_id: int
    product_id: int
    price: float

    @staticmethod
    def get(id):
        cursor = Config.conn.cursor()
        query = """
        SELECT id, user_id, product_id, price FROM notifications WHERE id = %s"""
        cursor.execute(query, (id,))
        result = cursor.fetchone()

        if result is None:
            return None

        return Notification(result[0], result[1], result[2], result[3])

    @staticmethod
    def create(user_id, product_id, price):
        logging.info(
            f"Creating notification for user {user_id} when product {product_id}'s price is under {price}"
        )

        cursor = Config.conn.cursor()
        query = "INSERT INTO notifications (user_id, product_id, price) VALUES (%s,%s,%s) ON CONFLICT (user_id, product_id) DO NOTHING RETURNING id"
        cursor.execute(query, (user_id, product_id, price))
        notification_id = cursor.fetchone()

        if notification_id is None:
            return None
        notification_id = notification_id[0]

        Config.conn.commit()

        return Notification.get(notification_id)

    @staticmethod
    def find(product_id, price):
        logging.info(
            f"Finding notifications for product {product_id} when price is under {price}"
        )

        cursor = Config.conn.cursor()
        query = "SELECT notifications.id, notifications.user_id, discord_webhook FROM notifications JOIN user_notifications using (user_id) WHERE product_id = %s AND price >= %s"
        cursor.execute(query, (product_id, price))
        results = cursor.fetchall()

        if results is None:
            return []

        return [
            Notification(result[0], result[1], product_id, result[2], price)
            for result in results
        ]

    def to_json(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "product_id": self.product_id,
            "price": self.price,
        }
