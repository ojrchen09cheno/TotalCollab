import sys
from flask import Flask, render_template, request, url_for, redirect, flash, g, jsonify, current_app
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, send
from config import Config
import json
from app.models import *
from app import app, db, socketio
from flask_login import current_user, login_user, logout_user, login_required
from werkzeug.urls import url_parse
from app.forms import RegistrationForm, LoginForm, SearchForm



@app.before_request
def before_request():
    if current_user.is_authenticated:
        db.session.commit()
        g.search_form = SearchForm()
    g.locale = str()

#index route
@app.route('/')
@app.route('/index/')
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
@app.route("/workspace/<int:workspaceId>/")
@login_required
def workspace(workspaceId):
    workspace = Workspace.query.get(workspaceId)
    subgroups = workspace.subgroups
    members = workspace.members
    owner = User.query.get(workspace.owner)
    return render_template('workspace.html', workspaceId = workspaceId, subgroups = subgroups, workspace = workspace, members=members, owner=owner)

#create subgroup route
@app.route("/workspace/<int:workspaceId>/add-subgroup/", methods=["GET","POST"])
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
@app.route("/workspace/<int:workspaceId>/subgroup/<int:subgroupId>/", methods=["GET","POST"])
@login_required
def subgroup(workspaceId, subgroupId):
    workspace = Workspace.query.get(workspaceId)
    subgroups= workspace.subgroups
    subgroup = subGroup.query.get(subgroupId)
    messages = subgroup.messages
    page = request.args.get('page', 1, type=int)
    messages = Message.query.filter_by(subgroup_id=subgroupId).order_by(Message.timestamp.desc()).paginate(page, app.config['MESSAGES_PER_PAGE'], False)
    older_url = url_for('subgroup', workspaceId=workspaceId, subgroupId=subgroupId, page=messages.next_num) \
        if messages.has_next else None
    newer_url = url_for('subgroup', workspaceId=workspaceId, subgroupId=subgroupId, page=messages.prev_num) \
        if messages.has_prev else None

    return render_template('subgroup.html', workspace=workspace, subgroup=subgroup, messages=messages.items,
                            newer_url=newer_url,older_url=older_url, user=current_user)

@socketio.on('message')
def handleMessage(msg):

    p=json.dumps(msg)
    hey=json.loads(p)

    print('message: ' + str(msg))
    workspace = Workspace.query.get(hey['workspaceId'])
    subgroups= workspace.subgroups
    subgroup = subGroup.query.get(hey['subgroupId'])
    messages = subgroup.messages
    user = User.query.get(hey['user'])
    subgroup.addMessage(hey['message'],user,hey['subgroupId'])
    send(msg, broadcast=True)




@app.route("/newcode/<int:workspaceId>/", methods=["POST"])
@login_required
def newcode(workspaceId):
    workspace = Workspace.query.get(workspaceId)
    workspace.newCode()
    return redirect(url_for('workspace', workspaceId=workspaceId))

@app.route("/join-workspace/", methods=["POST"])
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

@app.route('/register/', methods=['GET', 'POST'])
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

@app.route('/login/', methods=['GET', 'POST'])
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

@app.route('/logout/')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/delete/')
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


# shows the search page with results
@app.route('/workspace/<int:workspaceId>/subgroup/<int:subgroupId>/search/')
@login_required
def search(workspaceId, subgroupId):
    if not g.search_form.validate():
        return redirect(url_for('login'))
    workspace = Workspace.query.get(workspaceId)
    subgroups = workspace.subgroups
    subgroup = subGroup.query.get(subgroupId)
    messages = subgroup.messages
    page = request.args.get('page', 1, type=int)
    messages, total = Message.search(g.search_form.q.data, page, current_app.config['MESSAGES_PER_PAGE'])
    next_url = url_for('search.html', q=g.search_form.q.data, page=page+1) \
        if total > page * current_app.config['MESSAGES_PER_PAGE'] else None
    prev_url = url_for('search.html', q=g.search_form.q.data, page=page-1, ) \
        if page > 1 else None
    return render_template('search.html', messages=messages, next_url=next_url, prev_url=prev_url,
                           workspaceId=workspaceId, subgroupId=subgroupId)
