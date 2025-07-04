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

# Suggestions dictionary
SUGGESTIONS = {
    "Emotional State": {
        (1, 25): "It seems you're going through a difficult time emotionally. Consider talking to a counselor or taking short breaks to focus on self-care.",
        (26, 50): "You might be feeling somewhat low or anxious. Try mindfulness exercises or journaling to process your feelings.",
        (51, 75): "You're doing okay emotionally. Keep using strategies that help you maintain balance, like hobbies or social time.",
        (76, 100): "You appear to be in a positive emotional state. Keep it up and consider sharing your good energy with your team!"
    },
    "Workload & Role": {
        (1, 25): "Your workload or role may be overwhelming. Consider discussing priorities or task redistribution with your manager.",
        (26, 50): "You might be struggling with motivation or clarity in your role. Reflect on what you enjoy most and talk to your lead.",
        (51, 75): "Your workload seems manageable but there's room for better alignment. Consider setting clearer goals.",
        (76, 100): "You seem satisfied and fulfilled in your role. Great job! Consider mentoring others or expanding your responsibilities."
    },
    "Team & Social": {
        (1, 25): "You may feel isolated or disconnected. Try scheduling 1:1s or team coffee chats to rebuild rapport.",
        (26, 50): "Team dynamics may be off. Open communication or a team-building activity could help strengthen bonds.",
        (51, 75): "You're feeling moderately connected. Keep building on this by offering support or initiating casual chats.",
        (76, 100): "You're well-connected with your team! Consider fostering this by recognizing others and encouraging inclusivity."
    },
    "Growth & Development": {
        (1, 25): "You might feel stagnant in your growth. Request feedback or seek out new learning opportunities.",
        (26, 50): "There may be some gaps in support or direction. A development plan or mentorship could help.",
        (51, 75): "You're progressing steadily. Consider setting a skill goal or attending a workshop to push further.",
        (76, 100): "You're growing well in your role! Keep the momentum by mentoring or setting stretch goals."
    }
}

def get_suggestion(section, score):
    for (min_score, max_score), suggestion in SUGGESTIONS[section].items():
        if min_score <= score <= max_score:
            return suggestion
    return ""

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
        user_exists = username in df['username'].values
        if not user_exists:
            return render_template('login.html', error="Username not found")
        
        user_row = df[df['username'] == username].iloc[0]
        if user_row['password'] != password:
            return render_template('login.html', error="Incorrect password")
            
        session['username'] = username
        return redirect('/checkin')
    return render_template('login.html', error="No registered users found")

@app.route('/signup')
def signup():
    return render_template('signup.html')

@app.route('/register', methods=['POST'])
def register():
    username = request.form['username']
    password = request.form['password']
    
    # Validate input
    if not username or not password:
        return render_template('signup.html', error="Username and password are required")
        
    if os.path.exists(USERS_FILE):
        df = pd.read_csv(USERS_FILE)
        if username in df['username'].values:
            return render_template('signup.html', error="This username is already taken. Please choose a different one")
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
        suggestions = {}
        for section, sc in scores.items():
            avg = sum(sc) / len(sc)
            score = map_to_score(avg)
            summary[section] = score
            suggestions[section] = get_suggestion(section, score)

        row = {
            'Name': session['username'],
            'Timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            **summary
        }

        df = pd.DataFrame([row])
        df.to_csv(LOG_FILE, mode='a', index=False, header=not os.path.exists(LOG_FILE))
        return render_template('summary.html', summary=summary, suggestions=suggestions)

    return render_template('checkin.html', questions=questions)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)
