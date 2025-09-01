import os

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-change-me")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///app.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    MAX_NIGHTS_PER_MONTH = int(os.environ.get("MAX_NIGHTS_PER_MONTH", "14"))
    ADVANCE_BOOKING_MONTHS = int(os.environ.get("ADVANCE_BOOKING_MONTHS", "12"))
    TIMEZONE = os.environ.get("TIMEZONE", "Europe/Madrid")
