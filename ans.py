# from flask_sqlalchemy import SQLAlchemy
# from datetime import datetime  

# db = SQLAlchemy()

# class EmailRecord(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     sender_email = db.Column(db.String(255), nullable=False)
#     receiver_email = db.Column(db.String(255), nullable=False)
#     link=db.Column(db.Text,nullable=True)
#     read = db.Column(db.Boolean, default=False)
#     link_present = db.Column(db.Boolean, default=False)
#     token = db.Column(db.String(255), nullable=True)
#     link_records = db.relationship('LinkRecord', backref='email_record', lazy=True)
#     Email_send_time = db.Column(db.DateTime, default=datetime.now, nullable=False)

# class LinkRecord(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     token = db.Column(db.String(255), nullable=False)
#     email_record_id = db.Column(db.Integer, db.ForeignKey('email_record.id'), nullable=False)
#     link_click = db.Column(db.Boolean, default=0)
#     number_of_times_link_click = db.Column(db.Integer, default=0)
#     open_time = db.Column(db.DateTime, default=datetime.now, nullable=True)


from flask import Flask, request, redirect, session, url_for, jsonify
from authlib.integrations.flask_client import OAuth
import os
import requests
from flask_cors import CORS
import re
from urllib.parse import urlparse, parse_qs
import mysql.connector
from model import db
from model import db, EmailRecord ,LinkRecord
import secrets 
import json
from datetime import datetime
from flask import make_response


app = Flask(__name__)
CORS(app)
app.secret_key = os.urandom(24)

#SQLAlchemy database URI
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://root:new_password@localhost/referral'

# Initialize the SQLAlchemy 
db.init_app(app)

db_config = {
    "host": "localhost",
    "user": "root",
    "password": "new_password",
    "database": "referral"
}

try:
    #connection to the database
    conn = mysql.connector.connect(**db_config)
    conn.close()
    database_connected = True
except Exception as e:
    database_connected = False
    print(f'Error connecting to the database: {str(e)}')

# Create the tables if the database connection was successful
if database_connected:
    with app.app_context():
        db.create_all()
    print('Connected to the database successfully!')
else:
    print('Failed to connect to the database.')
    
# Configure Microsoft OAuth settings
oauth = OAuth(app)
oauth.register(
    name='microsoft',
    client_id='4ebb9d1a-110c-4120-ae73-651c63056f8f',
    client_secret='Kxs8Q~qrCWWtTIvry7WuqwLsXLRbfyQoJKeLebpG',
    authorize_url='https://login.microsoftonline.com/e14e73eb-5251-4388-8d67-8f9f2e2d5a46/oauth2/v2.0/authorize',
    token_url='https://login.microsoftonline.com/e14e73eb-5251-4388-8d67-8f9f2e2d5a46/oauth2/v2.0/token',
    client_kwargs={'scope': 'openid email profile'},
)
graph_send_email_url = 'https://graph.microsoft.com/v1.0/me/sendMail'



@app.route('/login')
def login():
    
    state = os.urandom(24)
   
    session['state'] = state
    redirect_uri = url_for('authorize', _external=True)
    return oauth.microsoft.authorize_redirect(redirect_uri, state=state)

@app.route('/authorize')
def authorize():
    try:
        # Get the authorization code
        code = request.args.get('code')

        # Exchange the authorization code for an access token
        token_url = 'https://login.microsoftonline.com/e14e73eb-5251-4388-8d67-8f9f2e2d5a46/oauth2/v2.0/token'
        token_params = {
            'client_id': '4ebb9d1a-110c-4120-ae73-651c63056f8f',
            'client_secret': 'Kxs8Q~qrCWWtTIvry7WuqwLsXLRbfyQoJKeLebpG',
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': url_for('authorize', _external=True)
        }
        token_response = requests.post(token_url, data=token_params)

        if token_response.status_code == 200:
            token_data = token_response.json()
            access_token = token_data.get('access_token')

            # Store the access token in the session
            session['access_token'] = access_token

            
            return redirect(f'http://localhost:3000/work/{access_token}')  
        else:
            return f"Error retrieving access token: {token_response.text}", 400

    except Exception as e:
        print(f"Error during token retrieval: {str(e)}")
        return f"Error: {str(e)}", 500

@app.route('/protected', methods=['POST'])
def protected_route():
    try:
        access_token = request.json.get('access_token')

        if not access_token:
            return 'Access token is missing', 400

        # Define the Microsoft Graph API endpoint to retrieve emails
        graph_api_url = 'https://graph.microsoft.com/v1.0/me/mailFolders/Inbox/messages'

        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
        }

        
        response = requests.get(graph_api_url, headers=headers)

        if response.status_code == 200:
            emails = response.json().get('value', [])
           
            return jsonify(emails)
        else:
            return f'Error retrieving emails: {response.text}', response.status_code

    except Exception as e:
        print(f"Error during email retrieval: {str(e)}")
        return f"Error: {str(e)}", 500


