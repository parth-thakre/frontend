# Event Extraction & Calendar Integration API

This Flask-based web application extracts events from text (emails, user input) and integrates them into **Google Calendar**. It utilizes **Natural Language Processing (NLP)** techniques to parse and understand event details.

## 🚀 Features

- **📌 Event Extraction**: Identifies events, dates, and times from unstructured text.
- **📬 Email Processing**: Fetches emails from Gmail API and extracts relevant event details.
- **📝 Text Summarization**: Uses **Facebook BART transformer model** to summarize text.
- **📅 Google Calendar Integration**: Adds extracted events to the user's Google Calendar.
- **🔍 NLP-based Processing**: Utilizes **spaCy, NLTK, and regex-based parsing** for text analysis.

---

## 📂 Project Structure

```
📦 project-folder
 ┣ 📜 app19.py       # Main Flask application
 ┣ 📜 requirements.txt # Dependencies
 ┣ 📜 credentials.json # Google API credentials (OAuth)
 ┣ 📜 token.json     # User authentication token
 ┗ 📜 README.md      # Project Documentation
```

---

## 🛠 Setup & Installation

### **1️⃣ Install Dependencies**

```bash
pip install -r requirements.txt
```

### **2️⃣ Set Up Google API Credentials**

1. Go to [Google Developer Console](https://console.developers.google.com/)
2. Create a **new project** and enable the following APIs:
   - **Gmail API**
   - **Google Calendar API**
3. Download `credentials.json` and place it in the project folder.

### **3️⃣ Run the Flask App**

```bash
python app19.py
```

### **4️⃣ Authenticate with Google**

- On first run, visit the provided authentication URL.
- Authorize the app and allow access to Gmail & Calendar.

---

## 🔗 API Endpoints

| Endpoint        | Method | Description                              |
| --------------- | ------ | ---------------------------------------- |
| `/summarize`    | POST   | Summarizes input text                    |
| `/events`       | POST   | Extracts events from text                |
| `/fetch-emails` | GET    | Fetches emails from Gmail                |
| `/add-events`   | POST   | Adds extracted events to Google Calendar |
| `/sign-out`     | POST   | Revokes API access                       |

### **Example Request** (Extract Events)

```bash
curl -X POST "http://localhost:5000/events" \n -H "Content-Type: application/json" \n -d '{"text": "Meeting with John at 3 PM tomorrow."}'
```

### **Example Response**

```json
{
  "events": [
    {
      "Event": "Meeting",
      "Date": "15-03-24",
      "Time": "15:00"
    }
  ]
}
```

---

## 🛡️ Security & Authentication

- Uses **OAuth 2.0** for secure authentication.
- Tokens are stored locally in `token.json`.

To sign out, use:

```bash
curl -X POST "http://localhost:5000/sign-out"
```

---

## 🏗️ Possible Improvements

✅ Enhance NLP accuracy with **transformer models** (e.g., GPT, T5).  
✅ Handle **recurring events** for better Calendar management.  
✅ Improve **error handling** for date/time parsing edge cases.

---

## 📜 License

This project is licensed under the **MIT License**.

---

## 🏆 Credits

- Built using **Flask, spaCy, NLTK, Google APIs**.
- NLP techniques inspired by event extraction research.

Happy coding! 🚀
