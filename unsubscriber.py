import logging
import time
from email.message import EmailMessage
from urllib.parse import urljoin, parse_qs, unquote, urlsplit

import requests
from bs4 import BeautifulSoup
from googleapiclient.errors import HttpError
from requests.exceptions import RequestException


class Unsubscriber:
    """Automates the process of unsubscribing from emails."""

    def __init__(self, gmail_client):
        self.gmail_client = gmail_client

    def unsubscribe(self, email_message, unsubscribe_instruction):
        """Visit unsubscribe links to automate unsubscribing."""
        session = requests.Session()
        # Set headers to mimic a real browser
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/86.0.4240.183 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
        })

        sender = email_message.sender
        link = unsubscribe_instruction
        logging.info(f"Attempting to unsubscribe from: {sender}")

        if not link:
            logging.warning(f"No unsubscribe link found for: {sender}")
            return False

        # Handle 'mailto:' links
        if link.startswith('mailto:'):
            logging.debug(f"Unsubscribe link is a mailto link: {link}")
            try:
                parsed_link = urlsplit(link)
                to_email = parsed_link.path.replace('mailto:', '').strip()
                self.send_unsubscribe_email(parsed_link, to_email)
                logging.info(f"Unsubscribe email sent for: {sender}")
                return True
            except Exception as e:
                logging.error(f"Error sending unsubscribe email for {sender}: {e}")
            return False

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
                                    form_data[name] = email_message.email_address or ''
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
                            return True
                        else:
                            logging.warning(f"Form submitted, but could not verify unsubscription for: {sender}")
                    else:
                        # No form found; check for confirmation message
                        if 'unsubscribed' in response.text.lower():
                            logging.info(f"Successfully unsubscribed from: {sender}")
                            return True
                        else:
                            logging.warning(f"No form or confirmation message found for: {sender}")
                else:
                    # Non-HTML content
                    logging.debug(f"Received non-HTML response when unsubscribing from: {sender}")
            else:
                logging.warning(f"Failed to access unsubscribe link for: {sender} - Status code: {response.status_code}")

        except RequestException as e:
            logging.error(f"Error unsubscribing from {sender}: {e}")

        # Respectful delay between requests
        time.sleep(2)
        return False

    def send_unsubscribe_email(self, parsed_link, to_email):
        """Send an unsubscribe email if the link is a mailto link."""
        try:
            query_params = parse_qs(parsed_link.query)

            # Extract subject and body, handling URL encoding
            subject = query_params.get('subject', [''])[0]
            body = query_params.get('body', [''])[0]
            subject = unquote(subject)
            body = unquote(body)

            # Construct the email message
            msg = EmailMessage()
            msg['From'] = self.gmail_client.get_user_email()
            msg['To'] = to_email
            msg['Subject'] = subject if subject else 'Unsubscribe Request'
            msg.set_content(body if body else 'Please unsubscribe me from your mailing list.')

            # Send the email
            self.gmail_client.send_email(msg)
        except HttpError as error:
            logging.error(f"An error occurred: {error}")