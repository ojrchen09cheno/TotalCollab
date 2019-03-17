from app import db, login
import string
import random
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from datetime import datetime


#association table for user-workspaces
subs = db.Table('subs',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('workspace_id', db.Integer, db.ForeignKey('workspace.id'))
)

#User class for later
class User(UserMixin, db.Model):
    __tablename__="user"
    id=db.Column(db.Integer,primary_key=True)
    username=db.Column(db.String,nullable=False, unique=True)
    password_hash = db.Column(db.String(128))
    owns = db.relationship("Workspace", backref="user", lazy=True,cascade="all, delete")
    workspaces = db.relationship("Workspace",secondary=subs,backref=db.backref('members', lazy='dynamic'), lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    # messages=db.relationship("Message",backref="user",lazy=True)

@login.user_loader
def load_user(id):
    return User.query.get(int(id))

class Workspace(db.Model):
    __tablename__="workspace"
    id=db.Column(db.Integer,primary_key=True)
    workspaceName=db.Column(db.String,nullable=False,unique=True)
    subgroups=db.relationship("subGroup",backref="workspace",lazy=True,cascade="all, delete")
    code = db.Column(db.String, nullable=False)
    owner = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def addsubgroup(self,name):
        newGroup=subGroup(name=name,workspaceId=self.id)
        db.session.add(newGroup)
        db.session.commit()

    def newCode(self,size=5, chars=string.ascii_uppercase + string.digits):
        self.code = ''.join(random.choice(chars) for _ in range(size))
        db.session.commit()

class subGroup(db.Model):
    __tablename__="subgroup"
    id=db.Column(db.Integer,primary_key=True)
    name=db.Column(db.String,nullable=False)
    messages=db.relationship("Message",backref="subgroup",lazy=True,cascade="all, delete")
    workspaceId=db.Column(db.Integer,db.ForeignKey('workspace.id'),nullable=False)

    def addMessage(self,message, current_user, subgroupId):
        newMessage=Message(message=message,subgroup_id=subgroupId, message_user_id=current_user.id, message_username=current_user.username)
        db.session.add(newMessage)
        db.session.commit()

class Message(db.Model):
    __tablename__="message"
    id=db.Column(db.Integer,primary_key=True)
    message=db.Column(db.String,nullable=False)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    subgroup_id=db.Column(db.Integer, db.ForeignKey('subgroup.id'),nullable=False)
    message_user_id=db.Column(db.Integer, db.ForeignKey('user.id'),nullable=False)
    message_username=db.Column(db.Integer, db.ForeignKey('user.username'),nullable=False)
