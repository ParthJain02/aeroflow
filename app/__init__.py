from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import Config

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)

    # Register blueprints
    from app.routes.user import user_bp
    from app.routes.admin import admin_bp
    from app.routes.auth import auth_bp

    app.register_blueprint(user_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(auth_bp)

    with app.app_context():
        db.create_all()
        
        # Ensure default admin exists
        from app.models import User
        if not User.query.filter_by(email='admin@aeroflow.com').first():
            admin_user = User(name='Admin', email='admin@aeroflow.com', is_admin=True)
            admin_user.set_password('admin123')
            db.session.add(admin_user)
            db.session.commit()
            
        # Ensure some sample flights exist
        from app.models import Flight
        from datetime import datetime, timedelta
        if Flight.query.count() == 0:
            sample_flights = [
                Flight(source='Mumbai', destination='Delhi', date=(datetime.now() + timedelta(days=2)).date(), time='08:00', seats=60, price=5500.0),
                Flight(source='Delhi', destination='Goa', date=(datetime.now() + timedelta(days=3)).date(), time='10:30', seats=45, price=7200.0),
                Flight(source='Bangalore', destination='Mumbai', date=(datetime.now() + timedelta(days=1)).date(), time='14:15', seats=50, price=4800.0),
                Flight(source='Hyderabad', destination='Bangalore', date=(datetime.now() + timedelta(days=5)).date(), time='18:45', seats=30, price=3500.0),
                Flight(source='Kolkata', destination='Delhi', date=(datetime.now() + timedelta(days=2)).date(), time='11:00', seats=55, price=6200.0)
            ]
            db.session.bulk_save_objects(sample_flights)
            db.session.commit()

    return app
