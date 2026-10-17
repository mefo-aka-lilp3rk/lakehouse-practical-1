import os

SECRET_KEY = os.environ["SUPERSET_SECRET_KEY"]
SQLALCHEMY_DATABASE_URI = "sqlite:////app/superset_home/superset.db"
ENABLE_PROXY_FIX = True
WTF_CSRF_ENABLED = True
