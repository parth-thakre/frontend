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


app = Flask(__name__)
CORS(app)  # Allow CORS

# Ensure NLTK data is downloaded
nltk.download('stopwords')
nltk.download('wordnet')

# Load spaCy model for English
nlp = spacy.load('en_core_web_sm')

# Initialize the NLTK WordNetLemmatizer
lemmatizer = WordNetLemmatizer()

# Define a list of priority words and their corresponding noun forms
priority_words = {
    "meet": "meeting",
    "submit": "submission",
    "present": "presentation",
    "deadline": "deadline",
    "plan": "planning",
    "report": "report",
    "discuss": "discussion",
    "call": "call",
    "sync": "sync",
    "launch": "launch",
    "lecture": "lecture",
    "class": "class",
    "session": "session",
    "break":"break",
    "workshop":"workshop"
}

# Initialize Matcher
matcher = Matcher(nlp.vocab)

# Define patterns for event-related phrases
event_patterns = [
    [{"POS": "NOUN"}, {"POS": "NOUN", "OP": "?"}],  # Noun + Optional Noun
    [{"POS": "ADJ"}, {"POS": "NOUN"}],              # Adjective + Noun
    [{"POS": "VERB"}, {"POS": "NOUN", "OP": "?"}],  # Verb + Optional Noun
    [{"POS": "VERB"}, {"POS": "ADP", "OP": "?"}, {"POS": "NOUN"}],  # Verb + Optional Preposition + Noun
    [{"POS": "NOUN"}, {"POS": "ADP"}, {"POS": "NOUN"}]  # Noun + Preposition + Noun
]
matcher.add("EVENT_PATTERN", event_patterns)

def convert_time_phrases(time_string):
    """Convert time phrases like 'half past 3' or '3 o'clock' into 24-hour format."""
    time_string = time_string.lower()

    # Dictionary for common time phrases
    time_conversions = {
        "half past": "30",  # "half past 3" => "3:30"
        "quarter past": "15",
        "quarter to": "-15",  # "quarter to 4" => "3:45"
        "o'clock": ":00"
    }

    # Regex to find time expressions
    time_pattern = r"(\d{1,2})(\s*:\s*\d{1,2})?\s*(am|pm)?"

    # Replace time phrases with standard numeric time representations
    for phrase, replacement in time_conversions.items():
        if phrase in time_string:
            time_string = time_string.replace(phrase, replacement)

    # Handle specific cases like "quarter to"
    if "quarter to" in time_string:
        match = re.search(r"(\d{1,2})", time_string)
        if match:
            hour = int(match.group(1)) - 1
            time_string = re.sub(r"quarter to \d{1,2}", f"{hour}:45", time_string)

    # Final conversion to 24-hour time format
    match = re.search(time_pattern, time_string)
    if match:
        hour = int(match.group(1))
        minute = match.group(2) or ":00"
        period = match.group(3)

        if period == "pm" and hour != 12:
            hour += 12
        elif period == "am" and hour == 12:
            hour = 0

        return f"{hour:02d}{minute}"

    return time_string

def convert_verbs_to_nouns(text):
    """ Convert verbs to nouns and prioritize certain words. """
    doc = nlp(text)
    nouns = [token.text for token in doc if token.pos_ == "NOUN"]
    verbs = [token.text for token in doc if token.pos_ == "VERB"]

    for word, noun_form in priority_words.items():
        if word in text.lower():
            return noun_form

    for verb in verbs:
        verb_base_form = lemmatizer.lemmatize(verb, 'v')
        if verb_base_form in priority_words:
            return priority_words[verb_base_form]

    if nouns:
        return ' '.join(nouns)

    if verbs:
        verb = verbs[0]
        noun_form = lemmatizer.lemmatize(verb, 'n')
        return noun_form if noun_form != verb else verb + "ing"

    return text


days_of_week = {
    'monday': 0, 'tuesday': 1, 'wednesday': 2,
    'thursday': 3, 'friday': 4, 'saturday': 5, 'sunday': 6
}

