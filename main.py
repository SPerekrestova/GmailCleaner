import logging
import time
from urllib.parse import urljoin, urlparse, parse_qs, unquote, urlsplit
import sys

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from email.message import EmailMessage
import pickle
import os.path
import requests
import base64
from bs4 import BeautifulSoup
import spacy
from sympy import true
from transformers import pipeline
from langdetect import detect
import re

# Define the API scope
SCOPES = ['https://mail.google.com/']

# Define models for different languages
classificationModels = {
    "en": "roberta-large-mnli",
    "ru": "cointegrated/rubert-tiny"
}

# Create pipelines for each classification model
pipelines = {lang: pipeline("zero-shot-classification", model=model) for lang, model in classificationModels.items()}

nlpModels = {
    "en": spacy.load("en_core_web_sm"),
    "ru": spacy.load("ru_core_news_sm")
}

logging.basicConfig(stream=sys.stdout, level=logging.INFO)

gmailService = None

def detect_language(text):
    """Detect the language of a given text."""
    try:
        return detect(text)
    except Exception as e:
        logging.error(f"Error detecting language: {e}")
        return "unknown"

def detect_unsubscribe_intent(decoded_body, email_headers):
    """Analyze email body and headers for unsubscribe links."""
    # First, check the 'List-Unsubscribe' header
    list_unsubscribe = next((h['value'] for h in email_headers if h['name'].lower() == 'list-unsubscribe'), None)
    if list_unsubscribe:
        # Extract URLs or mailto links from the header
        links = re.findall(r'<(.*?)>', list_unsubscribe)
        if links:
            return links[0]  # Return the first unsubscribe link found

    # Parse the HTML content
    soup = BeautifulSoup(decoded_body, 'html.parser')
    # Look for 'unsubscribe' links
    unsubscribe_links = []
    for a_tag in soup.find_all('a', href=True):
        link_text = a_tag.get_text().lower()
        link_href = a_tag['href'].lower()
        if 'unsubscribe' in link_text or 'unsubscribe' in link_href:
            unsubscribe_links.append(a_tag['href'])

    if unsubscribe_links:
        return unsubscribe_links[0]  # Return the first unsubscribe link found

    # Proceed with NLP-based intent detection
    lang = detect_language(decoded_body)
    logging.debug(f"Detected language: {lang}")
    if lang in pipelines:
        # Tokenize and extract sentences from the email body
        nlp = nlpModels[lang]
        doc = nlp(decoded_body)
        # Use the appropriate pipeline for the detected language
        classifier = pipelines[lang]
        sentences = [sent.text for sent in doc.sents if sent.text.strip()]
        # Search for unsubscribe instructions
        for sentence in sentences:
            cleaned = re.sub(r"(?m)^\s*\n", "", sentence)
            # Use a transformer-based model for classification
            # Define candidate labels based on language
            candidate_labels = {
                "en": ["unsubscribe", "other"],
                "ru": ["отписаться", "другое"]
            }
            labels = candidate_labels.get(lang, ["unsubscribe", "other"])
            result = classifier(cleaned, candidate_labels=labels)

            if result['labels'][0] == 'unsubscribe' and result['scores'][0] > 0.8:
                if contains_html(cleaned):
                    # Parse the sentence as HTML
                    sentence_soup = BeautifulSoup(cleaned, 'html.parser')
                    for a_tag in sentence_soup.find_all('a', href=True):
                        unsubscribe_link = a_tag['href']
                        logging.debug(f"Found unsubscribe link in NLP-detected sentence: {unsubscribe_link}")
                        return unsubscribe_link  # Return the unsubscribe link
                else:
                    # Search for URLs in the text
                    link_match = re.search(r'(https?://\S+)', cleaned)
                    if link_match:
                        unsubscribe_link = link_match.group(0)
                        logging.debug(f"Found unsubscribe link in text: {unsubscribe_link}")
                        return unsubscribe_link
                    else:
                        logging.debug("Unsubscribe intent detected, but no link found.")
                        return cleaned  # Return the sentence with the intent
    else:
        logging.error(f"No model available for language: {lang}")

    logging.warning("No unsubscribe link found.")
    return None

def fetch_emails():
    """Fetch emails and use NLP to identify unsubscribe instructions."""
    results = gmailService.users().messages().list(userId='me', includeSpamTrash=True, maxResults=500).execute()
    messages = results.get('messages', [])

    logging.info(f"Found total {len(messages)} emails in the account")

    unsubscribed_emails = 0

    for message in messages:
        msg = gmailService.users().messages().get(
            userId='me',
            id=message['id'],
            format='full'
        ).execute()

        payload = msg.get('payload', {})
        headers = payload.get('headers', [])

        # Extract sender
        sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), None)

        # Extract email subject
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')

        # Extract email body
        def get_email_body(payload):
            """Recursively retrieve the email body from the payload."""
            if 'body' in payload and payload['body'].get('data'):
                return payload['body']['data']
            elif 'parts' in payload:
                for part in payload['parts']:
                    body_data = get_email_body(part)
                    if body_data:
                        return body_data
            return None

        body_data = get_email_body(payload)

        if body_data:
            # Decode the body from base64
            decoded_body = base64.urlsafe_b64decode(body_data).decode('utf-8', errors='ignore')
        else:
            decoded_body = ''

        # Use NLP to detect unsubscribe instructions
        unsubscribe_instruction = detect_unsubscribe_intent(decoded_body, headers)

        if unsubscribe_instruction:
            body_ = {
                'sender': sender,
                'subject': subject,
                'unsubscribe_instruction': unsubscribe_instruction
            }
            time.sleep(2)
            logging.debug(body_)
            if unsubscribe(body_):
                unsubscribed_emails += 1

    return unsubscribed_emails


