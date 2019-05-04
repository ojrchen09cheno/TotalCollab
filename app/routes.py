import sys
from flask import Flask, render_template, request, url_for, redirect, flash, g, jsonify, current_app
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, send
from config import Config
import json
from app.models import *
from app import app, db, socketio, mail
from flask_login import current_user, login_user, logout_user, login_required
from werkzeug.urls import url_parse
from app.forms import RegistrationForm, LoginForm, ProfileForm
from flask_mail import Message


@app.route('/')
@app.route('/about/')
def aboutTotalCollab():
    totalUsers = User.query.count()
    totalWorkspaces = Workspace.query.count()
    totalWsMessages = Messages.query.count()
    totalDmMessages = DirectMessage.query.count()
    totalMessages = totalWsMessages+totalDmMessages
    return render_template('aboutTotalCollab.html', totalUsers=totalUsers,
                           totalWorkspaces=totalWorkspaces, totalMessages=totalMessages)


# index route
@app.route('/index/')
def index():
    workspaces = []
    if current_user.is_authenticated:
        workspaces = current_user.workspaces
#    workspaces = Workspace.query.all()
    users = User.query.all()
    return render_template('createWorkspace.html',workspaces = workspaces, users=users)


# create workspace. form is in index route
@app.route("/add_workspace/", methods=["POST"])
@login_required
def add_workspace():
    if request.method == "POST":
        workspaceName = request.form.get("workspaceName")
        workspaces = Workspace.query.all()
        for w in workspaces:
            if workspaceName == w.workspaceName:
                flash("Invalid Workspace Name")
                return redirect(url_for('index'))
        newWorkspace = Workspace(workspaceName=workspaceName, owner=current_user.id)
        newWorkspace.newCode()
        newWorkspace.mods.append(current_user)
        db.session.add(newWorkspace)
        newWorkspace.members.append(current_user)
        db.session.commit()
        newWorkspace.addsubgroup("General",current_user)
        return redirect(url_for('workspace', workspaceId=newWorkspace.id))


# workspace route
@app.route("/workspace/<int:workspaceId>/", methods=["POST", "GET"])
@login_required
def workspace(workspaceId):
    workspace = Workspace.query.get(workspaceId)
    subgroups = []
    status = False
    for m in workspace.mods:
        if current_user == m:
            subgroups = workspace.subgroups
            status = True
    if status == False:
        for s in workspace.subgroups:
            if s.name == 'General':
                subgroups.append(s)
            else:
                for submember in s.members:
                    if current_user == submember:
                        subgroups.append(s)
    members = workspace.members
    owner = User.query.get(workspace.owner)
    tasks = workspace.taskboard
    user = current_user
    current_Date_Time = datetime.now()

    if request.method == "POST":
        Filter = request.form.get("filterName")
        userF = User.query.filter_by(username=Filter).first()
        if userF is not None:
            tasks = Taskboard.query.filter_by(assigned_user=userF.id, workspaceId=workspaceId)
            return render_template('workspace.html', workspaceId=workspaceId, subgroups=subgroups,
                                   workspace=workspace, members=members, owner=owner, tasks=tasks, user=user)
    return render_template('workspace.html', workspaceId=workspaceId, subgroups=subgroups,
                           workspace=workspace, members=members, owner=owner, tasks=tasks, user=user)


@app.route('/workspace/<int:workspaceId>/reminder/task/<int:taskId>/everyone', methods=['GET', 'POST'])
def sendReminderEveryone(workspaceId, taskId):
        workspace = Workspace.query.get(workspaceId)
        subgroups = workspace.subgroups
        members = workspace.members
        tasks = workspace.taskboard
        taskId = taskId
        if request.method == "POST":
            # message_subject = request.form.get("message_subject")
            # message_content = request.form.get("message_content")
            # for m in members:
            #     msg = Message(subject=message_subject, sender=app.config['MAIL_USERNAME'])
            #     msg.body = message_content
            #     msg.add_recipient(m.email)
            #     mail.send(msg)
            with mail.connect() as conn:
                for m in members:
                    message_subject = request.form.get("message_subject")
                    message_content = request.form.get("message_content")
                    msg = Message(recipients=[m.email], sender=app.config['MAIL_USERNAME'], subject=message_subject)
                    msg.html = render_template('emailReminder.html', username=m.username,
                                               message_content=message_content, tasks=tasks,
                                               taskId=taskId, workspace=workspace)
                    conn.send(msg)
            return redirect(url_for('workspace', workspaceId=workspaceId))
        return render_template('sendReminder.html', workspaceId=workspaceId, subgroups=subgroups,
                               workspace=workspace, members=members, tasks=tasks, taskId=taskId)


