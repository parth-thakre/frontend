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

from dateutil.parser import parse
from dateutil.parser._parser import ParserError

# Load the spaCy model
nlp = spacy.load("en_core_web_sm")

# List of priority words to consider
priority_words = {"meeting", "conference", "call", "interview", "review", "session", "discussion", "presentation", "lecture"}

# List of time indicators and days of the week to exclude
time_indicators = {"am", "pm"}
days_of_week = {"monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"}

def is_date(text):
    """Checks if a given text is a date using dateutil's parse method."""
    try:
        # Parse with fuzzy=False to prevent partial matching
        parse(text, fuzzy=False)
        return True
    except ParserError:
        return False

def get_main_part(sentence):
    # Process the sentence with spaCy
    doc = nlp(sentence)
    print(sentence)
    # Initialize an empty list and set to hold the main part
    main_part = []
    unique_words = set()
    date_tokens = set()

    # Identify and store any tokens that are dates
    for token in doc:
        # If the token or token+next word represents a date, add to date_tokens
        if is_date(token.text):
            date_tokens.add(token.text)
        elif token.i + 1 < len(doc) and is_date(f"{token.text} {doc[token.i + 1].text}"):
            date_tokens.add(f"{token.text} {doc[token.i + 1].text}")

    # First, check for adjacent adjective + noun, noun + noun, noun + priority word, or priority word + noun
    for token in doc:
        # Skip time indicators, days of the week, and tokens identified as dates
        if token.text.lower() in time_indicators or token.text.lower() in days_of_week or token.text in date_tokens:
            continue
        
        # Check if token is a priority word
        if token.text.lower() in priority_words:
            # Check for adjacent adjective + noun or noun + noun
            next_token = token.nbor(1) if token.i + 1 < len(doc) else None
            prev_token = token.nbor(-1) if token.i - 1 >= 0 else None
            
            # Adjective + priority word or priority word + adjective
            if prev_token and prev_token.pos_ == "ADJ" and prev_token.dep_ in ("amod", "attr"):
                main_part_combo = f"{prev_token.text} {token.text}"
                if main_part_combo not in unique_words:
                    main_part.append(main_part_combo)
                    unique_words.add(main_part_combo)
                break  # Stop once we find the first valid combination
            
            # Adjective + noun pattern (priority word)
            elif next_token and next_token.pos_ == "ADJ" and next_token.dep_ in ("amod", "attr"):
                main_part_combo = f"{token.text} {next_token.text}"
                if main_part_combo not in unique_words:
                    main_part.append(main_part_combo)
                    unique_words.add(main_part_combo)
                break

            # Noun + noun pattern (priority word)
            elif next_token and next_token.pos_ == "NOUN":
                main_part_combo = f"{token.text} {next_token.text}"
                if main_part_combo not in unique_words:
                    main_part.append(main_part_combo)
                    unique_words.add(main_part_combo)
                break

            # Priority word + noun (adjacent)
            elif prev_token and prev_token.pos_ == "NOUN":
                main_part_combo = f"{prev_token.text} {token.text}"
                if main_part_combo not in unique_words:
                    main_part.append(main_part_combo)
                    unique_words.add(main_part_combo)
                break

            # If priority word has no adj/noun combination, just add the word itself
            elif token.text not in unique_words and len(main_part) == 0:
                main_part.append(token.text)
                unique_words.add(token.text)
                break
    
    # If no priority word with adjacent combinations is found, check for non-adjacent nouns
    if not main_part:
        for token in doc:
            # Skip time indicators, days of the week, and date tokens
            if token.text.lower() in time_indicators or token.text.lower() in days_of_week or token.text in date_tokens:
                continue
            
            # Add noun alone to the main part, but only if adjacent numbers are allowed
            if token.pos_ == "NOUN" and token.text not in unique_words:
                # Check if an adjacent number (like "5th") exists
                prev_token = token.nbor(-1) if token.i - 1 >= 0 else None
                next_token = token.nbor(1) if token.i + 1 < len(doc) else None
                
                if prev_token and prev_token.like_num:
                    main_part_combo = f"{prev_token.text} {token.text}"
                    if main_part_combo not in unique_words:
                        main_part.append(main_part_combo)
                        unique_words.add(main_part_combo)
                elif next_token and next_token.like_num:
                    main_part_combo = f"{token.text} {next_token.text}"
                    if main_part_combo not in unique_words:
                        main_part.append(main_part_combo)
                        unique_words.add(main_part_combo)
                else:
                    main_part.append(token.text)
                    unique_words.add(token.text)
            
            # Stop if we've found up to five words
            if len(main_part) >= 5:
                break
    
    # Return the combined main part (adj + noun or noun + noun) with a max of five words
    return " ".join(main_part) if main_part else None

