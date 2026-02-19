import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(
        BASE_DIR, "instance", "networth.db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # API endpoints
    COINGECKO_BTC_SEK = (
        "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=sek"
    )
    EUR_SEK_API = "https://api.exchangerate-api.com/v4/latest/EUR"