@app.route('/workspace/<int:workspaceId>/reminder/task/<int:taskId>/<string:assigned_person>', methods=['GET','POST'])
def sendReminderAssigned(workspaceId, taskId, assigned_person):
        workspace = Workspace.query.get(workspaceId)
        subgroups = workspace.subgroups
        members = workspace.members
        user = User.query.filter_by(username=assigned_person).first()
        tasks = workspace.taskboard
        taskId = taskId
        if request.method == "POST":
            message_subject = request.form.get("message_subject")
            message_content = request.form.get("message_content")
            msg = Message(subject=message_subject, sender=app.config['MAIL_USERNAME'])
            msg.html = render_template('emailReminder.html', username=user.username,
                                       message_content=message_content, tasks=tasks,
                                       taskId=taskId, workspace=workspace)
            msg.add_recipient(user.email)
            mail.send(msg)
            return redirect(url_for('workspace', workspaceId=workspaceId))
        return render_template('sendReminder.html', workspaceId=workspaceId, subgroups=subgroups,
                               workspace=workspace, members=members,
                               tasks=tasks, taskId=taskId, assigned_person=assigned_person)


# create subgroup route
@app.route("/workspace/<int:workspaceId>/add-subgroup/", methods=["GET","POST"])
@login_required
def add_subgroup(workspaceId):
    workspace = Workspace.query.get(workspaceId)
    owner = User.query.get(workspace.owner)
    subgroups = workspace.subgroups
    if request.method == "POST":
        subgroupName = request.form.get("subgroupName")
        for s in subgroups:
            if subgroupName == s.name:
                flash("Subgroup Already Exists")
                return redirect(url_for('add_subgroup', workspaceId=workspaceId))
        workspace.addsubgroup(subgroupName, owner)
        return redirect(url_for('workspace', workspaceId=workspaceId))
    return render_template('createSubgroup.html', subgroups=subgroups, workspace=workspace)


# subgroups route and messages
@app.route("/workspace/<int:workspaceId>/subgroup/<int:subgroupId>/", methods=["GET", "POST"])
@login_required
def subgroup(workspaceId, subgroupId):
    workspace = Workspace.query.get(workspaceId)
    subgroups = workspace.subgroups
    subgroup = subGroup.query.get(subgroupId)
    members = subgroup.members
    page = request.args.get('page', 1, type=int)
    messages = Messages.query.filter_by(subgroup_id=subgroupId)\
        .order_by(Messages.timestamp.desc())\
        .paginate(page, app.config['MESSAGES_PER_PAGE'], False)
    whiteboard = Whiteboard.query.filter_by(subgroup_id=subgroupId)\
        .order_by(Whiteboard.id.desc())
    return render_template('subgroup.html', workspace=workspace, subgroup=subgroup, messages=messages,
                           user=current_user, members=members, whiteboard=whiteboard)


@socketio.on('message')
def handleMessage(msg):

    p = json.dumps(msg)
    hey = json.loads(p)

    print('message: ' + str(msg))
    workspace = Workspace.query.get(hey['workspaceId'])
    subgroups = workspace.subgroups
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
        if (x.userOne == otherUser.id and x.userTwo == current_user.id) or \
                (x.userOne == current_user.id and x.userTwo == otherUser.id):
            print("HELLO THERE")
            chatId=x.id
            doesItExist=True
            return redirect(url_for('actualChannel', direct=chatId))
    if doesItExist == False:
        newDirect= Direct(userOne=current_user.id, userTwo=otherUser.id)
        db.session.add(newDirect)
        db.session.commit()
        print(newDirect.id)
        return redirect(url_for('actualChannel', direct=newDirect.id))

    # return ("DirectChat.html")
    return "HEY"


