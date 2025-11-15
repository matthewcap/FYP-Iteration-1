from flask import Flask, render_template, flash, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)

# Reference ChatGPT prompt in documentation
# Database configuration
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)



# Database model
class Skill(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(100), nullable=False)


# Create database tables
with app.app_context():
    db.create_all()

#Reference IS3312: Advanced Programming for Information Systems (2024).
#Geeksforgeeks (2025). Flask to database connection including CRUD operations.
@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        skill_name = request.form.get('skill')
        username = request.form.get('username')

        if skill_name and username:
            new_skill = Skill(name=skill_name, username=username)
            db.session.add(new_skill)
            db.session.commit()

        return redirect(url_for('home'))

    skills = Skill.query.all()
    return render_template('index.html', skills=skills)

#Geeksforgeeks (2025). Flask to database connection including CRUD operations.
@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit(id):
    skill = Skill.query.get_or_404(id)
    if request.method == 'POST':
        new_name = request.form.get('skill')
        if new_name:
            skill.name = new_name
            db.session.commit()
            return redirect(url_for('home'))
    return render_template('edit_skill.html', skill=skill)

#Geeksforgeeks (2025). Flask to database connection including CRUD operations.
@app.route('/delete/<int:id>')
def delete(id):
    skill = Skill.query.get_or_404(id)
    db.session.delete(skill)
    db.session.commit()
    return redirect(url_for('home'))
@app.route('/search')
def search():
    q = request.args.get('q', '').strip()
    results = []
    if q:
        results = Skill.query.filter(Skill.name.ilike(f"%{q}%")).order_by(Skill.name.asc()).all()
    return render_template('search.html', q=q, results=results)
app.secret_key = "change-this-to-a-long-random-secret"


# Message model
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    skill_id = db.Column(db.Integer, db.ForeignKey('skill.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
#Reference IS3312: Advanced Programming for Information Systems (2024).
@app.route('/skill/<int:id>', methods=['GET', 'POST'])
def skill_detail(id):
    skill = Skill.query.get_or_404(id)

    if request.method == 'POST':
        content = request.form.get('message', '').strip()
        if content:
            m = Message(skill_id=skill.id, content=content)
            db.session.add(m)
            db.session.commit()
            flash("Your message has been sent successfully.")
            return redirect(url_for('skill_detail', id=skill.id))

    messages = Message.query.filter_by(skill_id=skill.id).order_by(Message.id.desc()).all()
    return render_template('skill.html', skill=skill, messages=messages)

if __name__ == '__main__':
    app.run(debug=True)
