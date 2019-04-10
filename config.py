import os

basedir = os.path.abspath(os.path.dirname(__file__))

class Config(object):
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MESSAGES_PER_PAGE = 10
    ELASTICSEARCH_URL = os.environ.get('ELASTICSEARCH_URL')

    MAIL_SERVER = 'smtp.gmail.com' # name of the email server
    MAIL_PORT = 465 # port of server
    # MAIL_USE_TSL = True for more encryption
    MAIL_USE_SSL = True # enable SSL encryption
    MAIL_USERNAME = 'Total.Collab1@gmail.com' # username of sender
    MAIL_PASSWORD = '#CUS1166' # password of sender
