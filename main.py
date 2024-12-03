import logging
import time
from urllib.parse import urljoin

from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle
import os.path
import requests
import base64
from bs4 import BeautifulSoup
import spacy
from transformers import pipeline
from langdetect import detect
import re

# Define the API scope
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

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

def detect_language(text):
    """Detect the language of a given text."""
    try:
        return detect(text)
    except Exception as e:
        print(f"Error detecting language: {e}")
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
    print(f"Detected language: {lang}")
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

            print(f"{result}")
            if result['labels'][0] == 'unsubscribe' and result['scores'][0] > 0.8:
                # Parse the sentence as HTML
                sentence_soup = BeautifulSoup(cleaned, 'html.parser')
                for a_tag in sentence_soup.find_all('a', href=True):
                    unsubscribe_link = a_tag['href']
                    print(f"Found unsubscribe link in NLP-detected sentence: {unsubscribe_link}")
                    return unsubscribe_link  # Return the unsubscribe link
                # Search for URLs in the text
                link_match = re.search(r'(https?://\S+)', cleaned)
                if link_match:
                    unsubscribe_link = link_match.group(0)
                    print(f"Found unsubscribe link in text: {unsubscribe_link}")
                    return unsubscribe_link
                else:
                    print("Unsubscribe intent detected, but no link found.")
                    return cleaned  # Return the sentence with the intent
    else:
        print(f"No model available for language: {lang}")

    print("No unsubscribe link found.")
    return None

def fetch_emails(service):
    """Fetch emails and use NLP to identify unsubscribe instructions."""
    results = service.users().messages().list(userId='me', includeSpamTrash=True).execute()
    messages = results.get('messages', [])

    print(f"Found total {len(messages)} emails in the account")

    unsubscribe_emails = []

    for message in messages:
        msg = service.users().messages().get(
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
            print(body_)
            time.sleep(2)
            unsubscribe(body_)
            unsubscribe_emails.append(body_)

    return unsubscribe_emails


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
        logging.info(f"Unsubscribe link is a mailto link: {link}")
        # Implement email sending logic here if desired
        # Be cautious to avoid spamming or violating email policies
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
                    logging.info(f"Found form on unsubscribe page for: {sender}")
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
                    else:
                        logging.warning(f"Form submitted, but could not verify unsubscription for: {sender}")
                else:
                    # No form found; check for confirmation message
                    if 'unsubscribed' in response.text.lower():
                        logging.info(f"Successfully unsubscribed from: {sender}")
                    else:
                        logging.warning(f"No form or confirmation message found for: {sender}")
            else:
                # Non-HTML content
                logging.info(f"Received non-HTML response when unsubscribing from: {sender}")
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

# Test the connection by listing Gmail labels
if __name__ == "__main__":
    service = authenticate_gmail()
    emails_with_unsubscribe = fetch_emails(service)
    print(f"Found {len(emails_with_unsubscribe)} emails with unsubscribe links.")
