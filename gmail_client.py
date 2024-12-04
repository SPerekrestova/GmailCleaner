import base64
import logging
import os
import pickle

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Define the API scope
SCOPES = ['https://mail.google.com/']

class GmailClient:
    """Handles authentication and interactions with the Gmail API."""

    def __init__(self, credentials_file='credentials.json', token_file='token.pickle'):
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.service = self.authenticate_gmail()

    def authenticate_gmail(self):
        """Authenticate the user and return the Gmail API service."""
        creds = None
        if os.path.exists(self.token_file):
            with open(self.token_file, 'rb') as token:
                creds = pickle.load(token)
        # If credentials are not valid, authenticate
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(self.credentials_file, SCOPES)
                creds = flow.run_local_server(port=0)
            # Save credentials for the next run
            with open(self.token_file, 'wb') as token:
                pickle.dump(creds, token)
        return build('gmail', 'v1', credentials=creds)

    def get_messages(self, user_id='me', include_spam_trash=True, max_results=500):
        """Retrieve a list of messages."""
        try:
            results = self.service.users().messages().list(
                userId=user_id, includeSpamTrash=include_spam_trash, maxResults=max_results
            ).execute()
            messages = results.get('messages', [])
            logging.info(f"Found total {len(messages)} emails in the account")
            return messages
        except HttpError as error:
            logging.error(f"An error occurred: {error}")
            return []

    def get_message(self, message_id, user_id='me', format='full'):
        """Retrieve a message by ID."""
        try:
            message = self.service.users().messages().get(
                userId=user_id, id=message_id, format=format
            ).execute()
            return message
        except HttpError as error:
            logging.error(f"An error occurred: {error}")
            return None

    def send_email(self, email_message):
        """Send an email message."""
        try:
            encoded_message = base64.urlsafe_b64encode(email_message.as_bytes()).decode()
            create_message = {'raw': encoded_message}
            send_message = self.service.users().messages().send(
                userId='me', body=create_message
            ).execute()
            logging.info(f"Message sent. ID: {send_message['id']}")
            return send_message
        except HttpError as error:
            logging.error(f"An error occurred: {error}")
            return None

    def get_user_email(self):
        """Get the authenticated user's email address."""
        try:
            profile = self.service.users().getProfile(userId='me').execute()
            return profile.get('emailAddress')
        except HttpError as error:
            logging.error(f"An error occurred: {error}")
            return None