@app.route("/directChat/<int:direct>",methods=["GET", "POST"])
def actualChannel(direct):
    channel = Direct.query.get(direct)
    channelId = channel.id
    # messages=channel.messages
    page = request.args.get('page', 1, type=int)
    messages = DirectMessage.query.filter_by(directgroupId=direct)\
        .order_by(DirectMessage.timestamp.desc())\
        .paginate(page, app.config['MESSAGES_PER_PAGE'], False)
    if request.method == "POST":
        message = request.form.get("message")
        channel.addMessage(message, current_user, channelId)
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
    # user1.followed.append(user2)
    # user1.followed.remove(user2)
    #   def is_following(self, user):
    #    return self.followed.filter(
    #    followers.c.followed_id == user.id).count() > 0


@app.route("/leave-workspace/<int:workspaceId>/", methods=['GET', 'POST'])
@login_required
def leaveWorkspace(workspaceId):
    workspace = Workspace.query.filter_by(id=workspaceId).first()
    return render_template('confirmLeaveWorkspace.html', workspace=workspace)


@app.route("/confirm-leave-workspace/<int:workspaceId>/", methods=['POST'])
@login_required
def confirmLeaveWorkspace(workspaceId):
    user = User.query.get(current_user.id)
    workspace = Workspace.query.filter_by(id=workspaceId).first()
    for m in workspace.mods:
        if current_user.id == m.id:
            workspace.mods.remove(user)
            db.session.commit()
    workspace.members.remove(user)
    db.session.commit()
    return redirect(url_for('index'))


@app.route("/kick-workspace/<int:workspaceId>/user/<int:userId>", methods=['GET', 'POST'])
@login_required
def kickWorkspace(workspaceId, userId):
    workspace = Workspace.query.filter_by(id=workspaceId).first()
    user = User.query.filter_by(id=userId).first()
    return render_template('confirmKickWorkspace.html', workspace=workspace, user=user)


@app.route("/confirm-kick-workspace/<int:workspaceId>/user/<int:userId>", methods=['POST'])
@login_required
def confirmKickWorkspace(workspaceId, userId):
    workspace = Workspace.query.filter_by(id=workspaceId).first()
    user = User.query.filter_by(id=userId).first()
    for m in workspace.mods:
        if user.id == m.id:
            workspace.mods.remove(user)
            db.session.commit()
    workspace.members.remove(user)
    db.session.commit()
    worskspaceId = workspace.id
    return redirect(url_for('mods', workspaceId=worskspaceId))


