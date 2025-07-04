from flask import Flask, render_template, request, redirect, url_for, session
import pandas as pd
from datetime import datetime
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'
analyzer = SentimentIntensityAnalyzer()
USERS_FILE = "users.csv"
LOG_FILE = "emotional_checkin_log.csv"

# Utility functions
def load_questions():
    return {
        "Emotional State": [
            "How have you been feeling emotionally this week?",
            "Are you experiencing stress or anxiety?",
            "Have you felt excited or hopeful recently?"
        ],
        "Workload & Role": [
            "How manageable is your current workload?",
            "Do you find your tasks fulfilling?",
            "Are you satisfied with your current responsibilities?"
        ],
        "Team & Social": [
            "Do you feel connected with your team?",
            "How is your communication with colleagues?",
            "Do you feel appreciated at work?"
        ],
        "Growth & Development": [
            "Are you learning new things regularly?",
            "Do you feel you're growing in your role?",
            "Is your manager helping you improve?"
        ]
    }

def analyze_responses(responses):
    scores = []
    for r in responses:
        score = analyzer.polarity_scores(r)['compound']
        scores.append(score)
    return scores

def map_to_score(avg):
    return int((1 - avg) * 50 + 1)

# Routes
@app.route('/')
def home():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    if os.path.exists(USERS_FILE):
        df = pd.read_csv(USERS_FILE)
        if ((df['username'] == username) & (df['password'] == password)).any():
            session['username'] = username
            return redirect('/checkin')
    return "Invalid credentials. <a href='/'>Try again</a>"

@app.route('/signup')
def signup_page():
    return render_template('signup.html')

@app.route('/register', methods=['POST'])
def register():
    username = request.form['username']
    password = request.form['password']
    if os.path.exists(USERS_FILE):
        df = pd.read_csv(USERS_FILE)
        if username in df['username'].values:
            return "Username already exists. <a href='/'>Try again</a>"
    else:
        df = pd.DataFrame(columns=["username", "password"])
    df.loc[len(df)] = [username, password]
    df.to_csv(USERS_FILE, index=False)
    return redirect('/')

@app.route('/checkin', methods=['GET', 'POST'])
def checkin():
    if 'username' not in session:
        return redirect('/')
    questions = load_questions()
    if request.method == 'POST':
        responses = {}
        scores = {}
        for category, qs in questions.items():
            answers = [request.form.get(f"{category}_{i}") for i in range(len(qs))]
            responses[category] = answers
            scores[category] = analyze_responses(answers)

        summary = {}
        for section, sc in scores.items():
            avg = sum(sc) / len(sc)
            summary[section] = map_to_score(avg)

        row = {
            'Name': session['username'],
            'Timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            **summary
        }

        df = pd.DataFrame([row])
        df.to_csv(LOG_FILE, mode='a', index=False, header=not os.path.exists(LOG_FILE))
        return render_template('summary.html', summary=summary)

    return render_template('checkin.html', questions=questions)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)
