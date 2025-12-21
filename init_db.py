# init_db.py
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, User, Enrollment, Booking

def init_database():
    with app.app_context():
        try:
            print("🚨 WARNING: Dropping ALL existing tables...")
            print("This will DELETE ALL YOUR DATA!")
            db.drop_all()
            
            print("Creating fresh tables with new schema...")
            db.create_all()
            
            # Add admin user
            admin = User(
                username='admin', 
                email='admin@clearq.in', 
                role='admin'
            )
            admin.set_password('admin123')
            db.session.add(admin)
            
            # Add sample mentors for testing
            sample_mentors = [
                {
                    'username': 'john_doe',
                    'email': 'john@example.com',
                    'password': 'test123',
                    'full_name': 'John Doe',
                    'domain': 'Data Science',
                    'company': 'Google',
                    'job_title': 'Senior Data Scientist',
                    'experience': '5 years',
                    'skills': 'Python, Machine Learning, SQL, TensorFlow',
                    'services': 'Resume Review, Mock Interview, Career Guidance',
                    'bio': 'I help aspiring data scientists land their dream jobs at FAANG companies.',
                    'price': 1500,
                    'availability': 'Weekdays 6-9 PM',
                    'is_verified': True,
                    'role': 'mentor'
                },
                {
                    'username': 'jane_smith',
                    'email': 'jane@example.com',
                    'password': 'test123',
                    'full_name': 'Jane Smith',
                    'domain': 'Product Management',
                    'company': 'Microsoft',
                    'job_title': 'Product Manager',
                    'experience': '7 years',
                    'skills': 'Product Strategy, Agile, User Research, Roadmapping',
                    'services': 'Mock Interview, Product Case Studies, Career Transition',
                    'bio': 'Ex-Microsoft PM with 7+ years experience.',
                    'price': 2000,
                    'availability': 'Weekends 10 AM - 6 PM',
                    'is_verified': True,
                    'role': 'mentor'
                }
            ]
            
            for data in sample_mentors:
                mentor = User(
                    username=data['username'],
                    email=data['email'],
                    role=data['role'],
                    full_name=data['full_name'],
                    domain=data['domain'],
                    company=data['company'],
                    job_title=data['job_title'],
                    experience=data['experience'],
                    skills=data['skills'],
                    services=data['services'],
                    bio=data['bio'],
                    price=data['price'],
                    availability=data['availability'],
                    is_verified=data['is_verified']
                )
                mentor.set_password(data['password'])
                db.session.add(mentor)
            
            db.session.commit()
            print("✅ Database reset and populated successfully!")
            print("✅ Admin login: admin@clearq.in / admin123")
            print("✅ Sample mentors added for testing")
            
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == '__main__':
    init_database()
