from config import Config
from os import environ
import psycopg2
import logging


class Database:
    @staticmethod
    def connect():
        Config.conn = psycopg2.connect(
            database=environ.get("DB_NAME"),
            host=environ.get("DB_HOST"),
            user=environ.get("DB_USER"),
            password=environ.get("DB_PASSWORD"),
            port=environ.get("DB_PORT"),
        )

    logging.info("Initialized database connection")
