import sys
from flask import Flask, render_template, request, url_for, redirect
from flask_sqlalchemy import SQLAlchemy
from config import Config
from app.models import *
from app import app, db

#index route
@app.route('/')
def index():
    workspaces = Workspace.query.all()
    return render_template('createWorkspace.html',workspaces = workspaces)

#create workspace. form is in index route
@app.route("/add_workspace/", methods=["POST"])
def add_workspace():
    if request.method =="POST":
        workspaceName = request.form.get("workspaceName")
        newWorkspace = Workspace(workspaceName = workspaceName)
        db.session.add(newWorkspace)
        db.session.commit()
        newWorkspace.addsubgroup("General")
        return redirect(url_for('workspace', workspaceId=newWorkspace.id))

#workspace route
@app.route("/<int:workspaceId>")
def workspace(workspaceId):
    workspace = Workspace.query.get(workspaceId)
    subgroups = workspace.subgroups
    return render_template('workspace.html', workspaceId = workspaceId, subgroups = subgroups, workspace = workspace)

#create subgroup route
@app.route("/<int:workspaceId>/add-subgroup", methods=["GET","POST"])
def add_subgroup(workspaceId):
    workspace = Workspace.query.get(workspaceId)
    subgroups = workspace.subgroups
    if request.method =="POST":
        subgroupName = request.form.get("subgroupName")
        workspace.addsubgroup(subgroupName)
        return redirect(url_for('workspace', workspaceId=workspaceId))
    return render_template('createSubgroup.html', subgroups = subgroups, workspace = workspace)

#subgroups route and messages
@app.route("/<int:workspaceId>/<int:subgroupId>", methods=["GET","POST"])
def subgroup(workspaceId, subgroupId):
    workspace = Workspace.query.get(workspaceId)
    subgroups= workspace.subgroups
    subgroup = subGroup.query.get(subgroupId)
    messages = subgroup.messages
    if request.method =="POST":
        message = request.form.get("message")
        subgroup.addMessage(message)
        return redirect(url_for('subgroup', workspaceId=workspaceId, subgroupId = subgroupId))
    return render_template('subgroup.html', workspace=workspace, subgroup=subgroup, messages=messages)
