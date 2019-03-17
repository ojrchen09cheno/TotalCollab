import sys
from flask import Flask, render_template, request, url_for, redirect, flash
from flask_sqlalchemy import SQLAlchemy
from config import Config
from app.models import *
from app import app, db
from flask_login import current_user, login_user, logout_user, login_required
from werkzeug.urls import url_parse
from app.forms import RegistrationForm, LoginForm

#index route
@app.route('/')
@app.route('/index')
def index():
    workspaces = []
    if current_user.is_authenticated:
        workspaces = current_user.workspaces
#    workspaces = Workspace.query.all()
    users = User.query.all()
    return render_template('createWorkspace.html',workspaces = workspaces, users=users)

#create workspace. form is in index route
@app.route("/add_workspace/", methods=["POST"])
@login_required
def add_workspace():
    if request.method =="POST":
        workspaceName = request.form.get("workspaceName")
        workspaces = Workspace.query.all()
        for w in workspaces:
            if workspaceName == w.workspaceName:
                flash("Invalid Workspace Name")
                return redirect(url_for('index'))
        newWorkspace = Workspace(workspaceName = workspaceName, owner = current_user.id)
        newWorkspace.newCode()
        db.session.add(newWorkspace)
        newWorkspace.members.append(current_user)
        db.session.commit()
        newWorkspace.addsubgroup("General")
        return redirect(url_for('workspace', workspaceId=newWorkspace.id))

#workspace route
@app.route("/workspace/<int:workspaceId>")
@login_required
def workspace(workspaceId):
    workspace = Workspace.query.get(workspaceId)
    subgroups = workspace.subgroups
    members = workspace.members
    owner = User.query.get(workspace.owner)
    return render_template('workspace.html', workspaceId = workspaceId, subgroups = subgroups, workspace = workspace, members=members, owner=owner)

#create subgroup route
@app.route("/workspace/<int:workspaceId>/add-subgroup", methods=["GET","POST"])
@login_required
def add_subgroup(workspaceId):
    workspace = Workspace.query.get(workspaceId)
    subgroups = workspace.subgroups
    if request.method =="POST":
        subgroupName = request.form.get("subgroupName")
        workspace.addsubgroup(subgroupName)
        return redirect(url_for('workspace', workspaceId=workspaceId))
    return render_template('createSubgroup.html', subgroups = subgroups, workspace = workspace)

#subgroups route and messages
@app.route("/workspace/<int:workspaceId>/subgroup/<int:subgroupId>", methods=["GET","POST"])
@login_required
def subgroup(workspaceId, subgroupId):
    workspace = Workspace.query.get(workspaceId)
    subgroups= workspace.subgroups
    subgroup = subGroup.query.get(subgroupId)
    messages = subgroup.messages
    if request.method =="POST":
        message = request.form.get("message")
        subgroup.addMessage(message, current_user)
        return redirect(url_for('subgroup', workspaceId=workspaceId, subgroupId = subgroupId))
    return render_template('subgroup.html', workspace=workspace, subgroup=subgroup, messages=messages)

@app.route("/newcode/<int:workspaceId>", methods=["POST"])
@login_required
def newcode(workspaceId):
    workspace = Workspace.query.get(workspaceId)
    workspace.newCode()
    return redirect(url_for('workspace', workspaceId=workspaceId))

@app.route("/join-workspace", methods=["POST"])
@login_required
def joinworkspace():
    username = request.form.get("username")
    code = request.form.get("invitecode")
    workspace = Workspace.query.filter_by(code=code).first()
    if workspace != None:
        workspace.members.append(current_user)
        db.session.commit()
    else:
        flash("Invalid Code")
    return redirect(url_for('index'))
    #user1.followed.append(user2)
    #user1.followed.remove(user2)
    #   def is_following(self, user):
    #    return self.followed.filter(
    #    followers.c.followed_id == user.id).count() > 0

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        login_user(user)
        return redirect(url_for('index'))
    return render_template('login.html', title='Sign In', form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/delete')
def delete():
    #users = User.query.all()
    #workspaces = Workspace.query.all()
    for u in User.query.all():
        db.session.delete(u)
    db.session.commit()
    return redirect(url_for('index'))

# def is_following(self, user):
#        return self.followed.filter(
#            followers.c.followed_id == user.id).count() > 0
