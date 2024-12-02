from flask import Flask, request, jsonify
import spacy
from spacy.matcher import Matcher
import nltk
from nltk.corpus import wordnet, stopwords
from nltk.stem import WordNetLemmatizer
from transformers import pipeline
from flask_cors import CORS
from dateparser import parse
from datetime import datetime, timedelta
import re
import os
from dateutil.parser import parse
from dateutil.parser._parser import ParserError


app = Flask(__name__)
CORS(app)  # Allow CORS

# Ensure NLTK data is downloaded
nltk.download('stopwords')
nltk.download('wordnet')

# Load spaCy model for English
nlp = spacy.load('en_core_web_sm')

# Initialize the NLTK WordNetLemmatizer
lemmatizer = WordNetLemmatizer()

def convert_time_phrases(time_string):
    """
    Convert standard times (e.g., '2:30 pm') and natural language time phrases (e.g., 'half past 3 pm') to 24-hour format.
    """
    time_string = time_string.lower().strip()

    # Match standard time formats (e.g., '2:30 pm', '12:15 am')
    standard_time_match = re.match(r"(\d{1,2}):(\d{2})\s*(am|pm)?", time_string)
    if standard_time_match:
        hour = int(standard_time_match.group(1))
        minute = int(standard_time_match.group(2))
        period = standard_time_match.group(3)

        # Convert to 24-hour format
        if period == "pm" and hour != 12:
            hour += 12
        elif period == "am" and hour == 12:
            hour = 0

        return f"{hour:02d}:{minute:02d}"

    # Match phrases like 'half past 3 pm', 'quarter to 4 am'
    phrase_match = re.search(r"(half past|quarter past|quarter to|o'clock)?\s*(\d{1,2})\s*(am|pm)?", time_string)
    if phrase_match:
        phrase = phrase_match.group(1)
        hour = int(phrase_match.group(2))
        period = phrase_match.group(3)

        # Initialize minutes
        minutes = 0

        # Handle phrases
        if phrase == "half past":
            minutes = 30
        elif phrase == "quarter past":
            minutes = 15
        elif phrase == "quarter to":
            hour -= 1
            if hour < 1:
                hour = 12  # Wrap around midnight/midday
            minutes = 45
        elif phrase == "o'clock":
            minutes = 0

        # Convert to 24-hour format
        if period == "pm" and hour != 12:
            hour += 12
        elif period == "am" and hour == 12:
            hour = 0

        return f"{hour:02d}:{minutes:02d}"

    # If no valid time format is found, return the original string
    return time_string

days_of_week = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']

def get_next_monday(today):
    """Get the Monday of next week from the given date."""
    days_ahead = 0 - today.weekday() + 7
    if days_ahead <= 0:
        days_ahead += 7
    return today + timedelta(days=days_ahead)

