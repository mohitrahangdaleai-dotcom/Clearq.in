# init_db.py
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, User, Enrollment, Booking

def init_database():
    with app.app_context():
        print("Dropping all tables...")
        db.drop_all()
        
        print("Creating all tables with updated schema...")
        db.create_all()
        
        # Add admin user if not exists
        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin', 
                email='admin@clearq.in', 
                role='admin'
            )
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print("Admin user created successfully")
        
        print("Database initialization completed!")

if __name__ == '__main__':
    init_database()
