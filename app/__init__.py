from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import Config
from flask_login import LoginManager
from flask_moment import Moment
from flask_socketio import SocketIO, send
from flask_mail import Mail

db = SQLAlchemy()

app = Flask(__name__)
socketio = SocketIO(app)
app.config.from_object(Config)
db.init_app(app)
login = LoginManager(app)
login = LoginManager(app)
login.login_view = 'login'
moment = Moment(app)
mail = Mail(app)

from app import routes, models
