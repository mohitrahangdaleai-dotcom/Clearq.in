import os
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel
import pandas as pd

# --- FORCE FLASK TO FIND TEMPLATES ---
# 1. Get the folder where THIS file (app.py) is located
basedir = os.path.abspath(os.path.dirname(__file__))

# 2. Tell Flask specifically where the 'templates' folder is
template_dir = os.path.join(basedir, 'templates')

# 3. Initialize Flask with this explicit path
app = Flask(__name__, template_folder=template_dir)
# -------------------------------------

app.config['SECRET_KEY'] = 'clearq-secret-key-change-this-in-prod'

# Database Configuration
# Use SQLite for local dev, but allow switching to Postgres for hosting
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or \
    'sqlite:///' + os.path.join(basedir, 'clearq.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# --- MODELS ---

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200))
    role = db.Column(db.String(20), default='learner') # 'learner', 'mentor', 'admin'
    
    # Mentor Specific Fields
    domain = db.Column(db.String(100)) # e.g., Data Science, SDE
    company = db.Column(db.String(100))
    services = db.Column(db.String(500)) # Resume Review, Mock Interview
    bio = db.Column(db.Text) # Used for AI matching
    price = db.Column(db.Integer)
    is_verified = db.Column(db.Boolean, default=False)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mentor_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    learner_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    service_name = db.Column(db.String(100))
    slot_time = db.Column(db.String(50))
    status = db.Column(db.String(20), default='Pending') # Pending, Paid, Completed

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- AI ENGINE (No API) ---
def get_ai_recommendations(user_goal):
    """
    Uses Scikit-Learn to find mentors whose bios/domains match the user's goal.
    """
    try:
        mentors = User.query.filter_by(role='mentor', is_verified=True).all()
        if not mentors:
            return []

        # Prepare data for AI
        mentor_data = []
        for m in mentors:
            # Combine relevant fields into a single 'content' string
            content = f"{m.domain} {m.company} {m.services} {m.bio}"
            mentor_data.append({'id': m.id, 'content': content, 'obj': m})

        if not mentor_data:
            return []

        # Add user goal to the corpus
        corpus = [m['content'] for m in mentor_data]
        corpus.append(user_goal)

        # TF-IDF Vectorization
        tfidf = TfidfVectorizer(stop_words='english')
        tfidf_matrix = tfidf.fit_transform(corpus)

        # Calculate Cosine Similarity
        # The last item in matrix is the user_goal. Compare it with all others.
        cosine_sim = linear_kernel(tfidf_matrix[-1], tfidf_matrix[:-1])
        
        # Get similarity scores
        scores = list(enumerate(cosine_sim[0]))
        scores = sorted(scores, key=lambda x: x[1], reverse=True)

        # Return top 3 matched mentor objects
        recommended_mentors = []
        for i, score in scores[:3]:
            if score > 0.1: # Threshold to filter completely irrelevant matches
                recommended_mentors.append(mentor_data[i]['obj'])
                
        return recommended_mentors
    except Exception as e:
        print(f"AI Error: {e}")
        return []

# --- ROUTES ---

# DEBUG ROUTE: Helps diagnose file path issues on Render
@app.route('/debug')
def debug_paths():
    output = "<h2>Current Directory Files:</h2>"
    
    # Get the current working directory
    cwd = os.getcwd()
    output += f"<b>Current Folder:</b> {cwd}<br><br>"
    
    # List files in current folder
    try:
        files = os.listdir(cwd)
        output += "<br>".join(files)
    except Exception as e:
        output += f"Error listing files: {e}"

    # Check specifically for templates
    # We use the variable 'template_dir' we defined at the top
    output += f"<br><br><h2>Looking for templates at: {template_dir}</h2>"
    
    if os.path.exists(template_dir):
        output += "<b>Found templates folder! Contents:</b><br>"
        try:
            tpl_files = os.listdir(template_dir)
            output += "<br>".join(tpl_files)
        except Exception as e:
            output += f"Error reading templates folder: {e}"
    else:
        output += "<b style='color:red'>Templates folder NOT found here!</b>"
        
    return output
