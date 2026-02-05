from flask import Flask, render_template, flash, request, redirect, url_for, send_from_directory, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from sqlalchemy import func
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
import hashlib
import os

# Flask App Configuration
app = Flask(__name__)
app.secret_key = "change-this-secret-key"

# Reference: Pretty Printed. (2021) User Authentication & Authorization in Flask. YouTube.
# restricts standard content to users who have uploaded in the last 30 days
def has_recent_upload(user):
    """Returns True if user has uploaded content in the last 30 days"""
    cutoff = datetime.utcnow() - timedelta(days=30)

    recent_upload = Content.query.filter(
        Content.creator_id == user.id,
        Content.created_at >= cutoff
    ).first()

    return recent_upload is not None

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

class Content(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    creator_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)

    category = db.Column(db.String(50), nullable=False, default="Other")

    filename = db.Column(db.String(300), nullable=False)
    filetype = db.Column(db.String(20), nullable=False)

    views = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    creator = db.relationship("User", backref=db.backref("uploads", lazy=True))


class ContentView(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content_id = db.Column(db.Integer, db.ForeignKey("content.id"), nullable=False)

    viewer_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    ip_hash = db.Column(db.String(64), nullable=True)

    viewed_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    content = db.relationship("Content", backref=db.backref("view_events", lazy=True))


with app.app_context():
    db.create_all()

CATEGORIES = [
    "Music",
    "Coding",
    "Design",
    "Business",
    "Fitness",
    "Languages",
    "Art",
    "Other"
]


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

# Reference: Flask Documentation. (2025) File Uploads in Flask.
# Upload configuration
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024

ALLOWED_VIDEO_EXTENSIONS = {"mp4", "webm", "mov", "m4v"}
ALLOWED_DOC_EXTENSIONS = {"pdf"}
ALLOWED_EXTENSIONS = ALLOWED_VIDEO_EXTENSIONS | ALLOWED_DOC_EXTENSIONS

def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def get_ip_hash():
    ip = request.headers.get("X-Forwarded-For", request.remote_addr) or "unknown"
    salted = f"{ip}|{app.secret_key}"
    return hashlib.sha256(salted.encode("utf-8")).hexdigest()

def register_view(content: Content):
    now = datetime.utcnow()
    cutoff = now.timestamp() - (30 * 60)  # 30 minutes

    viewer_id = current_user.id if current_user.is_authenticated else None
    ip_hash = None if viewer_id else get_ip_hash()

    q = ContentView.query.filter_by(content_id=content.id)
    if viewer_id:
        q = q.filter_by(viewer_id=viewer_id)
    else:
        q = q.filter_by(ip_hash=ip_hash)

    recent = q.order_by(ContentView.viewed_at.desc()).first()
    if recent and recent.viewed_at.timestamp() > cutoff:
        return  # don't count again within 30 mins

    content.views += 1
    db.session.add(ContentView(content_id=content.id, viewer_id=viewer_id, ip_hash=ip_hash))
    db.session.commit()

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
    selected_category = request.args.get("category")

    categories = CATEGORIES

    uploads = []
    if selected_category:
        uploads = Content.query.filter_by(category=selected_category) \
            .order_by(Content.created_at.desc()).limit(12).all()
    else:
        uploads = Content.query.order_by(Content.created_at.desc()).limit(12).all()

    return render_template( 'index.html', user=current_user, categories=categories, uploads=uploads, selected_category=selected_category )

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

    channels = []
    uploads = []

    if q:
        # 1) Search channels (users)
        user_matches = User.query.filter(
            (func.ifnull(User.username, "").ilike(f"%{q}%")) |
            (func.ifnull(User.full_name, "").ilike(f"%{q}%"))
        ).all()

        channels = user_matches  # pass full user objects to template

        # 2) Search uploads/content
        content_matches = Content.query.filter(
            (func.ifnull(Content.title, "").ilike(f"%{q}%")) |
            (func.ifnull(Content.description, "").ilike(f"%{q}%"))
        ).order_by(Content.created_at.desc()).all()

        uploads = content_matches

    return render_template('search.html', q=q, channels=channels, uploads=uploads)

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

@app.route("/channel", methods=["GET", "POST"])
@login_required
def channel():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        file = request.files.get("file")
        category = request.form.get("category", "Other").strip()

        if not title:
            flash("Title is required.")
            return redirect(url_for("channel"))

        if category not in CATEGORIES:
            flash("Invalid category selected.")
            return redirect(url_for("channel"))

        if not file or file.filename == "":
            flash("Please choose a file to upload.")
            return redirect(url_for("channel"))

        if not allowed_file(file.filename):
            flash("File type not allowed. Upload mp4/webm/mov/m4v or pdf.")
            return redirect(url_for("channel"))

        original_name = secure_filename(file.filename)
        ext = original_name.rsplit(".", 1)[1].lower()

        # make filename unique per upload
        unique_name = f"user{current_user.id}_{int(datetime.utcnow().timestamp())}_{original_name}"
        save_path = os.path.join(app.config["UPLOAD_FOLDER"], unique_name)
        file.save(save_path)

        new_content = Content(
            creator_id=current_user.id,
            title=title,
            description=description,
            category=category,
            filename=unique_name,
            filetype=ext
        )
        db.session.add(new_content)
        db.session.commit()

        flash("Upload successful!")
        return redirect(url_for("channel"))

    my_uploads = Content.query.filter_by(creator_id=current_user.id).order_by(Content.created_at.desc()).all()
    is_active_creator = has_recent_upload(current_user)
    return render_template("channel.html", uploads=my_uploads, categories=CATEGORIES, is_active_creator=is_active_creator)

@app.route("/content/<int:content_id>")
@login_required
def view_content(content_id):
    content = Content.query.get_or_404(content_id)

    # Owner can always view their own content
    if content.creator_id != current_user.id:
        if not has_recent_upload(current_user):
            flash("You must upload content at least once every 30 days to access other creators' content.")
            return redirect(url_for("channel"))

    register_view(content)
    return render_template("content_view.html", content=content)

@app.route("/uploads/<path:filename>")
@login_required
def uploaded_file(filename):
    content = Content.query.filter_by(filename=filename).first_or_404()
    # if a user has not uploaded recently they cannot access the page by guessing the file url
    if content.creator_id != current_user.id:
        if not has_recent_upload(current_user):
            abort(403)

    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

@app.route("/content/<int:content_id>/edit", methods=["GET", "POST"])
@login_required
def edit_content(content_id):
    content = Content.query.get_or_404(content_id)

    if content.creator_id != current_user.id:
        abort(403)

    category = request.form.get("category", "Other").strip()
    if category not in CATEGORIES:
        flash("Invalid category selected.")
        return redirect(url_for("edit_content", content_id=content.id))


    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()

        if not title:
            flash("Title is required.")
            return redirect(url_for("edit_content", content_id=content.id))

        file = request.files.get("file")
        if file and file.filename:
            if not allowed_file(file.filename):
                flash("File type not allowed.")
                return redirect(url_for("edit_content", content_id=content.id))

            original_name = secure_filename(file.filename)
            ext = original_name.rsplit(".", 1)[1].lower()
            unique_name = f"user{current_user.id}_{int(datetime.utcnow().timestamp())}_{original_name}"

            save_path = os.path.join(app.config["UPLOAD_FOLDER"], unique_name)
            file.save(save_path)

            old_path = os.path.join(app.config["UPLOAD_FOLDER"], content.filename)
            try:
                if os.path.exists(old_path):
                    os.remove(old_path)
            except:
                pass

            content.filename = unique_name
            content.filetype = ext

        content.title = title
        content.description = description
        content.category = category
        db.session.commit()

        flash("Content updated.")
        return redirect(url_for("channel"))

    return render_template("content_edit.html", content=content, categories=CATEGORIES)

@app.route("/content/<int:content_id>/delete", methods=["POST"])
@login_required
def delete_content(content_id):
    content = Content.query.get_or_404(content_id)

    if content.creator_id != current_user.id:
        abort(403)

    file_path = os.path.join(app.config["UPLOAD_FOLDER"], content.filename)
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except:
        pass

    ContentView.query.filter_by(content_id=content.id).delete()

    db.session.delete(content)
    db.session.commit()

    flash("Content deleted.")
    return redirect(url_for("channel"))

#Reference: Corey Schafer. (2020) Flask Authorization Explained. YouTube.
@app.route("/channel/<username>")
@login_required
def public_channel(username):
    user = User.query.filter_by(username=username).first_or_404()

    uploads = Content.query.filter_by(creator_id=user.id)\
        .order_by(Content.created_at.desc()).all()

    is_owner = (current_user.id == user.id)

    return render_template("channel_public.html", channel_user=user, uploads=uploads, is_owner=is_owner)

if __name__ == '__main__':
    app.run(debug=True)
