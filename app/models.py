from app import db, login
import string
import random
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from datetime import datetime


# association table for user-workspaces
subs = db.Table('subs',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('workspace_id', db.Integer, db.ForeignKey('workspace.id'))
)

subgroupMember = db.Table('subgroupMember',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('subgroup_id', db.Integer, db.ForeignKey('subgroup.id'))
)

mods = db.Table('mods',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('workspace_id', db.Integer, db.ForeignKey('workspace.id'))
)


# User class for later
class User(UserMixin, db.Model):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String, nullable=False, unique=True)
    username = db.Column(db.String, nullable=False, unique=True)
    password_hash = db.Column(db.String(128))
    firstName = db.Column(db.String(20), nullable=True)
    lastName = db.Column(db.String(20), nullable=True)
    location = db.Column(db.String(30), nullable=True)
    about_me = db.Column(db.Text(), nullable=True)
    owns = db.relationship("Workspace",
                           backref="user", lazy=True, cascade="all, delete")
    mods = db.relationship("Workspace", secondary=mods,
                           backref=db.backref('mods', lazy='dynamic'), lazy='dynamic')
    workspaces = db.relationship("Workspace", secondary=subs,
                                 backref=db.backref('members', lazy='dynamic'), lazy='dynamic')
    subgroups = db.relationship("subGroup", secondary=subgroupMember,
                                backref=db.backref('members', lazy='dynamic'), lazy='dynamic')
    assignee = db.relationship('Taskboard', backref='assigned_person', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    # messages=db.relationship("Message",backref="user",lazy=True)


@login.user_loader
def load_user(id):
    return User.query.get(int(id))


class Workspace(db.Model):
    __tablename__ = "workspace"
    id = db.Column(db.Integer, primary_key=True)
    workspaceName = db.Column(db.String, nullable=False, unique=True)
    code = db.Column(db.String, nullable=False)
    owner = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    taskboard = db.relationship("Taskboard",
                                backref="taskboard", lazy=True)
    subgroups = db.relationship("subGroup",
                                backref="workspace", lazy=True, cascade="all, delete")

    def addsubgroup(self, name, user):
        newGroup = subGroup(name=name, workspaceId=self.id)
        db.session.add(newGroup)
        newGroup.members.append(user)
        db.session.commit()

    def newCode(self, size=5, chars=string.ascii_uppercase + string.digits):
        self.code = ''.join(random.choice(chars) for _ in range(size))
        db.session.commit()

    def addTask(self, name, description, deadline_day, deadline_time, assigned_user, workspaceId):
        newTask = Taskboard(name=name, description=description, deadline_day=deadline_day,
                            deadline_time=deadline_time, assigned_user=assigned_user, workspaceId=self.id)
        db.session.add(newTask)
        db.session.commit()


class subGroup(db.Model):
    __tablename__ = "subgroup"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    workspaceId = db.Column(db.Integer, db.ForeignKey('workspace.id'), nullable=False)
    messages = db.relationship("Messages",
                               backref="subgroup", lazy=True, cascade="all, delete")
    whiteboard = db.relationship("Whiteboard",
                                 backref="subgroup", lazy=True)

    def addMessage(self, message, user, subgroupId):
        newMessage = Messages(message=message, subgroup_id=subgroupId,
                              message_user_id=user.id, message_username=user.username)
        db.session.add(newMessage)
        db.session.commit()

    def addPic(self, whiteboard, user, subgroupId):
        newPicture = Whiteboard(picture=whiteboard, subgroup_id=subgroupId,
                                message_user_id=user.id, message_username=user.username)
        db.session.add(newPicture)
        db.session.commit()


class Whiteboard(db.Model):
    __tablename__ = "whiteboard"
    id = db.Column(db.Integer, primary_key=True)
    picture = db.Column(db.String, nullable=False)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    subgroup_id = db.Column(db.Integer, db.ForeignKey('subgroup.id'), nullable=False)
    message_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message_username = db.Column(db.Integer, db.ForeignKey('user.username'), nullable=False)


class Messages(db.Model):
    __tablename__ = "message"
    __searchable__ = ['message']
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.String, nullable=False)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    subgroup_id = db.Column(db.Integer, db.ForeignKey('subgroup.id'), nullable=False)
    message_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message_username = db.Column(db.Integer, db.ForeignKey('user.username'), nullable=False)


class Taskboard(db.Model):
    __tablename__ = "taskboard"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    description = db.Column(db.String)
    deadline_day = db.Column(db.String)
    deadline_time = db.Column(db.String)
    workspaceId = db.Column(db.Integer, db.ForeignKey('workspace.id'), nullable=False)
    assigned_user = db.Column(db.Integer, db.ForeignKey('user.id'))
    workspace = db.relationship("Workspace",
                                backref='tasks')

    def addTask(self, name, description, deadline_day, deadline_time, assigned_user, workspaceId):
        task = Taskboard(name=name, description=description, deadline_day=deadline_day,
                         deadline_time=deadline_time, assigned_user=assigned_user, workspaceId=workspaceId)
        db.session.add(task)
        db.session.commit()

    def deleteTask(self):
        db.session.delete(self)
        db.session.commit()


class Direct(db.Model):
    __tablename__ = "direct"
    id = db.Column(db.Integer, primary_key=True)
    userOne = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    userTwo = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    messages = db.relationship("DirectMessage",
                               backref="direct", lazy=True, cascade="all, delete")

    def addMessage(self, message, user, directgroupId):
        newMessage = DirectMessage(message=message, directgroupId=directgroupId,
                                   message_user_id=user.id, message_username=user.username)
        db.session.add(newMessage)
        db.session.commit()


class DirectMessage(db.Model):
    __tablename__ = "directmessage"
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.String, nullable=False)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    directgroupId = db.Column(db.Integer, db.ForeignKey('direct.id'), nullable=False)
    message_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message_username = db.Column(db.Integer, db.ForeignKey('user.username'), nullable=False)
