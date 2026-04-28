from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models import Flight, Booking, User
from functools import wraps
from datetime import datetime

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('user.index'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    total_flights = Flight.query.count()
    total_bookings = Booking.query.count()
    total_users = User.query.count()
    revenue = db.session.query(db.func.sum(Booking.total_price)).scalar() or 0.0
    
    return render_template('admin/dashboard.html', 
                           total_flights=total_flights,
                           total_bookings=total_bookings,
                           total_users=total_users,
                           revenue=revenue)

@admin_bp.route('/flights')
@login_required
@admin_required
def manage_flights():
    flights = Flight.query.order_by(Flight.date.desc()).all()
    return render_template('admin/manage_flights.html', flights=flights)

@admin_bp.route('/flight/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_flight():
    if request.method == 'POST':
        source = request.form.get('source')
        destination = request.form.get('destination')
        date_str = request.form.get('date')
        time_str = request.form.get('time')
        seats = int(request.form.get('seats'))
        price = float(request.form.get('price'))
        
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        time_obj = datetime.strptime(time_str, '%H:%M').time()
        
        flight = Flight(
            source=source,
            destination=destination,
            date=date_obj,
            time=time_obj,
            seats=seats,
            price=price
        )
        
        db.session.add(flight)
        db.session.commit()
        
        flash('Flight added successfully!', 'success')
        return redirect(url_for('admin.manage_flights'))
        
    return render_template('admin/add_flight.html')

@admin_bp.route('/flight/edit/<int:flight_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_flight(flight_id):
    flight = Flight.query.get_or_404(flight_id)
    
    if request.method == 'POST':
        flight.source = request.form.get('source')
        flight.destination = request.form.get('destination')
        
        date_str = request.form.get('date')
        time_str = request.form.get('time')
        flight.date = datetime.strptime(date_str, '%Y-%m-%d').date()
        flight.time = datetime.strptime(time_str, '%H:%M:%S' if len(time_str) > 5 else '%H:%M').time()
        
        flight.seats = int(request.form.get('seats'))
        flight.price = float(request.form.get('price'))
        
        db.session.commit()
        flash('Flight updated successfully!', 'success')
        return redirect(url_for('admin.manage_flights'))
        
    return render_template('admin/edit_flight.html', flight=flight)

@admin_bp.route('/flight/delete/<int:flight_id>', methods=['POST'])
@login_required
@admin_required
def delete_flight(flight_id):
    flight = Flight.query.get_or_404(flight_id)
    # also delete related bookings or handle constraints
    Booking.query.filter_by(flight_id=flight.id).delete()
    db.session.delete(flight)
    db.session.commit()
    flash('Flight deleted successfully', 'success')
    return redirect(url_for('admin.manage_flights'))

@admin_bp.route('/bookings')
@login_required
@admin_required
def view_bookings():
    bookings = Booking.query.order_by(Booking.timestamp.desc()).all()
    return render_template('admin/view_bookings.html', bookings=bookings)
