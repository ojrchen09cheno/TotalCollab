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
from app.forms import RegistrationForm, LoginForm, SearchForm, TaskForm, ProfileForm



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
        newWorkspace.addsubgroup("General",current_user)
        return redirect(url_for('workspace', workspaceId=newWorkspace.id))

#workspace route
@app.route("/workspace/<int:workspaceId>/", methods=["POST", "GET"])
@login_required
def workspace(workspaceId):
    workspace = Workspace.query.get(workspaceId)
    subgroups = workspace.subgroups
    members = workspace.members
    owner = User.query.get(workspace.owner)
    form = TaskForm()
    tasks = workspace.taskboard
    if form.validate_on_submit():
        task = Taskboard(tasks=form.tasks.data, workspaceId=workspaceId)
        db.session.add(task)
        db.session.commit()
        flash('Task added')
        return redirect(url_for('workspace', workspaceId=workspaceId))
    return render_template('workspace.html', workspaceId=workspaceId, subgroups=subgroups, workspace=workspace, members=members, owner=owner, tasks=tasks, form=form)

#create subgroup route
@app.route("/workspace/<int:workspaceId>/add-subgroup/", methods=["GET","POST"])
@login_required
def add_subgroup(workspaceId):
    workspace = Workspace.query.get(workspaceId)
    subgroups = workspace.subgroups
    if request.method =="POST":
        subgroupName = request.form.get("subgroupName")
        workspace.addsubgroup(subgroupName, current_user)
        return redirect(url_for('workspace', workspaceId=workspaceId))
    return render_template('createSubgroup.html', subgroups = subgroups, workspace = workspace)

#subgroups route and messages
@app.route("/workspace/<int:workspaceId>/subgroup/<int:subgroupId>/", methods=["GET","POST"])
@login_required
def subgroup(workspaceId, subgroupId):
    workspace = Workspace.query.get(workspaceId)
    subgroups= workspace.subgroups
    subgroup = subGroup.query.get(subgroupId)
    members = subgroup.members
    messages = subgroup.messages
    page = request.args.get('page', 1, type=int)
    messages = Message.query.filter_by(subgroup_id=subgroupId).order_by(Message.timestamp.desc()).paginate(page, app.config['MESSAGES_PER_PAGE'], False)
    return render_template('subgroup.html', workspace=workspace, subgroup=subgroup, messages=messages, user=current_user, members=members)

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

@app.route("/direct/<int:otherUserId>", methods=["GET"])
@login_required
def direct(otherUserId):
    doesItExist= False
    otherUser=User.query.get(otherUserId)
    directQuery=Direct.query.all()
    for x in directQuery:
        if (x.userOne == otherUser.id and x.userTwo ==current_user.id) or (x.userOne == current_user.id and x.userTwo==otherUser.id):
            print("HELLO THERE")
            chatId=x.id
            doesItExist=True
            return redirect(url_for('actualChannel',direct=chatId))
    if doesItExist == False:
        newDirect= Direct(userOne=current_user.id,userTwo=otherUser.id)
        db.session.add(newDirect)
        db.session.commit()
        print(newDirect.id)
        return redirect(url_for('actualChannel',direct=newDirect.id))

    #return ("DirectChat.html")
    return("HEY")
@app.route("/directChat/<int:direct>",methods=["GET","POST"])
def actualChannel(direct):
    channel=Direct.query.get(direct)
    channelId=channel.id
    messages=channel.messages
    if request.method =="POST":
        message=request.form.get("message")
        channel.addMessage(message,current_user,channelId)
        return redirect(url_for('actualChannel', direct=direct))

    return render_template("DirectChat.html",direct=direct, channel=channel,messages=messages)




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
@app.route("/workspace/<int:workspaceId>/subgroup/<int:subgroupId>/search/")
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
    next_url = url_for('search.html', q=g.search_form.q.data, page=page+1) if total > page * current_app.config['MESSAGES_PER_PAGE'] else None
    prev_url = url_for('search.html', q=g.search_form.q.data, page=page-1) if page > 1 else None
    return render_template('search.html', messages=messages, next_url=next_url, prev_url=prev_url,workspaceId=workspaceId, subgroupId=subgroupId)

#add members to a subgroup
@app.route("/workspace/<int:workspaceId>/subgroup/<int:subgroupId>/addMember/", methods=['POST'])
@login_required
def subgroupMember(workspaceId,subgroupId):
    username=request.form.get('username')
    user = User.query.filter_by(username=username)
    subgroup = subGroup.query.get(subgroupId)
    subgroup.members.append(user)
    db.sesssion.commit()
    flash("Added member")
    return redirect(url_for('subgroup'))

#manage members of a subgroup
@app.route("/workspace/<int:workspaceId>/subgropup/<int:subgroupId>/manageMembers/")
@login_required
def manageMembers(workspaceId,subgroupId):
    workspace = Workspace.query.get(workspaceId)
    subgroup = subGroup.query.get(subgroupId)
    subMembers = subgroup.members
    members = workspace.members
    workMembers = []
    check = True
    for w in members:
        for s in subMembers:
            if w == s:
                check=False
        if check==True:
            workMembers.append(w)
        if check==False:
            check=True
    return render_template('manage.html', workspace = workspace, subgroup=subgroup,subMembers = subMembers,workMembers=workMembers)


#Route for adding members to a subgroup
@app.route("/workspace/<int:workspaceId>/subgroup/<int:subgroupId>/add/<int:userId>/",methods=['POST'])
@login_required
def add(workspaceId, subgroupId,userId):
    user = User.query.get(userId)
    subgroup = subGroup.query.get(subgroupId)
    subgroup.members.append(user)
    db.session.commit()
    flash("Added member")
    return redirect(url_for('manageMembers', workspaceId=workspaceId, subgroupId=subgroupId))

#Route for deleting members from a subgroup
@app.route("/workspace/<int:workspaceId>/subgroup/<int:subgroupId>/kick/<int:userId>/", methods=['POST'])
@login_required
def kick(workspaceId, subgroupId, userId):
    user = User.query.get(userId)
    subgroup = subGroup.query.get(subgroupId)
    subgroup.members.remove(user)
    db.session.commit()
    flash("Kicked member")
    return redirect(url_for('manageMembers', workspaceId= workspaceId, subgroupId=subgroupId))

@app.route("/createUserProfile/", methods=["GET", "POST"])
@login_required
def createUserProfile():
    user = current_user
    form = ProfileForm()
    if request.method == 'POST':
        user.firstName = request.form.get("firstName")
        user.lastName = request.form.get("lastName")
        user.location = request.form.get("location")
        user.about_me = request.form.get("about_me")
        db.session.commit()
        flash("Thanks for creating a profile!")
        #return " Test"
        #return render_template("createUserProfile.html", workspace=workspace, form=form)
        return redirect(url_for('user', username = user.username))
    return render_template("createUserProfile.html", workspace=workspace, form=form)

@app.route("/profile/<string:username>", methods=["GET"])
@login_required
def user(username):
    user= User.query.filter_by(username=username).first()
    return render_template('userProfile.html', user=user, workspace=workspace)