@app.route('/send-email', methods=['POST'])
def send_email():
    try:
        # Get the access token
        access_token = request.json.get('accessToken')

        # Get the email data
        email_data = request.json.get('emailData')
        
        # print(email_data)

        # Extract the email body from the email data
        email_body = email_data.get('body')
        urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', email_body)

        link = False
        if urls:
            link = True

        link_urls = []

        for url in urls:
            token_generate = secrets.token_urlsafe(16)
            modified_url = f'http://localhost:5000/custom-redirect/?original_url={url}&token={token_generate}'
            email_body = email_body.replace(url, modified_url)
            link_urls.append((url, token_generate))

        # Print all the modified links and their respective tokens
        for url, token in link_urls:
            print(f"Link: {url}, Token: {token}")
        # Add the HTML image tag within a valid HTML structure
        tracking_pixel_url = f'https://ca06-103-155-138-209.ngrok-free.app/track-pixel/{token_generate}'
        email_body += f'<p><img src="{tracking_pixel_url}" alt="ahds" width="1" height="1" /></p>'
        # print(email_body)

        
        # Set up the headers for the Microsoft Graph API request
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
        }

        # Construct the request body for sending email
        email_request = {
            "message": {
                "subject": email_data.get('subject'),
                "body": {
                    "contentType": "HTML",
                    "content": f'<html><body>{email_body}</body></html>',
                },
                "toRecipients": [
                    {
                        "emailAddress": {
                            "address": email_data.get('recipientEmail'),
                        }
                    }
                ],
                "isReadReceiptRequested": "true"
            },
            "saveToSentItems": "true",
        }

        response = requests.post(graph_send_email_url, headers=headers, json=email_request)

        # Send a GET request to Microsoft Graph API to get user information
        user_response = requests.get('https://graph.microsoft.com/v1.0/me', headers=headers)
        if user_response.status_code == 200:
            user_info = json.loads(user_response.text)
            current_user_email = user_info.get('mail')  

            # Save email data and current user's email to the database
            email_record = EmailRecord(
                sender_email=current_user_email,
                receiver_email=email_data.get('recipientEmail'),
                # body=email_body,
                link=url,
                read=False,
                link_present=link,
                token=token_generate
            )

            
            db.session.add(email_record)
            db.session.commit()

            return jsonify({'message': 'Email sent successfully'})
        else:
            return f'Error sending email: {user_response.text}', user_response.status_code

    except Exception as e:
        print(f"Error during email sending: {str(e)}")
        return f"Error: {str(e)}", 500

# Route for custom redirection
@app.route('/custom-redirect/')
def custom_redirect():
    # Get the original URL and token from the request query parameters
    original_url = request.args.get('original_url')
    token = request.args.get('token')

    
    link_record = LinkRecord.query.filter_by(token=token).first()

    if link_record:
        
        link_record.link_click = True

        # link_record.open_time=datetime.now

        # Update the number of times the link was clicked
        link_record.number_of_times_link_click += 1


        db.session.commit()
    else:
        # Create a new LinkRecord if it doesn't exist
        email_record = EmailRecord.query.filter_by(token=token).first()
        if email_record:
            link_record = LinkRecord(token=token,link_click=True,number_of_times_link_click=1, email_record_id=email_record.id)
            db.session.add(link_record)
            db.session.commit()

    # Redirect to original URL
    return redirect(original_url)

@app.route('/track-pixel/<token>', methods=['GET'])
def track_pixel(token):
    # Search for the EmailRecord with the given token
    email_record = EmailRecord.query.filter_by(token=token).first()

    if email_record:
        # Mark the email as read
        email_record.read = True
        db.session.commit()

        # Log the tracking event (you can save this data to the database)
        print(f"Email with token {token} has been opened.")

        # Serve a 1x1 transparent pixel
        pixel = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00'
            b'\x00\x00\x00\x00\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00\x01'
            b'\x00\x01\x00\x00\x02\x02\x44\x01\x00'
        )

        response = make_response(pixel)
        response.headers['Content-Type'] = 'image/gif'
        response.headers['Content-Length'] = str(len(pixel))

        return response
    else:
        
        return "Email not found for the given token", 404

@app.route('/get-email-details', methods=['GET'])
def get_email_details():
    # token = request.headers.get('Authorization')
    # print(token)

    email_records = EmailRecord.query.all()
    email_data = []

    for record in email_records:
        link_open_time = None
        link_open_count = None

        if record.link_present and record.link_records:
            link_record = record.link_records[0]
            link_open_time = link_record.open_time
            link_open_count = link_record.number_of_times_link_click

        email_data.append({
            'id': record.id,
            'senderEmail': record.sender_email,
            'receiverEmail': record.receiver_email,
            'link':record.link,
            'mailSentTime': record.Email_send_time.strftime('%Y-%m-%d %H:%M:%S'),
            'linkPresent': record.link_present,
            'mailRead': record.read,
            'linkOpenTime': link_open_time.strftime('%Y-%m-%d %H:%M:%S') if link_open_time else None,
            'linkOpenCount': link_open_count if link_open_count is not None else None  # Set to None if link_open_count is None
        })

    return jsonify(email_data)


if __name__ == '__main__':
    app.run(debug=True)

