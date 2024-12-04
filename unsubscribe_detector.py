import logging
import re
from bs4 import BeautifulSoup
from langdetect import detect
import spacy
from transformers import pipeline

class UnsubscribeDetector:
    """Detects unsubscribe instructions or links within an email message."""
    # Define models for different languages
    classification_models = {
        "en": "roberta-large-mnli",
        "ru": "cointegrated/rubert-tiny"
    }

    # Create pipelines for each classification model
    pipelines = {
        lang: pipeline("zero-shot-classification", model=model)
        for lang, model in classification_models.items()
    }

    # Load SpaCy models for each language
    nlp_models = {
        "en": spacy.load("en_core_web_sm"),
        "ru": spacy.load("ru_core_news_sm")
    }

    def __init__(self):
        pass

    @staticmethod
    def detect_language(text):
        """Detect the language of a given text."""
        try:
            return detect(text)
        except Exception as e:
            logging.error(f"Error detecting language: {e}")
            return "unknown"

    @staticmethod
    def contains_html(text):
        """Check if the text contains HTML tags."""
        return bool(re.search(r'<.*?>', text))

    def detect_unsubscribe_intent(self, email_message):
        """Analyze email body and headers for unsubscribe links."""
        decoded_body = email_message.body
        email_headers = email_message.headers

        # First, check the 'List-Unsubscribe' header
        list_unsubscribe = email_message.get_header('List-Unsubscribe')
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
        lang = self.detect_language(decoded_body)
        logging.debug(f"Detected language: {lang}")
        if lang in self.pipelines:
            # Tokenize and extract sentences from the email body
            nlp = self.nlp_models[lang]
            doc = nlp(decoded_body)
            # Use the appropriate pipeline for the detected language
            classifier = self.pipelines[lang]
            sentences = [sent.text for sent in doc.sents if sent.text.strip()]
            # Search for unsubscribe instructions
            for sentence in sentences:
                cleaned = re.sub(r"(?m)^\s*\n", "", sentence)
                # Define candidate labels based on language
                candidate_labels = {
                    "en": ["unsubscribe", "other"],
                    "ru": ["отписаться", "другое"]
                }
                labels = candidate_labels.get(lang, ["unsubscribe", "other"])
                result = classifier(cleaned, candidate_labels=labels)

                if result['labels'][0] == 'unsubscribe' and result['scores'][0] > 0.8:
                    if self.contains_html(cleaned):
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