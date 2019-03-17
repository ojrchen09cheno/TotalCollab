from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import Config
from flask_login import LoginManager

db = SQLAlchemy()

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)
login = LoginManager(app)
login = LoginManager(app)
login.login_view = 'login'

from app import routes, models
