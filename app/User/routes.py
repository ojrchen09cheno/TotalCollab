from app.User import bp
from app.models import *
from app import db
from flask import render_template, flash, redirect


@bp.route('/')
def index():
    return render_template('index.html', title='Welcome')
