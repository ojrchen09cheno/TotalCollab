from app import db

#User class for later
#class User(db.Model):
#    __tablename__="user"
#    id=db.Column(db.Integer,primary_key=True)
#    username=db.Column(db.String,nullable=False)
#    workspaces=db.relationship("Workspace",backref="user",lazy=True)
#    messages=db.relationship("message",backref="user",lazy=True)

class Workspace(db.Model):
    __tablename__="workspace"
    id=db.Column(db.Integer,primary_key=True)
    workspaceName=db.Column(db.String,nullable=False)
    subgroups=db.relationship("subGroup",backref="workspace",lazy=True)

    def addsubgroup(self,name):
        newGroup=subGroup(name=name,workspaceId=self.id)
        db.session.add(newGroup)
        db.session.commit()

class subGroup(db.Model):
    __tablename__="subgroup"
    id=db.Column(db.Integer,primary_key=True)
    name=db.Column(db.String,nullable=False)
    messages=db.relationship("Message",backref="subgroup",lazy=True)
    workspaceId=db.Column(db.Integer,db.ForeignKey('workspace.id'),nullable=False)

    def addMessage(self,message):
        newMessage=Message(message=message,subgroup_id=self.id)
        db.session.add(newMessage)
        db.session.commit()

class Message(db.Model):
    __tablename__="message"
    id=db.Column(db.Integer,primary_key=True)
    message=db.Column(db.String,nullable=False)
    subgroup_id=db.Column(db.Integer, db.ForeignKey('subgroup.id'),nullable=False)
