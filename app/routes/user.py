from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models import Flight, Booking
from datetime import datetime

user_bp = Blueprint('user', __name__)

@user_bp.route('/')
def index():
    return render_template('index.html')

@user_bp.route('/flights')
def flights():
    page = request.args.get('page', 1, type=int)
    source = request.args.get('source', '')
    destination = request.args.get('destination', '')
    date = request.args.get('date', '')

    query = Flight.query

    if source:
        query = query.filter(Flight.source.ilike(f'%{source}%'))
    if destination:
        query = query.filter(Flight.destination.ilike(f'%{destination}%'))
    if date:
        try:
            date_obj = datetime.strptime(date, '%Y-%m-%d').date()
            query = query.filter(Flight.date == date_obj)
        except ValueError:
            pass
            
    # Filter out past flights
    query = query.filter(Flight.date >= datetime.utcnow().date())
    
    pagination = query.order_by(Flight.date.asc(), Flight.time.asc()).paginate(page=page, per_page=10, error_out=False)
    
    return render_template('flights.html', flights=pagination.items, pagination=pagination, source=source, destination=destination, date=date)

@user_bp.route('/book/<int:flight_id>', methods=['GET', 'POST'])
@login_required
def book(flight_id):
    flight = Flight.query.get_or_404(flight_id)
    
    if request.method == 'POST':
        seats_to_book = int(request.form.get('seats', 1))
        
        if seats_to_book <= 0:
            flash('Invalid number of seats', 'danger')
            return redirect(url_for('user.book', flight_id=flight_id))
            
        if seats_to_book > flight.seats:
            flash('Not enough seats available', 'danger')
            return redirect(url_for('user.book', flight_id=flight_id))
            
        total_price = seats_to_book * flight.price
        
        import razorpay
        from flask import current_app
        client = razorpay.Client(auth=(current_app.config['RAZORPAY_KEY_ID'], current_app.config['RAZORPAY_KEY_SECRET']))
        
        order_amount = int(total_price * 100)
        order_currency = 'INR'
        
        try:
            payment_order = client.order.create(dict(amount=order_amount, currency=order_currency, payment_capture='1'))
            order_id = payment_order['id']
            
            booking = Booking(
                user_id=current_user.id,
                flight_id=flight.id,
                seats_booked=seats_to_book,
                total_price=total_price,
                order_id=order_id,
                status='pending'
            )
            
            db.session.add(booking)
            db.session.commit()
            
            return render_template('payment.html', booking=booking, order_amount=order_amount, key_id=current_app.config['RAZORPAY_KEY_ID'])
            
        except Exception as e:
            flash(f'Razorpay Error: {str(e)}', 'danger')
            return redirect(url_for('user.book', flight_id=flight_id))
            
    return render_template('booking.html', flight=flight)

@user_bp.route('/payment/verify', methods=['POST'])
@login_required
def payment_verify():
    import razorpay
    from flask import current_app
    
    razorpay_payment_id = request.form.get('razorpay_payment_id')
    razorpay_order_id = request.form.get('razorpay_order_id')
    razorpay_signature = request.form.get('razorpay_signature')
    
    booking = Booking.query.filter_by(order_id=razorpay_order_id, user_id=current_user.id).first()
    if not booking:
        flash('Booking not found', 'danger')
        return redirect(url_for('user.my_bookings'))
        
    client = razorpay.Client(auth=(current_app.config['RAZORPAY_KEY_ID'], current_app.config['RAZORPAY_KEY_SECRET']))
    
    try:
        client.utility.verify_payment_signature({
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature': razorpay_signature
        })
        
        # Payment is successful
        booking.status = 'paid'
        booking.payment_id = razorpay_payment_id
        
        # Now decrement seats safely
        flight = Flight.query.get(booking.flight_id)
        if flight:
            flight.seats -= booking.seats_booked
            
        db.session.commit()
        
        flash('Payment successful! Booking confirmed.', 'success')
        return render_template('booking_confirmation.html', booking=booking)
        
    except razorpay.errors.SignatureVerificationError:
        booking.status = 'failed'
        db.session.commit()
        flash('Payment verification failed. Please try again.', 'danger')
        return redirect(url_for('user.book', flight_id=booking.flight_id))

@user_bp.route('/my_bookings')
@login_required
def my_bookings():
    bookings = Booking.query.filter_by(user_id=current_user.id).order_by(Booking.timestamp.desc()).all()
    return render_template('my_bookings.html', bookings=bookings, current_time=datetime.utcnow().date())

@user_bp.route('/cancel_booking/<int:booking_id>', methods=['POST'])
@login_required
def cancel_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    
    if booking.user_id != current_user.id:
        flash('Unauthorized action', 'danger')
        return redirect(url_for('user.my_bookings'))
        
    flight = Flight.query.get(booking.flight_id)
    if flight:
        flight.seats += booking.seats_booked
        
    db.session.delete(booking)
    db.session.commit()
    
    flash('Booking cancelled successfully', 'success')
    return redirect(url_for('user.my_bookings'))

@user_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        gender = request.form.get('gender')
        phone = request.form.get('phone')
        dob_str = request.form.get('dob')
        
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        
        # Update name and email
        if name:
            current_user.name = name
        if email and email != current_user.email:
            # Check if email is already taken
            existing_user = db.session.query(type(current_user)).filter_by(email=email).first()
            if existing_user:
                flash('Email address already registered to another account.', 'danger')
                return redirect(url_for('user.profile'))
            current_user.email = email
            
        # Update professional details
        if gender:
            current_user.gender = gender
        if phone:
            current_user.phone = phone
        if dob_str:
            from datetime import datetime
            try:
                current_user.dob = datetime.strptime(dob_str, '%Y-%m-%d').date()
            except ValueError:
                pass
            
        # Update password if provided
        if new_password:
            if not current_password or not current_user.check_password(current_password):
                flash('Incorrect current password. Password not changed.', 'danger')
                return redirect(url_for('user.profile'))
            current_user.set_password(new_password)
            flash('Profile and password updated successfully!', 'success')
        else:
            flash('Profile updated successfully!', 'success')
            
        db.session.commit()
        return redirect(url_for('user.profile'))
        
    return render_template('profile.html')
