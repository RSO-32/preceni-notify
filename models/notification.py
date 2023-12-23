from config import Config
from dataclasses import dataclass
from flask import current_app as app


@dataclass
class Notification:
    id: int
    user_id: int
    product_id: int
    price: float
    discord_webhook: str

    @staticmethod
    def get(id):
        cursor = Config.conn.cursor()
        query = "SELECT id, user_id, product_id, price, discord_webhook FROM notifications WHERE id = %s"
        cursor.execute(query, (id,))
        result = cursor.fetchone()

        if result is None:
            return None

        return Notification(result[0], result[1], result[2], result[3], result[4])

    @staticmethod
    def get_all():
        cursor = Config.conn.cursor()
        query = """SELECT id, user_id, product_id, price, discord_webook FROM notifications"""
        cursor.execute(query)
        result = cursor.fetchall()

        notifications = []
        for row in result:
            notifications.append(Notification(row[0], row[1], row[2], row[3], row[4]))

        return notifications

    @staticmethod
    def create(user_id, product_id, price, discord_webhook):
        app.logger.info(f"Creating notification for user {user_id} when product {product_id}'s price is under {price}")

        cursor = Config.conn.cursor()
        query = "INSERT INTO notifications (user_id, product_id, price, discord_webhook) VALUES (%s,%s,%s,%s) ON CONFLICT (user_id, product_id) DO NOTHING RETURNING id"
        cursor.execute(query, (user_id, product_id, price, discord_webhook))
        notification_id = cursor.fetchone()

        if notification_id is None:
            return None
        notification_id = notification_id[0]

        Config.conn.commit()

        return Notification.get(notification_id)

    @staticmethod
    def find(product_id, price):
        app.logger.info(f"Finding notifications for product {product_id} when price is under {price}")

        cursor = Config.conn.cursor()
        query = "SELECT id, user_id, discord_webhook FROM notifications WHERE product_id = %s AND price >= %s"
        cursor.execute(query, (product_id, price))
        results = cursor.fetchall()

        if results is None:
            return []

        return [Notification(result[0], result[1], product_id, price, result[2]) for result in results]

    def to_json(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "product_id": self.product_id,
            "price": self.price,
        }
