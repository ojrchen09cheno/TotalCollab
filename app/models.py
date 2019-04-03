from app import db, login
import string
import random
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from datetime import datetime
from app.search import *


# integrates ElasticSearch with SQLAlchemy, any class with SearchableMixin can be searched
class SearchableMixin(object):
# using cls instead of self uses the class instead of an instance of the class

    @classmethod
    def search(cls, expression, page, per_page):
        ids, total = query_index(cls.__tablename__, expression, page, per_page)
        if total == 0:
            return cls.query.filter_by(id=0), 0
        when = []
        for i in range(len(ids)):
            when.apeend((ids[i], i))
        return cls.query.filter(cls.id.in_(ids)).order_by(db.case(when, value=cls.id)), total

    @classmethod
    def before_commit(cls, session):
        session._changes = {
            'add': list(session.new),
            'update': list(session.dirty),
            'delete': list(session.deleted)
        }

    @classmethod
    def after_commit(cls, session):
        for obj in session._changes['add']:
            if isinstance(obj, SearchableMixin):
                add_to_index(obj.__tablename__, obj)
        for obj in session._changes['update']:
                if isinstance(obj, SearchableMixin):
                    add_to_index(obj.__tablename__, obj)
        for obj in session._changes['delete']:
            if isinstance(obj, SearchableMixin):
                remove_from_index(obj.__tablename__, obj)
        session._changes = None


    @classmethod
    def reindex(cls):
        for obj in cls.query:
            add_to_index(cls.__tablename__, obj)


# calls the before and after commit methods before and after each commit respectively
db.event.listen(db.session, 'before_commit', SearchableMixin.before_commit)
db.event.listen(db.session, 'after_commit', SearchableMixin.after_commit)


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
    taskboard = db.relationship("Taskboard", backref="taskboard",lazy=True)

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

    def addMessage(self,message, user, subgroupId):
        newMessage=Message(message=message,subgroup_id=subgroupId, message_user_id=user.id, message_username=user.username)
        db.session.add(newMessage)
        db.session.commit()


class Message(SearchableMixin, db.Model):
    __tablename__="message"
    __searchable__=['message']
    id=db.Column(db.Integer,primary_key=True)
    message=db.Column(db.String,nullable=False)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    subgroup_id=db.Column(db.Integer, db.ForeignKey('subgroup.id'),nullable=False)
    message_user_id=db.Column(db.Integer, db.ForeignKey('user.id'),nullable=False)
    message_username=db.Column(db.Integer, db.ForeignKey('user.username'),nullable=False)


class Taskboard(db.Model):
    __tablename__="taskboard"
    id=db.Column(db.Integer, primary_key=True)
    tasks=(db.Column(db.String))
    workspaceId=db.Column(db.Integer, db.ForeignKey('workspace.id'), nullable=False)
    workspace = db.relationship("Workspace", backref='tasks')


class Direct(db.Model):
    __tablename__="direct"
    id=db.Column(db.Integer,primary_key=True)
    userOne = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    userTwo = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    messages=db.relationship("DirectMessage",backref="direct",lazy=True,cascade="all, delete")

    def addMessage(self,message,user,directgroupId):
        newMessage=DirectMessage(message=message,directgroupId=directgroupId,message_user_id=user.id,message_username=user.username)
        db.session.add(newMessage)
        db.session.commit()

class DirectMessage(db.Model):
    __tablename__="directmessage"
    id=db.Column(db.Integer,primary_key=True)
    message=db.Column(db.String,nullable=False)
    directgroupId=db.Column(db.Integer, db.ForeignKey('direct.id'),nullable=False)
    message_user_id=db.Column(db.Integer, db.ForeignKey('user.id'),nullable=False)
    message_username=db.Column(db.Integer, db.ForeignKey('user.username'),nullable=False)
