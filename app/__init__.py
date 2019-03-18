from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import Config
from flask_login import LoginManager
from flask_moment import Moment
from elasticsearch import Elasticsearch
from flask_socketio import SocketIO, send

db = SQLAlchemy()

app = Flask(__name__)
socketio = SocketIO(app)
app.config.from_object(Config)
db.init_app(app)
login = LoginManager(app)
login = LoginManager(app)
login.login_view = 'login'
moment = Moment(app)
app.elasticsearch = Elasticsearch([app.config['ELASTICSEARCH_URL']]) \
    if app.config['ELASTICSEARCH_URL'] else None

from app import routes, models
