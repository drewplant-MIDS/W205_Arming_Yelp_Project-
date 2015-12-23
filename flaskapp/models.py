from flaskapp import app
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy(app)

class inspections (db.Model):
    __tablename__ = "inspections"
    busid = db.Column('busid', db.Integer, primary_key=True)
    score = db.Column('score', db.Integer)
    date = db.Column('date', db.Unicode)
    type = db.Column('type',db.Unicode)

class Violation (db.Model):
    __tablename__ = "violations"
    busid = db.Column('busid', db.Integer, primary_key=True)
    inspectdate = db.Column('inspectdate', db.Date)
    violationid = db.Column('violationid', db.Unicode)
    risk = db.Column('risk', db.Unicode)
    description = db.Column('description', db.Unicode)
