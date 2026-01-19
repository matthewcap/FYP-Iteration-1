from flask import Flask, render_template, flash, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from sqlalchemy import func
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

# Flask App Configuration
app = Flask(__name__)
app.secret_key = "change-this-secret-key"

# Calculate Age from DOB
def calculate_age(dob_string):
    if not dob_string:
        return None
    try:
        dob = datetime.strptime(dob_string, "%Y-%m-%d")
        today = datetime.today()
        return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    except:
        return None

# Reference ChatGPT prompt in documentation
# Database configuration
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'database_v1.db')
print("USING DATABASE PATH:", app.config['SQLALCHEMY_DATABASE_URI'])
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Database MODELS
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# Reference, Werkzeug. (2025) Password Hashing Utilities and database models setup.
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)

    # Profile fields
    full_name = db.Column(db.String(120))
    country = db.Column(db.String(120))
    language = db.Column(db.String(120))
    dob = db.Column(db.String(20))

    # Skills user can teach
    teach_skills = db.Column(db.String(500))

    # Skills the user wants to learn
    learn_skills = db.Column(db.String(500))

with app.app_context():
    db.create_all()

# Flask-Login User Loader
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Registration
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Prevent duplicate usernames
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('register'))

        # Hash and store password securely
        # Reference, Werkzeug. (2025) Password Hashing Utilities and database models setup.
        hashed_pw = generate_password_hash(password)
        new_user = User(username=username, password=hashed_pw)
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful. Please log in.')
        return redirect(url_for('login'))

    return render_template('register.html')

# User Profile Page
@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':

        # profile fields
        current_user.full_name = request.form.get('full_name')
        current_user.country = request.form.get('country')
        current_user.language = request.form.get('language')
        current_user.dob = request.form.get('dob')
        skill1 = request.form.get('skill1', '').strip()
        skill2 = request.form.get('skill2', '').strip()
        skill3 = request.form.get('skill3', '').strip()
        skill4 = request.form.get('skill4', '').strip()
        skill5 = request.form.get('skill5', '').strip()

        skills_list = [s for s in [skill1, skill2, skill3, skill4, skill5] if s != ""]
        current_user.teach_skills = ", ".join(skills_list)

        db.session.commit()
        flash("Profile updated successfully.")
        return redirect(url_for('profile'))

    return render_template('profile.html', user=current_user)

#Reference IS3312: Advanced Programming for Information Systems (2024).
# Login Route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        # Invalid login
        if not user or not check_password_hash(user.password, password):
            flash('Invalid username or password')
            return redirect(url_for('login'))

        login_user(user)
        flash('Logged in successfully!')
        return redirect(url_for('home'))

    return render_template('login.html')

# Logout Route
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('home'))

#Reference IS3312: Advanced Programming for Information Systems (2024).
# Homepage Route
@app.route('/', methods=['GET', 'POST'])
def home():
    return render_template('index.html',user=current_user)

#Geeksforgeeks (2025). Flask to database connection including CRUD operations.
@app.route('/add_learn_skill', methods=['POST'])
@login_required
def add_learn_skill():
    skill = request.form.get('learn_skill', '').strip()

    if skill:
        existing = []
        if current_user.learn_skills:
            existing = current_user.learn_skills.split(', ')

        # Avoid duplicates
        if skill not in existing:
            existing.append(skill)

        current_user.learn_skills = ", ".join(existing)
        db.session.commit()
        flash("Skill added to your learning list.")

    return redirect(url_for('home'))


#Geeksforgeeks (2025). Flask to database connection including CRUD operations.
# Remove Skill from 'Learn List' route
@app.route('/remove_learn_skill', methods=['POST'])
@login_required
def remove_learn_skill():
    skill_to_remove = request.form.get('skill')

    if skill_to_remove and current_user.learn_skills:
        skills = current_user.learn_skills.split(', ')

        if skill_to_remove in skills:
            skills.remove(skill_to_remove)

        current_user.learn_skills = ", ".join(skills) if skills else ""
        db.session.commit()
        flash("Skill removed from your learning list.")

    return redirect(url_for('home'))

# Skill Search Route
@app.route('/search')
def search():
    q = request.args.get('q', '').strip()
    results = []

    if q:
        # Case-insensitive match on teach_skills
        users = User.query.filter(
            func.ifnull(User.teach_skills, "").ilike(f"%{q}%")
        ).all()

        for user in users:
            if user.teach_skills:
                for skill in user.teach_skills.split(','):
                    skill_clean = skill.strip()
                    if q.lower() in skill_clean.lower():
                        results.append({
                            "skill": skill_clean,
                            "teacher": user.full_name or user.username,
                            "country": user.country,
                            "language": user.language,
                            "teacher_id": user.id
                        })

    return render_template('search.html', q=q, results=results)

#Reference IS3312: Advanced Programming for Information Systems (2024).
# Single Teacher Skill Page
@app.route('/teach/<skill>/<int:user_id>')
def skill_view_single(skill, user_id):
    user = User.query.get_or_404(user_id)
    user.age = calculate_age(user.dob)
    return render_template('skill_single.html', skill=skill, user=user)

# Messaging System
@app.route('/message/<int:user_id>', methods=['GET', 'POST'])
@login_required
def message_user(user_id):
    other_user = User.query.get_or_404(user_id)

    if request.method == 'POST':
        content = request.form.get('content', '').strip()
        if content:
            msg = Message(sender_id=current_user.id, receiver_id=user_id, content=content)
            db.session.add(msg)
            db.session.commit()
            flash("Message sent!")

    # Fetch conversation: messages between both users
    conversation = Message.query.filter(
        ((Message.sender_id == current_user.id) & (Message.receiver_id == user_id)) |
        ((Message.sender_id == user_id) & (Message.receiver_id == current_user.id))
    ).order_by(Message.timestamp.asc()).all()

    return render_template("conversation.html", other_user=other_user, messages=conversation)

# Inbox Page, Shows Latest Message Per Conversation
@app.route('/inbox')
@login_required
def inbox():
    user_id = current_user.id

    # Get all messages involving this user
    msgs = Message.query.filter(
        (Message.sender_id == user_id) |
        (Message.receiver_id == user_id)
    ).order_by(Message.timestamp.desc()).all()

    conversations = {}

    for m in msgs:
        other_id = m.sender_id if m.sender_id != user_id else m.receiver_id

        # Only keep the FIRST message (latest because we sorted DESC)
        if other_id not in conversations:
            conversations[other_id] = m

    results = []
    for other_user_id, message in conversations.items():
        other_user = User.query.get(other_user_id)
        results.append({
            "user": other_user,
            "message": message
        })

    return render_template('inbox.html', conversations=results)

if __name__ == '__main__':
    app.run(debug=True)