def unsubscribe(email):
    """Visit unsubscribe links to automate unsubscribing."""
    session = requests.Session()
    # Set headers to mimic a real browser
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) ' \
                      'AppleWebKit/537.36 (KHTML, like Gecko) ' \
                      'Chrome/86.0.4240.183 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
    })

    sender = email.get('sender')
    link = email.get('unsubscribe_instruction')
    logging.info(f"Attempting to unsubscribe from: {sender}")

    if not link:
        logging.warning(f"No unsubscribe link found for: {sender}")
        return

    # Handle 'mailto:' links
    if link.startswith('mailto:'):
        logging.debug(f"Unsubscribe link is a mailto link: {link}")
        try:
            parsed_link = urlsplit(link)
            to_email = parsed_link.path.replace('mailto:', '').strip()
            send_unsubscribe_email(parsed_link, to_email)
            logging.info(f"Unsubscribe email sent for: {sender}")
        except Exception as e:
            logging.error(f"Error sending unsubscribe email for {sender}: {e}")
        return

    # Handle HTTP/HTTPS links
    try:
        # Send initial request
        response = session.get(link, allow_redirects=True, timeout=10)
        logging.debug(f"GET {link} - Status code: {response.status_code}")

        # Check for successful response
        if response.status_code == 200:
            # Parse the response content
            content_type = response.headers.get('Content-Type', '')
            if 'text/html' in content_type:
                soup = BeautifulSoup(response.text, 'html.parser')

                # Look for forms to submit
                form = soup.find('form')
                if form:
                    logging.debug(f"Found form on unsubscribe page for: {sender}")
                    form_action = form.get('action')
                    form_method = form.get('method', 'get').lower()
                    form_inputs = form.find_all(['input', 'select', 'textarea'])

                    # Build form data
                    form_data = {}
                    for input_element in form_inputs:
                        name = input_element.get('name')
                        if not name:
                            continue
                        value = input_element.get('value', '')
                        input_type = input_element.get('type', '').lower()

                        # Handle checkboxes and radio buttons
                        if input_type in ['checkbox', 'radio']:
                            if input_element.has_attr('checked'):
                                form_data[name] = value
                        else:
                            # Provide email address if requested
                            if 'email' in name.lower():
                                form_data[name] = email.get('email_address', '')
                            else:
                                form_data[name] = value

                    # Construct form URL
                    form_url = urljoin(response.url, form_action)

                    # Submit the form
                    if form_method == 'post':
                        form_response = session.post(form_url, data=form_data)
                    else:
                        form_response = session.get(form_url, params=form_data)
                    logging.debug(f"{form_method.upper()} {form_url} - Status code: {form_response.status_code}")

                    # Verify unsubscription
                    if form_response.status_code == 200 and 'unsubscribed' in form_response.text.lower():
                        logging.info(f"Successfully unsubscribed from: {sender}")
                        return true
                    else:
                        logging.warning(f"Form submitted, but could not verify unsubscription for: {sender}")
                else:
                    # No form found; check for confirmation message
                    if 'unsubscribed' in response.text.lower():
                        logging.info(f"Successfully unsubscribed from: {sender}")
                        return true
                    else:
                        logging.warning(f"No form or confirmation message found for: {sender}")
            else:
                # Non-HTML content
                logging.debug(f"Received non-HTML response when unsubscribing from: {sender}")
        else:
            logging.warning(f"Failed to access unsubscribe link for: {sender} - Status code: {response.status_code}")

    except requests.exceptions.RequestException as e:
        logging.error(f"Error unsubscribing from {sender}: {e}")

    # Respectful delay between requests
    time.sleep(2)

def authenticate_gmail():
    """Authenticate the user and return the Gmail API service."""
    creds = None
    # Check if token.pickle exists (stored credentials)
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If credentials are not valid, authenticate
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    return build('gmail', 'v1', credentials=creds)

def send_unsubscribe_email(parsed_link, to_email):
    try:
        query_params = parse_qs(parsed_link.query)

        # Extract subject and body, handling URL encoding
        subject = query_params.get('subject', [''])[0]
        body = query_params.get('body', [''])[0]
        subject = unquote(subject)
        body = unquote(body)

        # Construct the email message
        msg = EmailMessage()
        msg['From'] = gmailService.users().getProfile(userId='me').execute().get('emailAddress')
        msg['To'] = to_email
        msg['Subject'] = subject if subject else 'Unsubscribe Request'
        msg.set_content(body if body else 'Please unsubscribe me from your mailing list.')

        # encoded message
        encoded_message = base64.urlsafe_b64encode(msg.as_bytes()).decode()

        create_message = {"raw": encoded_message}
        # pylint: disable=E1101
        send_message = (
            gmailService.users()
            .messages()
            .send(userId="me", body=create_message)
            .execute()
        )

        logging.debug(f'Message Id: {send_message["id"]}')
    except HttpError as error:
        logging.error(f"An error occurred: {error}")
        send_message = None

    return send_message

def contains_html(text):
    """Check if the text contains HTML tags."""
    return bool(re.search(r'<.*?>', text))

# Test the connection by listing Gmail labels
if __name__ == "__main__":
    gmailService = authenticate_gmail()
    successfully_unsubscribed = fetch_emails()
    logging.info(f"Successfully unsubscribed from {successfully_unsubscribed} junk emails.")
