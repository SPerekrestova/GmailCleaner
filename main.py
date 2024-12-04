import logging
import sys
import time
from gmail_client import GmailClient
from email_message_wrapper import EmailMessageWrapper
from unsubscribe_detector import UnsubscribeDetector
from unsubscriber import Unsubscriber

# Configure logging
logging.basicConfig(stream=sys.stdout, level=logging.INFO)

def main():
    gmail_client = GmailClient()
    messages = gmail_client.get_messages(max_results=10)
    unsubscribe_detector = UnsubscribeDetector()
    unsubscriber = Unsubscriber(gmail_client)
    successfully_unsubscribed = 0

    for message_info in messages:
        message_data = gmail_client.get_message(message_info['id'])
        if not message_data:
            continue
        email_message = EmailMessageWrapper(message_data)
        unsubscribe_instruction = unsubscribe_detector.detect_unsubscribe_intent(email_message)
        if unsubscribe_instruction:
            time.sleep(2)  # Respectful delay
            if unsubscriber.unsubscribe(email_message, unsubscribe_instruction):
                successfully_unsubscribed += 1

    logging.info(f"Successfully unsubscribed from {successfully_unsubscribed} junk emails.")

if __name__ == "__main__":
    main()