@app.route('/mentorship-program')
def mentorship_program():
    return render_template('mentorship_program.html')
    
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/explore', methods=['GET', 'POST'])
def explore():
    recommendations = []
    query = ""
    
    if request.method == 'POST':
        query = request.form.get('goal')
        recommendations = get_ai_recommendations(query)
        
    # Get all verified mentors
    all_mentors = User.query.filter_by(role='mentor', is_verified=True).all()
    return render_template('mentors.html', mentors=all_mentors, recommendations=recommendations, query=query)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        role = request.form.get('role')
        
        if role == 'learner':
            # Handle learner registration (existing logic)
            username = request.form.get('username')
            email = request.form.get('email')
            password = request.form.get('password')
            # ... rest of your learner logic
            
        elif role == 'mentor':
            # Handle mentor registration with new fields
            username = request.form.get('username')
            email = request.form.get('email')
            password = request.form.get('password')
            full_name = request.form.get('full_name')
            phone = request.form.get('phone')
            job_title = request.form.get('job_title')
            company = request.form.get('company')
            domain = request.form.get('domain')
            experience = request.form.get('experience')
            skills = request.form.get('skills')  # Comma-separated
            price = request.form.get('price')
            availability = request.form.get('availability')
            bio = request.form.get('bio')
            # Get services as list
            services = request.form.getlist('services')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('index'))
        flash('Invalid credentials')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/mentor/<int:id>', methods=['GET', 'POST'])
def mentor_detail(id):
    mentor = User.query.get_or_404(id)
    # Basic slots logic (Hardcoded for demo, normally would be dynamic)
    slots = ["10:00 AM", "2:00 PM", "5:00 PM"]
    
    # Remove slots that are already booked for this mentor
    booked_slots = [b.slot_time for b in Booking.query.filter_by(mentor_id=id).all()]
    available_slots = [s for s in slots if s not in booked_slots]

    if request.method == 'POST':
        if not current_user.is_authenticated:
            return redirect(url_for('login'))
            
        service = request.form.get('service')
        slot = request.form.get('slot')
        
        # Payment Gateway Mock
        # In real life, redirect to Stripe/Razorpay here
        booking = Booking(mentor_id=id, learner_id=current_user.id, service_name=service, slot_time=slot, status='Paid')
        db.session.add(booking)
        db.session.commit()
        flash('Booking Confirmed! Payment Successful.')
        return redirect(url_for('dashboard'))

    return render_template('mentor_detail.html', mentor=mentor, slots=available_slots)

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'admin':
        pending_mentors = User.query.filter_by(role='mentor', is_verified=False).all()
        return render_template('admin.html', pending_mentors=pending_mentors)
    
    elif current_user.role == 'mentor':
        my_bookings = Booking.query.filter_by(mentor_id=current_user.id).all()
        return render_template('dashboard.html', bookings=my_bookings, type='mentor')
        
    else: # Learner
        my_bookings = Booking.query.filter_by(learner_id=current_user.id).all()
        mentors_booked = []
        for b in my_bookings:
            mentors_booked.append({'booking': b, 'mentor': User.query.get(b.mentor_id)})
        return render_template('dashboard.html', data=mentors_booked, type='learner')

@app.route('/verify/<int:id>')
@login_required
def verify_mentor(id):
    if current_user.role != 'admin':
        return "Unauthorized", 403
    mentor = User.query.get(id)
    mentor.is_verified = True
    db.session.commit()
    flash(f'{mentor.username} verified!')
    return redirect(url_for('dashboard'))

# Create DB on first run
with app.app_context():
    db.create_all()
    # Create a default admin if not exists
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', email='admin@clearq.in', role='admin')
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()

if __name__ == '__main__':
    app.run(debug=True)


