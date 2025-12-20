from app import app, db
from datetime import datetime

# This script manually creates/updates the database tables.
# Run this once when you first set up the project or move to a new database.

with app.app_context():
    try:
        # Create all tables
        db.create_all()
        
        # Check and add missing columns to Booking table
        from sqlalchemy import inspect, text
        
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('booking')]
        
        # Add new columns if they don't exist
        if 'booking_date' not in columns:
            db.session.execute(text('ALTER TABLE booking ADD COLUMN booking_date DATE'))
            print("Added booking_date column")
        
        if 'booking_time' not in columns:
            db.session.execute(text('ALTER TABLE booking ADD COLUMN booking_time VARCHAR(50)'))
            print("Added booking_time column")
        
        if 'duration' not in columns:
            db.session.execute(text('ALTER TABLE booking ADD COLUMN duration INTEGER DEFAULT 60'))
            print("Added duration column")
        
        if 'meeting_link' not in columns:
            db.session.execute(text('ALTER TABLE booking ADD COLUMN meeting_link VARCHAR(500)'))
            print("Added meeting_link column")
        
        if 'notes' not in columns:
            db.session.execute(text('ALTER TABLE booking ADD COLUMN notes TEXT'))
            print("Added notes column")
        
        # Add new columns to User table if they don't exist
        user_columns = [col['name'] for col in inspector.get_columns('user')]
        
        if 'profile_views' not in user_columns:
            db.session.execute(text('ALTER TABLE user ADD COLUMN profile_views INTEGER DEFAULT 0'))
            print("Added profile_views column")
        
        if 'link_clicks' not in user_columns:
            db.session.execute(text('ALTER TABLE user ADD COLUMN link_clicks INTEGER DEFAULT 0'))
            print("Added link_clicks column")
        
        db.session.commit()
        print("SUCCESS: Database tables created/updated successfully!")
        
        # Add admin user if not exists
        from app import User
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', email='admin@clearq.in', role='admin')
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print("Admin user created successfully!")
            
    except Exception as e:
        print(f"ERROR: Could not create/update database. Reason: {e}")
        db.session.rollback()
