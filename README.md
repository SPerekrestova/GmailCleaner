# Automated Email Unsubscriber

The **Automated Email Unsubscriber** is a Python project designed to help you automatically unsubscribe from unwanted emails in your Gmail account. It uses the Gmail API for secure access, Natural Language Processing (NLP) for analyzing emails, and automation techniques to process unsubscribe requests.

---

## Table of Contents
- [Features](#features)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Usage](#usage)
- [Dependencies](#dependencies)
- [Potential Issues and Solutions](#potential-issues-and-solutions)
- [License](#license)
- [Acknowledgments](#acknowledgments)
- [Contact](#contact)

---

## Features
- **Gmail API Integration**: Secure OAuth 2.0 authentication to connect to Gmail.
- **Email Parsing**: Extracts sender, subject, body, and headers from emails.
- **Unsubscribe Detection**: Detects unsubscribe links or instructions using NLP (supports English and Russian).
- **Automated Unsubscription**: Automates the process of visiting unsubscribe links or sending unsubscribe emails.
- **Language Detection**: Identifies the email's language to apply appropriate NLP models.
- **Respectful Request Handling**: Implements delays to avoid overwhelming servers.

---

## Project Structure
```
automated-email-unsubscriber/
├── email_message_wrapper.py    # Parses email messages.
├── gmail_client.py             # Handles Gmail API interactions.
├── main.py                     # Main script to run the program.
├── README.md                   # This README file.
├── requirements.txt            # Python dependencies list.
├── unsubscribe_detector.py     # Detects unsubscribe links.
├── unsubscriber.py             # Automates the unsubscription process.
└── utils.py                    # Utility functions.
```

---

## Prerequisites
- **Python**: Version 3.8 or higher.
- **Google Account**: A Gmail account with Gmail API access enabled.
- **Internet Connection**: Required for downloading models and API access.

---

## Installation
1. **Clone the Repository**:
    ```bash
    git clone https://github.com/yourusername/automated-email-unsubscriber.git
    cd automated-email-unsubscriber
    ```

2. **Create a Virtual Environment** (Optional but recommended):
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3. **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4. **Download SpaCy Language Models**:
    ```bash
    python -m spacy download en_core_web_sm
    python -m spacy download ru_core_news_sm
    ```

5. **Set Up Google API Credentials**:
    - Enable Gmail API:
        1. Go to the [Google Cloud Console](https://console.cloud.google.com).
        2. Create a new project or select an existing one.
        3. Navigate to **APIs & Services > Library**.
        4. Search for "Gmail API" and click **Enable**.
    - Create OAuth 2.0 Credentials:
        1. Navigate to **APIs & Services > Credentials**.
        2. Click **Create Credentials > OAuth client ID**.
        3. Select "Desktop app" as the application type.
        4. Download the `credentials.json` file.
        5. Place the `credentials.json` file in the project directory.

---

## Usage
1. **Authenticate with Gmail**:
    - Run the script for the first time:
      ```bash
      python main.py
      ```
    - A browser window will open for Google account login. Grant the necessary permissions. Authentication tokens will be saved in `token.pickle` for future use.

2. **Run the Script**:
    ```bash
    python main.py
    ```
    The script will:
    - Fetch emails from your Gmail account.
    - Detect unsubscribe instructions.
    - Attempt to unsubscribe from unwanted emails.
    - Log the results in the console.

3. **Monitor the Output**:
    - Check the console for details about:
        - Emails processed.
        - Unsubscribe links found.
        - Unsubscription attempts and their success status.

---

## Dependencies
The dependencies are listed in `requirements.txt`:
- `beautifulsoup4==4.12.2`
- `google-api-python-client==2.94.0`
- `google-auth-httplib2==0.1.0`
- `google-auth-oauthlib==1.0.0`
- `langdetect==1.0.9`
- `requests==2.31.0`
- `spacy==3.6.1`
- `transformers==4.33.3`

Install them with:
```bash
pip install -r requirements.txt
```

---

## Potential Issues and Solutions

### SSL Warning
- **Warning Message**:
  ```
  NotOpenSSLWarning: urllib3 v2 only supports OpenSSL 1.1.1+, currently the 'ssl' module is compiled with 'LibreSSL 2.8.3'
  ```
- **Cause**: Python’s SSL module is compiled with an older LibreSSL version.
- **Solutions**:
    1. Upgrade SSL Libraries:
        - Install OpenSSL 1.1.1+ and recompile Python with the updated version.
    2. Temporarily downgrade `urllib3`:
        ```bash
        pip install 'urllib3<2'
        ```

### Model Downloads
- **Issue**: NLP models fail to download.
- **Solution**:
    - Ensure a stable internet connection.
    - Retry downloading or manually download the models using SpaCy's CLI.

---

## License
This project is licensed under the [MIT License](LICENSE).

---

## Acknowledgments
- **Google Gmail API**: For providing access to Gmail functionalities.
- **SpaCy**: For NLP capabilities.
- **Hugging Face Transformers**: For zero-shot classification models.
- **Beautiful Soup**: For parsing HTML content.

---

## Contact
For questions or suggestions, reach out to:
- **Svetlana Perekrestova**  
  Email: [svetlana.perekrestova2@gmail.com](mailto:svetlana.perekrestova2@gmail.com)