def get_first_day_of_next_month(today):
    """Get the first day of next month."""
    next_month = today.month % 12 + 1
    next_year = today.year + (today.month // 12)
    return datetime(next_year, next_month, 1)

def get_next_day_by_name(today, day_name):
    """Get the next specific day from the current date."""
    target_day = days_of_week.index(day_name.lower())
    if target_day is None:
        return None
    days_ahead = target_day - today.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    return today + timedelta(days=days_ahead)

def split_sentences(sentence: str) -> list:
    """Split a sentence by commas or 'and' only if multiple twings are present."""
    # Parse the sentence using spaCy to extract entities
    doc = nlp(sentence)
    
    # Find all time entities
    times = [ent.text for ent in doc.ents if ent.label_ == "TwE"]

    # If there are multiple time entities, split the sentence
    if len(times) > 1:
        parts = re.split(r',|\band\b', sentence)
        return [part.strip() for part in parts if part.strip()]
    
    # If only one or no time found, return the sentence as a single item list
    return [sentence.strip()]

# Load the trained spaCy model
MODEL_PATH = "Replace with trained_model path"  # Replace with your model's path
nlp = spacy.load(MODEL_PATH)


def get_main_part(sentence):
    """Simplified summarization function for extracting the main event."""
    # Implement your summarization logic here; for now, returning the sentence as-is.
    return sentence if sentence else "No event"


def extract_event_details(sentence, current_date=None):
    """Extract event details from the sentence."""
    doc = nlp(sentence)
    dates = [ent.text for ent in doc.ents if ent.label_ == "DATE"]
    times = [ent.text for ent in doc.ents if ent.label_ == "TIME"]
    
    today = datetime.today()
    formatted_dates = []
    formatted_times = times  # Use the extracted times directly

    # Summarize the event
    summarized_event = get_main_part(sentence)
    doc= nlp(sentence)

    for ent in doc.ents:
        if ent.label_=="EVENT":
            summarized_event=ent.text
    print(summarized_event)
    # Flag cancellations

    for date_str in dates:
        parsed_date = None
        try:
            if "next week" in date_str.lower():
                parsed_date = get_next_monday(today)
            elif "next month" in date_str.lower():
                parsed_date = get_first_day_of_next_month(today)
            elif any(day in date_str.lower() for day in days_of_week):
                for day_name in days_of_week:
                    if day_name in date_str.lower():
                        parsed_date = get_next_day_by_name(today, day_name)
                        break
            else:
                parsed_date = parse(date_str, fuzzy=True)

            # Append parsed date if valid
            if parsed_date:
                formatted_dates.append((date_str, parsed_date.strftime("%d-%m-%y")))
                current_date = parsed_date.strftime("%d-%m-%y")

        except Exception as e:
            print(f"Error parsing date '{date_str}': {e}")

    formatted_times = [convert_time_phrases(t) for t in times]

    print(formatted_dates)
    if "cancelled" in sentence.lower():
        summarized_event += ": Cancelled"

    # Set default date if no date was found
    if not formatted_dates:
        current_date = current_date or today.strftime("%d-%m-%y")
        formatted_dates.append((None, current_date))

    # Handle edge cases
    if summarized_event == "No event" and not formatted_times:
        return None, current_date
    elif not formatted_dates and not formatted_times:
        return None, current_date
    elif not formatted_times:
        return None, current_date
    # Prepare the result
    result = {
        "Event": summarized_event,
        "Date":', '.join([d[1] for d in formatted_dates]),
        "Time": ', '.join(formatted_times) if formatted_times else ""
    }
    return result, current_date



def process_paragraph(paragraph: str) -> list:
    """Process a paragraph and extract event details from each sentence."""
    # Split paragraph by periods, and handle new lines as sentence delimiters
    sentences = [sentence.strip() + '.' for sentence in paragraph.split('.') if sentence.strip()]
    
    # Initialize current_date to None for the first sentence
    current_date = None
    schedule = []
    # print(sentences)
    # Extract event details from each sentence directly
    for sentence in sentences:
        # Use the split_sentences function to get segments
        split_sentences_list = split_sentences(sentence)
        for seg in split_sentences_list:
            event_details, current_date = extract_event_details(seg, current_date) 
             # Pass current_date and receive updated current_date
            # print(event_details)
            if event_details:  # Append only if event details are valid
                schedule.append(event_details)

    # Ensure each event has consistent fields
    return [
        {
            "Event": item.get("Event", "Unknown Event"),
            "Date": item.get("Date", "No Date"),
            "Time": item.get("Time", "No Time")
        }
        for item in schedule if item is not None
    ]

def summarize_text(text):
    summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
    
    # Calculate the lengths
    text_length = len(text.split())  # Number of words in the text
    
    target_length = int(text_length * 0.4)  # 40% of original length
    
    # Set minimum and maximum lengths for summarization
    max_length = max(target_length, 50)  # Ensure max_length is not too small
    min_length = max(target_length // 2, 20)  # Ensure min_length is not too small
    
    # Generate summary
    summary = summarizer(text, max_length=max_length, min_length=min_length, do_sample=False)
    return summary[0]['summary_text']



# Flask routes
@app.route('/summarize', methods=['POST'])
def summarize():
    data = request.json
    text = data.get('text')
    
    # Check if text was provided
    if not text:
        return jsonify({"error": "No text provided"}), 400
    
    # Fetch email bodies stored in MongoDB and deduplicate
    emails = collection.find({}, {"_id": 0, "body": 1})
    email_bodies = list(set([email["body"] for email in emails]))  # Deduplicate emails
    
    # Combine the provided text with the email bodies
    combined_text = text + " ".join(email_bodies)  # Combine user-provided text and email bodies
    
    # Generate summary for the combined text
    summary = summarize_text(combined_text)
    
    return jsonify({"summary": summary})


@app.route('/events', methods=['POST'])
def events():
    """Endpoint to extract event details from the provided text."""
    data = request.json
    text = data.get('text', '')

    # emails=fetch_emails()

    
    # Fetch email bodies from MongoDB and deduplicate
    emails = collection.find({}, {"_id": 0, "body": 1})  # Retrieve email bodies from MongoDB
    email_bodies = list(set([email["body"] for email in emails]))  # Deduplicate emails

    if not text and not email_bodies:
        return jsonify({"error": "No text provided"}), 400
    
    
    # Combine the provided text with the email bodies
    if email_bodies:
        combined_text = text + " " + " ".join(email_bodies)  # Combine the input text with email bodies
    else:
        combined_text = text

    try:
        # event_details = process_paragraph(text)
        event_details = process_paragraph(combined_text)  # Process the combined text
        return jsonify({"events": event_details})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


import imaplib
import email
from bs4 import BeautifulSoup
# import credentials  # Your credentials file
from pymongo import MongoClient


# MongoDB connection setup
client = MongoClient("mongodb://localhost:27017/")
db = client["emailDB"]
collection = db["emails"]

import traceback

from bson import ObjectId
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow  # <-- Import this
from flask import jsonify
import os
import base64

# Assuming your MongoDB collection is already initialized as 'collection'
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/calendar.events',
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/calendar.readonly',
    'https://www.googleapis.com/auth/userinfo.profile',
    'https://www.googleapis.com/auth/userinfo.email',
    'openid'
]




@app.route('/fetch-emails', methods=['GET'])
def fetch_emails():
    """Fetches emails using Gmail API and stores them in MongoDB."""
    try:
        creds = None
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
                creds = flow.run_local_server(port=5001,access_type='offline', prompt='consent')
            with open('token.json', 'w') as token:
                token.write(creds.to_json())

        # Build the Gmail API service
        service = build('gmail', 'v1', credentials=creds)

        # Fetch the user's profile to get their email address
        profile = service.users().getProfile(userId='me').execute()
        user_email = profile.get('emailAddress', 'Unknown')

        # Fetch important emails
        results = service.users().messages().list(userId='me', labelIds=['IMPORTANT']).execute()
        messages = results.get('messages', [])
        emails = []

        if not messages:
            print('No important messages found.')
        else:
            for message in messages:
                msg = service.users().messages().get(userId='me', id=message['id']).execute()
                message_id = msg['id']
                subject = ''
                from_ = ''
                body = ''

                # Get email headers
                for header in msg['payload']['headers']:
                    if header['name'] == 'From':
                        from_ = header['value']
                    if header['name'] == 'Subject':
                        subject = header['value']

                # Get email body
                if 'parts' in msg['payload']:
                    for part in msg['payload']['parts']:
                        if part['mimeType'] == 'text/plain':
                            body = part['body'].get('data', '')
                            body = base64.urlsafe_b64decode(body).decode()

                email_data = {
                    "message_id": message_id,
                    "subject": subject,
                    "from": from_,
                    "body": body
                }

                # Insert or update email data in MongoDB
                collection.update_one(
                    {"message_id": message_id},
                    {"$set": email_data},
                    upsert=True
                )

                emails.append(email_data)

        return jsonify({"emails": emails, "user_email": user_email})

    except HttpError as error:
        print(f"An error occurred: {error}")
        return jsonify({"error": f"An error occurred: {error}"}), 500

@app.route('/sign-out', methods=['POST'])
def sign_out():
    """Clears saved credentials and signs the user out."""
    try:
        if os.path.exists('token.json'):
            os.remove('token.json')
        return jsonify({"message": "Signed out successfully"}), 200
    except Exception as error:
        return jsonify({"error": f"An error occurred: {error}"}), 500

from datetime import datetime, timedelta
import re
from datetime import datetime, timedelta
from flask import jsonify
@app.route('/add-events', methods=['POST'])
def add_events():
    """Adds events to the user's Google Calendar."""
    try:
        # Load credentials (omitting the token management for brevity)
        creds = None
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                return jsonify({"error": "User is not signed in."}), 401

        # Build the Calendar API service
        service = build('calendar', 'v3', credentials=creds)

        # Get events from request body
        events = request.json.get('events', [])
        if not events:
            return jsonify({"error": "No events provided"}), 400

        for event in events:
            title = event.get('title', 'Untitled Event')
            raw_date = event.get('date', '')  # Format: DD-MM-YY
            raw_time = event.get('time', '').strip().lower()  # Format: HH:MM or other variations
            raw_end_time = None

            # Validate and parse date
            try:
                date = datetime.strptime(raw_date, "%d-%m-%y").strftime("%Y-%m-%d")
            except ValueError:
                return jsonify({"error": f"Invalid date format: {raw_date}"}), 400

            # Remove any alphabetical string from the time input and extract valid times
            valid_time_format = re.findall(r'\d{2}:\d{2}', raw_time)
            if valid_time_format:
                # If multiple valid time formats are found, assume first one is start time, second is end time
                if len(valid_time_format) == 2:
                    start_time_str, end_time_str = valid_time_format
                else:
                    start_time_str = valid_time_format[0]
                    end_time_str = start_time_str  # If only one time provided, use the same for end time
                try:
                    start_time = datetime.strptime(f"{date} {start_time_str}", "%Y-%m-%d %H:%M")
                    end_time = datetime.strptime(f"{date} {end_time_str}", "%Y-%m-%d %H:%M")
                except ValueError:
                    return jsonify({"error": f"Invalid time format: {start_time_str} or {end_time_str}"}), 400
            else:
                return jsonify({"error": f"Invalid time format: {raw_time}"}), 400

            # Prepare start and end for Google Calendar
            if start_time:
                start = {"dateTime": start_time.isoformat(), "timeZone": "UTC"}
                end = {"dateTime": end_time.isoformat(), "timeZone": "UTC"} if end_time else start
            else:
                start = end = {"date": date}  # All-day event

            # Create the event
            event_body = {"summary": title, "start": start, "end": end}
            service.events().insert(calendarId="primary", body=event_body).execute()

        return jsonify({"message": "Events added successfully"}), 200

    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)
