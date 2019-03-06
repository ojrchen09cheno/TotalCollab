from flask import Blueprint

bp = Blueprint('User', __name__)

from app.User import forms, routes
