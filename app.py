import os
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel
import pandas as pd

app = Flask(__name__)
app.config['SECRET_KEY'] = 'clearq-secret-key-change-this-in-prod'

# Database Configuration
# Use SQLite for local dev, but allow switching to Postgres for hosting
basedir = os.path.abspath(os.path.dirname(__file__))
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
    mentors = User.query.filter_by(role='mentor', is_verified=True).all()
    if not mentors:
        return []

    # Prepare data for AI
    mentor_data = []
    for m in mentors:
        # Combine relevant fields into a single 'content' string
        content = f"{m.domain} {m.company} {m.services} {m.bio}"
        mentor_data.append({'id': m.id, 'content': content, 'obj': m})

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

# --- ROUTES ---

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
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered')
            return redirect(url_for('register'))

        user = User(username=username, email=email, role=role)
        user.set_password(password)
        
        if role == 'mentor':
            user.domain = request.form.get('domain')
            user.company = request.form.get('company')
            user.services = request.form.get('services')
            user.price = request.form.get('price')
            user.bio = request.form.get('bio')
            user.is_verified = False # Admin must approve
        
        db.session.add(user)
        db.session.commit()
        login_user(user)
        return redirect(url_for('index'))
        
    return render_template('register.html')

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