@app.route('/register/', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
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
    return redirect(url_for('aboutTotalCollab'))


@app.route('/delete/')
def delete():
    # users = User.query.all()
    # workspaces = Workspace.query.all()
    for u in User.query.all():
        db.session.delete(u)
    db.session.commit()
    return redirect(url_for('index'))

# def is_following(self, user):
#        return self.followed.filter(
#            followers.c.followed_id == user.id).count() > 0

# search messages within a subgroup


@app.route("/workspace/<int:workspaceId>/subgroup/<int:subgroupId>/search-messages/", methods=["GET", "POST"])
@login_required
def searchSubgroupMessages(workspaceId, subgroupId):
    workspace = Workspace.query.get(workspaceId)
    subgroups = workspace.subgroups
    subgroup = subGroup.query.get(subgroupId)
    search = request.args.get('search', '*', type=str)
    page = request.args.get('page', 1, type=int)
    page = request.args.get('page', 1, type=int)
    messages = Messages.query.filter_by(subgroup_id=subgroupId)\
        .filter(Messages.message.contains(search))\
        .order_by(Messages.timestamp.desc())\
        .paginate(page, app.config['MESSAGES_PER_PAGE'], False)
    if request.method == 'POST':
        search = request.form.get("search")
        page = request.args.get('page', 1, type=int)
        messages = Messages.query.filter_by(subgroup_id=subgroupId)\
            .filter(Messages.message.contains(search))\
            .order_by(Messages.timestamp.desc())\
            .paginate(page, app.config['MESSAGES_PER_PAGE'], False)
    return render_template("viewSubgroupMessagesSearch.html", workspace=workspace, subgroup=subgroup,
                           messages=messages, search=search, page=page)


# manage members of a subgroup
@app.route("/workspace/<int:workspaceId>/subgropup/<int:subgroupId>/manageMembers/")
@login_required
def manageMembers(workspaceId,subgroupId):
    workspace = Workspace.query.get(workspaceId)
    subgroup = subGroup.query.get(subgroupId)
    subMembers = subgroup.members
    members = workspace.members
    members = []
    for m in workspace.members:
        members.append(m)
    workMembers = []
    owner = User.query.get(workspace.owner)
    mods = workspace.mods
    check = True
    for m in mods:
        for w in members:
            if m == w:
                members.remove(m)
    for w in members:
        for s in subMembers:
            if w == s:
                check=False
        if check==True:
            workMembers.append(w)
        if check==False:
            check = True
    return render_template('manage.html', workspace=workspace, subgroup=subgroup,
                           subMembers=subMembers, workMembers=workMembers, owner=owner)


# Route for adding members to a subgroup
@app.route("/workspace/<int:workspaceId>/subgroup/<int:subgroupId>/add/<int:userId>/", methods=['POST'])
@login_required
def add(workspaceId, subgroupId,userId):
    user = User.query.get(userId)
    subgroup = subGroup.query.get(subgroupId)
    subgroup.members.append(user)
    db.session.commit()
    flash("Added member")
    return redirect(url_for('manageMembers', workspaceId=workspaceId, subgroupId=subgroupId))


# Route for deleting members from a subgroup
@app.route("/workspace/<int:workspaceId>/subgroup/<int:subgroupId>/kick/<int:userId>/", methods=['POST'])
@login_required
def kick(workspaceId, subgroupId, userId):
    user = User.query.get(userId)
    subgroup = subGroup.query.get(subgroupId)
    subgroup.members.remove(user)
    db.session.commit()
    flash("Kicked member")
    return redirect(url_for('manageMembers', workspaceId= workspaceId, subgroupId=subgroupId))


# manage moderators of a workspace
@app.route("/workspace/<int:workspaceId>/mods/")
@login_required
def mods(workspaceId):
    workspace = Workspace.query.get(workspaceId)
    members = workspace.members
    mods = workspace.mods
    workMembers = []
    owner = User.query.get(workspace.owner)
    check = True
    for w in members:
        for m in mods:
            if w == m:
                check=False
        if check==True:
            workMembers.append(w)
        if check==False:
            check=True
    return render_template('mods.html', workspace = workspace, mods = mods,workMembers=workMembers, owner = owner)


# Route for adding moderators
@app.route("/workspace/<int:workspaceId>/mods/add/<int:userId>/",methods=['POST'])
@login_required
def addMod(workspaceId,userId):
    user = User.query.get(userId)
    workspace = Workspace.query.get(workspaceId)
    workspace.mods.append(user)
    db.session.commit()
    flash("Added Moderator")
    return redirect(url_for('mods', workspaceId=workspaceId))


# Route for removing a moderator
@app.route("/workspace/<int:workspaceId>/mods/kick/<int:userId>/", methods=['POST'])
@login_required
def kickMod(workspaceId, userId):
    user = User.query.get(userId)
    workspace = Workspace.query.get(workspaceId)
    workspace.mods.remove(user)
    db.session.commit()
    flash("Removed Moderator")
    return redirect(url_for('mods', workspaceId= workspaceId))


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
        # return " Test"
        # return render_template("createUserProfile.html", workspace=workspace, form=form)
        return redirect(url_for('user', username = user.username))
    return render_template("createUserProfile.html", workspace=workspace, form=form)


@app.route("/profile/<string:username>", methods=["GET"])
@login_required
def user(username):
    user = User.query.filter_by(username=username).first()
    return render_template('userProfile.html', user=user, workspace=workspace)


@app.route("/<int:workspaceId>/<int:taskId>/taskboardDelete", methods=['GET', 'POST'])
@login_required
def taskboardDelete(workspaceId, taskId):

    workspace = Workspace.query.get(workspaceId)
    task = Taskboard.query.get(taskId)
    if request.method == "POST":
        Taskboard.deleteTask(task)
        return redirect(url_for('workspace', workspaceId=workspaceId))
    return render_template('taskboardDelete.html', workspaceId=workspaceId, workspace=workspace, task=task)


@app.route("/<int:workspaceId>/<int:userId>/personalTasks", methods=['GET', 'POST'])
@login_required
def showPerTask(workspaceId, userId):
    tasks = Taskboard.query.filter_by(assigned_user=userId)
    return render_template('taskboard.html', workspaceId=workspaceId, tasks=tasks)


@app.route("/<int:workspaceId>/addTask", methods=['GET', 'POST'])
@login_required
def addTask(workspaceId):
    workspace = Workspace.query.get(workspaceId)
    subgroups = workspace.subgroups
    members = workspace.members
    owner = User.query.get(workspace.owner)
    tasks = workspace.taskboard
    if request.method == "POST":
        name = request.form.get("name")
        description = request.form.get("description")
        deadline_day = request.form.get("deadline_day")
        deadline_time = request.form.get("deadline_time")
        assigned_user = request.form.get("assigned_user")
        userAssigned = User.query.filter_by(id=assigned_user).first()
        workspace.addTask(name, description, deadline_day, deadline_time, userAssigned.id, workspaceId)
        return redirect(url_for('workspace', workspaceId=workspaceId))
    return render_template('taskboardAdd.html',workspaceId=workspaceId, workspace=workspace, members=members)


@app.route("/workspace/<int:workspaceId>/subgroup/<int:subgroupId>/Draw", methods=["GET","POST"])
@login_required
def drawing(workspaceId, subgroupId):
    # p=json.dumps(data)
    # hey=json.loads(p)
    # print('message: ' + str(data))
    workspace = Workspace.query.get(workspaceId)
    subgroup = subGroup.query.get(subgroupId)
    return render_template("Drawing.html",workspace= workspace, subgroup=subgroup)


@app.route("/savedrawing", methods=["POST"])
def savepic():
    a = request.form['dataURL']
    b = request.form['workspaceId']
    c = request.form['subgroupId']

    print(str(a))

    workspace = Workspace.query.get(b)
    subgroup = subGroup.query.get(c)
    subgroup.addPic(a, current_user, c)
    # save method here
    return "It's Good?"


@app.route("/Test2", methods=["GET"])
def f():
    workspace = Workspace.query.get(1)
    subgroup = subGroup.query.get(1)
    whiteboard = subgroup.whiteboard
    return render_template("OTHERTEST.html", whiteboard=whiteboard)


@app.route("/view-user-profiles/", methods=["GET", "POST"])
@login_required
def viewUserProfiles():
    page = request.args.get('page', 1, type=int)
    users = User.query.paginate(page, app.config['USERS_PER_PAGE'], False)
    return render_template("viewUserProfiles.html", users=users)


@app.route("/search-user-profiles/", methods=["GET", "POST"])
@login_required
def searchUserProfiles():
    search = request.args.get('search', '*', type=str)
    page = request.args.get('page', 1, type=int)
    users = User.query.filter(User.username.contains(search))\
        .paginate(page, app.config['USERS_PER_PAGE'], False)
    if request.method == 'POST':
        search = request.form.get("search")
        page = request.args.get('page', 1, type=int)
        users = User.query.filter(User.username.contains(search))\
            .paginate(page, app.config['USERS_PER_PAGE'], False)
    return render_template("viewUserProfilesSearch.html", users=users, search=search)


@app.route("/invite-workspace/user/<string:username>", methods=["GET", "POST"])
@login_required
def inviteUserWorkspace(username):
    user = User.query.filter_by(username=username).first()
    workspaces = Workspace.query.all()
    total_ws = []
    hide = []
    show = []
    for w in workspaces:
        total_ws.append(w)
        for m in w.members:
            if user.id == m.id:
                hide.append(w)
    not_member_WS = [i for i in total_ws + hide if i not in total_ws or i not in hide]
    for s in not_member_WS:
        if s.owner == current_user.id:
            show.append(s)
        else:
            mods = s.mods
            for mod in mods:
                if mod == current_user:
                    show.append(s)
    return render_template("inviteUserWorkspace.html", user=user, workspaces=workspaces, show=show)


@app.route("/confirm-invite-workspace/user/<string:username>/workspace/<string:workspaceID>", methods=["GET", "POST"])
@login_required
def confirmInviteUserWorkspace(username, workspaceID):
    user = User.query.filter_by(username=username).first()
    workspace = Workspace.query.filter_by(id=workspaceID).first()
    if request.method == "POST":
        workspace = Workspace.query.filter_by(id=workspaceID).first()
        owner = User.query.get(workspace.owner)
        message_subject = "Invitation To Workspace: " + workspace.workspaceName
        msg = Message(subject=message_subject, sender=app.config['MAIL_USERNAME'])
        msg.html = render_template('emailInviteWorkspace.html', user=user, workspace=workspace, owner=owner)
        msg.add_recipient(user.email)
        mail.send(msg)
        return redirect(url_for('viewUserProfiles'))
    return render_template("confirmInviteUserWorkspace.html", user=user, workspace=workspace)
