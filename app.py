from app import app, db
from app.models import *
import sys

def main():
    if (len(sys.argv)==2):
        print(sys.argv)
        if sys.argv[1] == 'createdb':
            db.create_all()
    else:
        print("Run app using 'flask run' . To create a database use 'python app.py createdb' ")

if __name__=="__main__":
    with app.app_context():
        main()

@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User, 'Post': Post}
