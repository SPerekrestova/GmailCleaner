import base64

class EmailMessageWrapper:
    """Represents an email message with methods to parse content."""

    def __init__(self, message_data):
        self.message_data = message_data
        self.payload = message_data.get('payload', {})
        self.headers = self.payload.get('headers', [])
        self.sender = self.get_header('From')
        self.subject = self.get_header('Subject', default='No Subject')
        self.body = self.get_body()
        self.email_address = None  # Placeholder for user's email address if needed

    def get_header(self, name, default=None):
        """Retrieve a header value by name."""
        for header in self.headers:
            if header['name'].lower() == name.lower():
                return header['value']
        return default

    def get_body(self):
        """Extract and decode the email body."""
        body_data = self._get_body_data(self.payload)
        if body_data:
            decoded_body = base64.urlsafe_b64decode(body_data).decode('utf-8', errors='ignore')
            return decoded_body
        else:
            return ''

    def _get_body_data(self, payload):
        """Recursively retrieve the email body data from the payload."""
        if 'body' in payload and payload['body'].get('data'):
            return payload['body']['data']
        elif 'parts' in payload:
            for part in payload['parts']:
                body_data = self._get_body_data(part)
                if body_data:
                    return body_data
        return None