from app import create_app, db
from app.models import User, Flight
from datetime import datetime, timedelta
import random

app = create_app()

def create_sample_data():
    with app.app_context():
        db.drop_all()
        db.create_all()

        # Create Admin User
        admin = User(name='Admin User', email='admin@aeroflow.com', is_admin=True)
        admin.set_password('admin123')
        
        # Create Normal User
        user = User(name='John Doe', email='john@example.com', is_admin=False)
        user.set_password('password123')
        
        db.session.add(admin)
        db.session.add(user)
        
        # Create Sample Flights
        cities = ['Mumbai', 'Delhi', 'Bangalore', 'Hyderabad', 'Chennai', 'Kolkata', 'Pune', 'Ahmedabad', 'Jaipur', 'Goa']
        
        today = datetime.utcnow().date()
        
        for _ in range(20):
            source = random.choice(cities)
            dest = random.choice([c for c in cities if c != source])
            
            # Flights from today up to 30 days in future
            days_ahead = random.randint(0, 30)
            flight_date = today + timedelta(days=days_ahead)
            
            # Random time
            hour = random.randint(0, 23)
            minute = random.choice([0, 15, 30, 45])
            flight_time = datetime.strptime(f'{hour}:{minute}', '%H:%M').time()
            
            seats = random.randint(5, 200)
            price = round(random.uniform(2500.0, 15000.0), 2)
            
            flight = Flight(
                source=source,
                destination=dest,
                date=flight_date,
                time=flight_time,
                seats=seats,
                price=price
            )
            db.session.add(flight)

        db.session.commit()
        print("Sample data created successfully!")
        print("Admin Login -> Email: admin@aeroflow.com | Password: admin123")
        print("User Login  -> Email: john@example.com | Password: password123")

if __name__ == '__main__':
    create_sample_data()
