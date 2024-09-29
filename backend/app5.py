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
    "session": "session"
}

# Initialize Matcher
matcher = Matcher(nlp.vocab)

# Define patterns for event-related phrases
event_patterns = [
    [{"POS": "NOUN"}, {"POS": "NOUN", "OP": "?"}],  # Noun + Optional Noun
    [{"POS": "ADJ"}, {"POS": "NOUN"}],              # Adjective + Noun (e.g., Chemistry Class)
    [{"POS": "VERB"}, {"POS": "NOUN", "OP": "?"}],  # Verb + Optional Noun
    [{"POS": "VERB"}, {"POS": "ADP", "OP": "?"}, {"POS": "NOUN"}],  # Verb + Optional Preposition + Noun
    [{"POS": "NOUN"}, {"POS": "ADP"}, {"POS": "NOUN"}],  # Noun + Preposition + Noun
    [{"POS": "ADJ"}, {"POS": "ADJ"}, {"POS": "NOUN"}],  # Adjective + Adjective + Noun (e.g., Advanced Chemistry Class)
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



def is_interrogative(sentence):
    """Check if a sentence is a question."""
    return sentence.strip().endswith('?')

def extract_event_details(sentence):
    """Extract event details from the sentence, and handle cancellations."""
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

    # Check if the sentence contains "cancelled" and is not interrogative


def extract_event_details(sentence):
    """Extract event details from the sentence and account for cancellations."""
    doc = nlp(sentence)
    dates = [ent.text for ent in doc.ents if ent.label_ == "DATE"]
    time = [ent.text for ent in doc.ents if ent.label_ == "TIME"]
    today = datetime.today()
    formatted_dates = []

    matches = matcher(doc)
    events = []
    
    # Check if the sentence contains the word "cancelled"
    is_cancelled = "cancelled" in sentence.lower()

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
        if "next week" in date_str.lower():
            formatted_dates.append((date_str, get_next_monday(today).strftime("%d-%m-%y")))
        elif "next month" in date_str.lower():
            formatted_dates.append((date_str, get_first_day_of_next_month(today).strftime("%d-%m-%y")))
        elif any(day in date_str.lower() for day in days_of_week):
            for day_name in days_of_week:
                if day_name in date_str.lower():
                    next_day = get_next_day_by_name(today, day_name)
                    if next_day:
                        formatted_dates.append((date_str, next_day.strftime("%d-%m-%y")))
        else:
            parsed_date = parse(date_str, settings={'RELATIVE_BASE': today})
            if parsed_date:
                formatted_dates.append((date_str, parsed_date.strftime("%d-%m-%y")))

    # Convert time phrases
    formatted_time = [convert_time_phrases(t) for t in time]

    # If the event is cancelled, append 'Cancelled' to the event description
    summarized_event = convert_verbs_to_nouns(sentence)
    if is_cancelled:
        summarized_event = f"{summarized_event}: Cancelled "

    result = {
        "Event": summarized_event,
        "Date": ', '.join([d[1] for d in formatted_dates]) if formatted_dates else "",
        "Time": ', '.join(formatted_time) if formatted_time else ""
    }

    return result

    """ Extract event details from the sentence, including cancelled events. """
    doc = nlp(sentence)
    dates = [ent.text for ent in doc.ents if ent.label_ == "DATE"]
    time = [ent.text for ent in doc.ents if ent.label_ == "TIME"]
    today = datetime.today()
    formatted_dates = []

    matches = matcher(doc)
    events = []
    
    # Check if the sentence contains the word "cancelled"
    is_cancelled = any(token.text.lower() in ["cancelled", "canceled"] for token in doc)
    
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
    
    # Mark the event as cancelled if applicable
    if is_cancelled:
        events = [f"{event} (Cancelled)" for event in events]

    # Process dates and format them
    for date_str in dates:
        if "next week" in date_str.lower():
            formatted_dates.append((date_str, get_next_monday(today).strftime("%d-%m-%y")))
        elif "next month" in date_str.lower():
            formatted_dates.append((date_str, get_first_day_of_next_month(today).strftime("%d-%m-%y")))
        elif any(day in date_str.lower() for day in days_of_week):
            for day_name in days_of_week:
                if day_name in date_str.lower():
                    next_day = get_next_day_by_name(today, day_name)
                    if next_day:
                        formatted_dates.append((date_str, next_day.strftime("%d-%m-%y")))
        else:
            parsed_date = parse(date_str, settings={'RELATIVE_BASE': today})
            if parsed_date:
                formatted_dates.append((date_str, parsed_date.strftime("%d-%m-%y")))

    # Convert time phrases
    formatted_time = [convert_time_phrases(t) for t in time]

    # Summarize the event
    summarized_event = convert_verbs_to_nouns(sentence)

    result = {
        "Event": summarized_event if summarized_event else "No Event",
        "Date": ', '.join([d[1] for d in formatted_dates]) if formatted_dates else "No Date",
        "Time": ', '.join(formatted_time) if formatted_time else "No Time"
    }

    return result



def process_paragraph(paragraph: str) -> list:
    """Process a paragraph and extract event details from each sentence."""
    sentences = [sentence.strip() + '.' for sentence in paragraph.split('.') if sentence.strip()]
    schedule = [extract_event_details(sentence) for sentence in sentences]

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
    max_input_length = 1024
    min_summary_length = 50
    max_summary_length = 200

    # Break text into chunks if needed
    inputs = [text[i:i+max_input_length] for i in range(0, len(text), max_input_length)]

    summary = ""
    for input_text in inputs:
        summary_chunk = summarizer(input_text, max_length=max_summary_length, min_length=min_summary_length, do_sample=False)[0]['summary_text']
        summary += summary_chunk + " "

    return summary.strip()

# Flask routes
@app.route('/summarize', methods=['POST'])
def summarize():
    data = request.json
    text = data.get('text')
    if not text:
        return jsonify({"error": "No text provided"}), 400
    summary = summarize_text(text)
    return jsonify({"summary": summary})

@app.route('/events', methods=['POST'])
def events():
    """Endpoint to extract event details from the provided text."""
    data = request.json
    text = data.get('text', '')

    if not text:
        return jsonify({"error": "No text provided"}), 400

    try:
        event_details = process_paragraph(text)
        return jsonify({"events": event_details})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