# Load spaCy English model
nlp = spacy.load("en_core_web_sm")


import re

def split_sentences(sentence: str) -> list:
    """Split a sentence by commas or 'and' only if multiple twings are present."""
    # Parse the sentence using spaCy to extract entities
    doc = nlp(sentence)
    
    # Find all time entities
    times = [ent.text for ent in doc.ents if ent.label_ == "TwE"]

    # If there are multiple time entities, split the sentence
    if len(times) > 1:
        parts = re.split(r',|\band\b', sentence)
        print(f"Split parts: {parts}") 
        return [part.strip() for part in parts if part.strip()]
    
    # If only one or no time found, return the sentence as a single item list
    return [sentence.strip()]

from datetime import datetime
from dateutil.parser import parse

def extract_event_details(sentence, current_date=None):
    """Extract event details from the sentence."""
    doc = nlp(sentence)
    dates = [ent.text for ent in doc.ents if ent.label_ == "DATE"]
    times = [ent.text for ent in doc.ents if ent.label_ == "TIME"]
    today = datetime.today()
    formatted_dates = []
    print("Original sentence:", sentence)

    # Summarize the event
    summarized_event = get_main_part(sentence)

    # Flag cancellations
    if "cancelled" in sentence.lower():
        summarized_event += ": Cancelled"

    # Process dates and add debug info
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
                parsed_date = parse(date_str, settings={'RELATIVE_BASE': today})

            # Append parsed date if valid
            if parsed_date:
                formatted_dates.append((date_str, parsed_date.strftime("%d-%m-%y")))
                current_date = parsed_date.strftime("%d-%m-%y")

        except Exception as e:
            print(f"Error parsing date '{date_str}': {e}")

    # Set default date if no date was found
    if not formatted_dates:
        current_date = current_date or today.strftime("%d-%m-%y")
        formatted_dates.append((None, current_date))

    # Convert time phrases
    formatted_times = [convert_time_phrases(t) for t in times]
    
    # Prepare the result
    result = {
        "Event": summarized_event,
        "Date": ', '.join([d[1] for d in formatted_dates]),
        "Time": ', '.join(formatted_times) if formatted_times else ""
    }
    
    print("Result:", result)
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
        print(split_sentences_list)
        for seg in split_sentences_list:
            print(seg)
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

    # emails=fetch_emails()

    
    # Fetch email bodies from MongoDB and deduplicate
    emails = collection.find({}, {"_id": 0, "body": 1})  # Retrieve email bodies from MongoDB
    email_bodies = list(set([email["body"] for email in emails]))  # Deduplicate emails

    if not text and not email_bodies:
        return jsonify({"error": "No text provided"}), 400
    
    
    # Combine the provided text with the email bodies
    if email_bodies:
        combined_text = text + " " + " ".join(email_bodies)  # Combine the input text with email bodies
        print(combined_text)
    else:
        combined_text = text

    try:
        # event_details = process_paragraph(text)
        event_details = process_paragraph(combined_text)  # Process the combined text
        print(combined_text)
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

@app.route('/fetch-emails', methods=['GET'])
def fetch_emails():
    """Fetches emails using saved credentials and stores them in MongoDB."""
    try:
        email_address = os.getenv("EMAIL")
        email_password = os.getenv("PASSWORD")
        
        # Connect to email server
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login("testemailminiproj@gmail.com", "bilb htsi xtwa rdkw")

        # Select inbox and fetch important emails
        mail.select("inbox")
        result, data = mail.search(None, 'X-GM-RAW', 'is:important')
        email_ids = data[0].split()
        emails = []

        for email_id in email_ids:
            result, msg_data = mail.fetch(email_id, "(RFC822)")
            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)

            # Extract unique message ID
            message_id = msg["Message-ID"]
            subject = msg["subject"]
            from_ = msg["from"]

            # Process email body
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    if content_type in ["text/plain", "text/html"]:
                        body = part.get_payload(decode=True)
                        text = BeautifulSoup(body, "html.parser").get_text() if content_type == "text/html" else body.decode()
                        
                        email_data = {
                            "message_id": message_id,
                            "subject": subject,
                            "from": from_,
                            "body": text
                        }
                        
                        # Use upsert to insert or update based on message_id
                        collection.update_one(
                            {"message_id": message_id},
                            {"$set": email_data},
                            upsert=True
                        )

                        emails.append(email_data)
            else:
                body = msg.get_payload(decode=True)
                email_data = {
                    "message_id": message_id,
                    "subject": subject,
                    "from": from_,
                    "body": body.decode()
                }

                # Use upsert to insert or update based on message_id
                collection.update_one(
                    {"message_id": message_id},
                    {"$set": email_data},
                    upsert=True
                )
                
                emails.append(email_data)

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
