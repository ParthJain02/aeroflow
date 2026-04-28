from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user
from app import db
from app.models import User

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('user.index'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        if user is None or not user.check_password(password):
            flash('Invalid email or password', 'danger')
            return redirect(url_for('auth.login'))
            
        login_user(user)
        flash(f'Welcome back, {user.name}!', 'success')
        
        if user.is_admin:
            return redirect(url_for('admin.dashboard'))
        
        next_page = request.args.get('next')
        if not next_page or not next_page.startswith('/'):
            next_page = url_for('user.index')
        return redirect(next_page)
        
    return render_template('auth/login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('user.index'))
        
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash('Passwords must match', 'danger')
            return redirect(url_for('auth.register'))
            
        if User.query.filter_by(email=email).first():
            flash('Email address already registered', 'warning')
            return redirect(url_for('auth.register'))
            
        user = User(name=name, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('auth.login'))
        
    return render_template('auth/register.html')

@auth_bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('user.index'))

@auth_bp.route('/google', methods=['POST'])
def google_auth():
    from google.oauth2 import id_token
    from google.auth.transport import requests as google_requests
    from flask import current_app
    
    token = request.form.get('credential')
    try:
        # Verify the token
        idinfo = id_token.verify_oauth2_token(
            token, google_requests.Request(), current_app.config['GOOGLE_CLIENT_ID'])

        # Get user info from the payload
        email = idinfo['email']
        name = idinfo.get('name', 'Google User')

        # Check if user exists
        user = User.query.filter_by(email=email).first()
        
        if not user:
            # Create a new user account without a password (since they use Google)
            import secrets
            user = User(name=name, email=email)
            # Set a random impossible password so they can't login via normal form
            user.set_password(secrets.token_urlsafe(32))
            db.session.add(user)
            db.session.commit()
            flash('Account created successfully via Google!', 'success')
        else:
            flash(f'Welcome back, {user.name}!', 'success')

        login_user(user)
        return redirect(url_for('user.index'))

    except ValueError:
        # Invalid token
        flash('Invalid Google Sign-In token.', 'danger')
        return redirect(url_for('auth.login'))
