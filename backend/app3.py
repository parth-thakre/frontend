from flask import Flask, request, jsonify
import spacy
from spacy.matcher import Matcher
import inflect
import re
import nltk
from nltk.stem import WordNetLemmatizer
from transformers import pipeline
from flask_cors import CORS
from dateutil import parser
from datetime import datetime

app = Flask(__name__)
CORS(app)  # Allow CORS

# Ensure NLTK data is downloaded
nltk.download('stopwords')
nltk.download('wordnet')

# Load spaCy model for English
nlp = spacy.load('en_core_web_sm')

# Initialize the inflect engine
p = inflect.engine()

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
    [{"POS": "ADJ"}, {"POS": "NOUN"}],              # Adjective + Noun
    [{"POS": "VERB"}, {"POS": "NOUN", "OP": "?"}],  # Verb + Optional Noun
    [{"POS": "VERB"}, {"POS": "ADP", "OP": "?"}, {"POS": "NOUN"}],  # Verb + Optional Preposition + Noun
    [{"POS": "NOUN"}, {"POS": "ADP"}, {"POS": "NOUN"}]  # Noun + Preposition + Noun
]
matcher.add("EVENT_PATTERN", event_patterns)

def convert_time_phrases(text: str) -> str:
    """Convert colloquial time phrases into standard time format."""
    time_conversions = {
        r'half[-\s]?past (\d+)': lambda m: f"{int(m.group(1))}:30",  # Half-past 3 -> 3:30
        r'quarter[-\s]?to (\d+)': lambda m: f"{int(m.group(1))-1}:45",  # Quarter to 4 -> 3:45
        r'quarter[-\s]?past (\d+)': lambda m: f"{int(m.group(1))}:15",  # Quarter past 3 -> 3:15
        r'o\'clock': '',  # Remove 'o'clock' as it's redundant
        r'(\d+)\s*to\s*(\d+)\s*(am|pm)?': lambda m: f"{int(m.group(1))}:00-{int(m.group(2))}:00"  # 12 to 1 -> 12:00-1:00
    }

    # Apply all time conversions
    for pattern, converter in time_conversions.items():
        text = re.sub(pattern, converter, text, flags=re.IGNORECASE)

    return text

def remove_date_time(sentence: str) -> str:
    """Remove date and time entities from the sentence."""
    sentence = convert_time_phrases(sentence)
    doc = nlp(sentence)

    # Remove date and time entities
    remaining_text = ' '.join([token.text for token in doc if token.ent_type_ not in ["DATE", "TIME"]])

    # Clean up extra spaces and punctuation
    remaining_text = ' '.join(remaining_text.split()).strip(",. ")

    return remaining_text

def convert_verbs_to_nouns(text: str) -> str:
    """Convert verbs in the text to their corresponding noun forms."""
    doc = nlp(text)
    nouns = [token.text for token in doc if token.pos_ == "NOUN"]
    verbs = [token.text for token in doc if token.pos_ == "VERB"]

    # Check for priority words and their forms
    for word, noun_form in priority_words.items():
        if word in text.lower():
            return noun_form

    # Convert verbs to their noun forms
    for verb in verbs:
        verb_base_form = lemmatizer.lemmatize(verb, 'v')  # Base form of the verb
        if verb_base_form in priority_words:
            return priority_words[verb_base_form]

    if nouns:
        return ' '.join(nouns)

    if verbs:
        verb = verbs[0]
        noun_form = lemmatizer.lemmatize(verb, 'n')
        if noun_form != verb:
            return noun_form
        else:
            return verb + "ing"  # Default to gerund form

    return text

def normalize_date(date_str):
    """Normalize the date to YYYY-MM-DD format."""
    try:
        parsed_date = parser.parse(date_str, fuzzy=True)
        return parsed_date.strftime('%Y-%m-%d')
    except (ValueError, TypeError):
        return "No Date"

def normalize_time(time_str):
    """Normalize the time to HH:MM AM/PM format."""
    try:
        parsed_time = parser.parse(time_str, fuzzy=True)
        return parsed_time.strftime('%I:%M %p')
    except (ValueError, TypeError):
        return "No Time"

def extract_event_details(sentence: str) -> dict:
    """Extract event details such as event name, date, and time from a sentence."""
    sentence_with_standard_time = convert_time_phrases(sentence)
    doc = nlp(sentence_with_standard_time)

    # Extract date and time entities
    date_entities = [ent.text for ent in doc.ents if ent.label_ == "DATE"]
    time_entities = [ent.text for ent in doc.ents if ent.label_ == "TIME"]

    # Normalize date and time
    normalized_date = normalize_date(date_entities[0]) if date_entities else "No Date"
    normalized_time = normalize_time(time_entities[0]) if time_entities else "No Time"

    # Remove date and time from the sentence for event extraction
    remaining_text = remove_date_time(sentence_with_standard_time)
    
    # Extract potential event (noun or verb converted to noun)
    summarized_text = convert_verbs_to_nouns(remaining_text)

    # Ensure we have some event name, fallback if necessary
    event_name = summarized_text if summarized_text else "Unknown Event"
    
    # Handling specific timetable formats (e.g., "12:00-1:00")
    time_range_match = re.search(r'(\d{1,2}:\d{2}-\d{1,2}:\d{2})', sentence_with_standard_time)
    if time_range_match:
        time_range = time_range_match.group(1)
        event_match = re.search(r':\s*(\w+)', sentence_with_standard_time)
        event_name = event_match.group(1) if event_match else summarized_text
        return {
            "Event": event_name,
            "Date": normalized_date,
            "Time": time_range  # Keep the original time range format
        }
    
    # Return the extracted event details with normalized date and time
    return {
        "Event": event_name,
        "Date": normalized_date,
        "Time": normalized_time
    }

def process_paragraph2(paragraph: str) -> list:
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
        schedule = process_paragraph2(text)
        return jsonify({"schedule": schedule})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
