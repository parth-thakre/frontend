from flask import Flask, request, jsonify
from transformers import pipeline
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Allow CORS

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

@app.route('/summarize', methods=['POST'])
def summarize():
    data = request.json
    text = data.get('text')
    if not text:
        return jsonify({"error": "No text provided"}), 400
    summary = summarize_text(text)
    return jsonify({"summary": summary})

if __name__ == "__main__":
    app.run(debug=True)