def get_next_monday(today):
    """ Get the Monday of next week from the given date """
    days_ahead = 0 - today.weekday() + 7
    if days_ahead <= 0:
        days_ahead += 7
    return today + timedelta(days_ahead)

def get_first_day_of_next_month(today):
    """ Get the first day of next month """
    next_month = today.month % 12 + 1
    next_year = today.year + (today.month // 12)
    return datetime(next_year, next_month, 1)

def get_next_day_by_name(today, day_name):
    """ Get the next specific day from the current date """
    target_day = days_of_week.get(day_name.lower())
    if target_day is None:
        return None
    days_ahead = target_day - today.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    return today + timedelta(days_ahead)



def remove_am_pm(event_text):
    """Remove 'am' and 'pm' from the event text."""
    return event_text.replace(" am", "").replace(" pm", "")


# Load spaCy English model
nlp = spacy.load("en_core_web_sm")


import re

def split_sentences(sentence: str) -> list:
    """Split a sentence by commas or 'and' only if multiple timings are present."""
    # Parse the sentence using spaCy to extract entities
    doc = nlp(sentence)
    
    # Find all time entities
    times = [ent.text for ent in doc.ents if ent.label_ == "TIME"]

    # If there are multiple time entities, split the sentence
    if len(times) > 1:
        parts = re.split(r',|\band\b', sentence)
        return [part.strip() for part in parts if part.strip()]
    
    # If only one or no time found, return the sentence as a single item list
    return [sentence.strip()]
def extract_event_details(sentence, current_date=None):
    """Extract event details from the sentence."""
    doc = nlp(sentence)
    dates = [ent.text for ent in doc.ents if ent.label_ == "DATE"]
    time = [ent.text for ent in doc.ents if ent.label_ == "TIME"]
    today = datetime.today()
    formatted_dates = []

    matches = matcher(doc)
    events = []
    
    # Extract matches based on defined patterns
    for match_id, start, end in matches:
        span = doc[start:end]
        event_text = span.text.strip()
        if event_text and event_text not in events:
            events.append(event_text)

    # If no matches found, convert verbs to nouns
    if not events:
        verbs = [token.text for token in doc if token.pos_ == "VERB"]
        if verbs:
            event = convert_verbs_to_nouns(verbs[0])
            if event:
                events.append(event)

    # Process dates and format them
    for date_str in dates:
        parsed_date = None  # Initialize parsed_date

        if "next week" in date_str.lower():
            parsed_date = get_next_monday(today)
        elif "next month" in date_str.lower():
            parsed_date = get_first_day_of_next_month(today)
        elif any(day in date_str.lower() for day in days_of_week):
            for day_name in days_of_week:
                if day_name in date_str.lower():
                    parsed_date = get_next_day_by_name(today, day_name)
                    break  # Exit loop once found
        else:
            parsed_date = parse(date_str, settings={'RELATIVE_BASE': today})

        # If we have a valid parsed_date, format and set current_date
        if parsed_date:
            formatted_dates.append((date_str, parsed_date.strftime("%d-%m-%y")))
            current_date = parsed_date.strftime("%d-%m-%y")  # Update the current date
        elif current_date:
            formatted_dates.append((date_str, current_date))  # Use the last known date

    # If no dates were found, use today's date if current_date is still None
    if not formatted_dates:
        if current_date is None:
            current_date = today.strftime("%d-%m-%y")  # Set to today's date if no date was found
    
        formatted_dates.append((None, current_date))

    # Convert time phrases
    formatted_time = [convert_time_phrases(t) for t in time]

    summarized_event = convert_verbs_to_nouns(sentence)
    summarized_event = remove_am_pm(summarized_event)

    # Check if summarized_event contains only adjectives or adverbs
    summarized_doc = nlp(summarized_event)
    only_adjective_or_adverb = all(
        token.pos_ in {"ADJ", "ADV"} for token in summarized_doc
    )
    
    # Replace with "No event" if it contains only adjectives or adverbs
    if only_adjective_or_adverb:
        summarized_event = "No event"

    # Capitalize the first letter of the summarized event
    summarized_event = summarized_event.capitalize()

    # Check if the sentence contains the word "cancelled"
    if "cancelled" in sentence.lower():
        summarized_event =  summarized_event + ": Cancelled" ;# Prepend "Cancelled"

    # If summarized_event is "No event" and no time is present, do not return it
    if summarized_event == "No event" and not formatted_time:
        return None, current_date

    result = {
        "Event": summarized_event,
        "Date": ', '.join([d[1] for d in formatted_dates]) if formatted_dates else "",
        "Time": ', '.join(formatted_time) if formatted_time else ""
    }

    return result, current_date

def process_paragraph(paragraph: str) -> list:
    """Process a paragraph and extract event details from each sentence."""
    # Split paragraph by periods, and handle new lines as sentence delimiters
    sentences = [sentence.strip() + '.' for sentence in paragraph.split('.') if sentence.strip()]
    
    # Initialize current_date to None for the first sentence
    current_date = None
    schedule = []
    
    # Extract event details from each sentence directly
    for sentence in sentences:
        # Use the split_sentences function to get segments
        split_sentences_list = split_sentences(sentence)
        for seg in split_sentences_list:
            event_details, current_date = extract_event_details(seg, current_date)  # Pass current_date and receive updated current_date
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
    # if email_bodies:
        # combined_text = text + " ".join(email_bodies)
    # else:
        # combined_text=text
    # Generate summary for the combined text
    # summary = summarize_text(combined_text)
    summary = summarize_text(text)
    
    return jsonify({"summary": summary})


@app.route('/events', methods=['POST'])
def events():
    """Endpoint to extract event details from the provided text."""
    data = request.json
    text = data.get('text', '')

    # fetch_emails()

    
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

@app.route('/fetch-emails', methods=['GET'])
def fetch_emails():
    """Fetches emails using saved credentials and stores them in MongoDB."""
    try:
        # Import saved credentials
        import credentials  # Assumes 'credentials.py' exists after saving

        # Connect to email server
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(credentials.EMAIL, credentials.PASSWORD)

        # Select inbox and fetch all emails
        mail.select("inbox")
        result, data = mail.search(None, 'ALL')
        email_ids = data[0].split()
        emails = []

        for email_id in email_ids:
            result, msg_data = mail.fetch(email_id, "(RFC822)")
            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)

            subject = msg["subject"]
            from_ = msg["from"]

            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    if content_type == "text/plain" or content_type == "text/html":
                        body = part.get_payload(decode=True)
                        text = BeautifulSoup(body, "html.parser").get_text() if content_type == "text/html" else body.decode()
                        email_data = {"subject": subject, "from": from_, "body": text}
                        emails.append(email_data)
                        collection.insert_one(email_data)  # Insert email data into MongoDB
            else:
                body = msg.get_payload(decode=True)
                email_data = {"subject": subject, "from": from_, "body": body.decode()}
                emails.append(email_data)
                collection.insert_one(email_data)

        mail.logout()
       
        return jsonify({"emails": emails})

    except Exception as e:
        print("An error occurred:", e)
        return jsonify({"error": str(e)}), 500

# Automatically fetch emails if credentials already exist
# if os.path.exists("credentials.py"):
#     try:
#         fetch_emails()
#     except Exception as e:
#         print(f"Error fetching emails at startup: {e}")
        
@app.route('/save-credentials', methods=['POST'])
def save_credentials():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    try:
        file_path = os.path.join(os.path.dirname(__file__), 'credentials.py')
        with open(file_path, 'w') as f:
            f.write(f'EMAIL = "{email}"\n')
            f.write(f'PASSWORD = "{password}"\n')

        print("Credentials successfully saved to credentials.py")

        
# Trigger fetch_emails after saving credentials
        fetch_emails()
        response = {
            "message": "Credentials saved successfully",
            "email": email
        }


    except Exception as e:
        print("An error occurred:", e)
        response = {
            "message": "Failed to save credentials",
            "error": str(e)
        }
    
    
    return jsonify(response)

if __name__ == "__main__":
    app.run(debug=True)
