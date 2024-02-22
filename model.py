from flask_sqlalchemy import SQLAlchemy
from datetime import datetime  

db = SQLAlchemy()

class EmailRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_email = db.Column(db.String(255), nullable=False)
    receiver_email = db.Column(db.String(255), nullable=False)
    link=db.Column(db.Text,nullable=True)
    read = db.Column(db.Boolean, default=False)
    link_present = db.Column(db.Boolean, default=False)
    token = db.Column(db.String(255), nullable=True)
    link_records = db.relationship('LinkRecord', backref='email_record', lazy=True)
    Email_send_time = db.Column(db.DateTime, default=datetime.now, nullable=False)

class LinkRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(255), nullable=False)
    email_record_id = db.Column(db.Integer, db.ForeignKey('email_record.id'), nullable=False)
    link_click = db.Column(db.Boolean, default=0)
    number_of_times_link_click = db.Column(db.Integer, default=0)
    open_time = db.Column(db.DateTime, default=datetime.now, nullable=True)