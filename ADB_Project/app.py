from flask import Flask, render_template, request, redirect, url_for, flash ,session
from flask_pymongo import PyMongo
from flask_bcrypt import Bcrypt
import os
import datetime
from bson.objectid import ObjectId
from flask import jsonify
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'supersecret'
app.config['MONGO_URI'] = 'mongodb://localhost:27017/Veterinary_Appointment_System'


mongo = PyMongo(app)
bcrypt = Bcrypt(app)
db = mongo.db
admins = db['Admin']
customers = db['Customer']
vets = db['Vet']
type_collection=db['Pet_type']
appointments_collection=db['Appointments']
treatments_collection=db['Treatment']
payments_collection=db['Payments']

pets_collection=db['Pets']
@app.route('/', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        role = request.form.get('role')
        user_data = {
            'name': request.form.get('name'),
            'last_name': request.form.get('last_name'),
            'email': request.form.get('email'),
            'phone': request.form.get('phone'),
            'password': bcrypt.generate_password_hash(request.form.get('password')).decode('utf-8'),
            'street': request.form.get('street'),
            'city': request.form.get('city'),
            'state': request.form.get('state'),
            'zip': request.form.get('zip'),
            'role': role
        }

        # Add specialization only if vet
        if role == 'vet':
            user_data['specialization'] = request.form.get('specialization')
            user_data['status'] = 'inactive'  # initially inactive
            existing_user = mongo.db.vets.find_one({'email': user_data['email']})
            if existing_user:
                flash('Vet already exists with this email.', 'danger')
                return redirect(url_for('register'))
            mongo.db.Vet.insert_one(user_data)
        else:
            existing_user = mongo.db.customers.find_one({'email': user_data['email']})
            if existing_user:
                flash('Customer already exists with this email.', 'danger')
                return redirect(url_for('register'))
            mongo.db.Customer.insert_one(user_data)

        flash('Registration successful!', 'success')
        return redirect(url_for('register'))

    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')

        if not email or not password or not role:
            flash('Please fill all fields', 'danger')
            return redirect(url_for('login'))
        if role == 'Vet':
            user = vets.find_one({'email': email})
        elif role == 'Customer':
            user = customers.find_one({'email': email})

        elif role == 'Admin':
            user = admins.find_one({'email': email})

        else:
            user = None
        

        if user and bcrypt.check_password_hash(user['password'], request.form.get('password')):
            # Login success: store session info if you want
            session['user_id'] = str(user['_id'])
            session['role'] = role
            session['user_name'] = user['name']
            session['mail'] = user['email']

            # Redirect based on role
            if role == 'Vet':
                return redirect(url_for('vet_dashboard'))
            elif role == 'Customer':
                return redirect(url_for('customer_dashboard'))
            elif role == 'Admin':
                return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid email or password', 'danger')
            return redirect(url_for('login'))

    # GET request
    return render_template('login.html')

# Example dashboard routes
@app.route('/vet_dashboard')
def vet_dashboard():
    return render_template('vet_dashboard.html')

@app.route('/customer_dashboard')
def customer_dashboard():
    return render_template('customer_dashboard.html')

@app.route('/admin_dashboard')
def admin_dashboard():
    return render_template('admin_dashboard.html')

@app.route('/admin/vets/<vet_id>/approve', methods=['POST'])
def approve_vet(vet_id):
    vets.update_one({'_id': ObjectId(vet_id)}, {'$set': {'status': 'active'}})
    flash('Vet approved successfully', 'success')
    return redirect(url_for('show_vets'))

@app.route('/admin/vets/<vet_id>/reject', methods=['POST'])
def reject_vet(vet_id):
    vets.update_one({'_id': ObjectId(vet_id)}, {'$set': {'status': 'inactive'}})
    flash('Vet rejected successfully', 'warning')
    return redirect(url_for('show_vets'))

@app.route('/manage_vets')
def show_vets():
    vets = list(db['Vet'].find())  # assuming vets_collection = db['Vet']
    return render_template('show_vets.html', vets=vets)


@app.route('/create_pet', methods=['GET', 'POST'])
def create_pet():
    if request.method == 'POST':
        pet_name = request.form['pet_name'].strip()


        breed_raw = request.form.get('breed', '')  # e.g. "Golden Retriever,Labrador,Beagle"

        breed_list = [b.strip() for b in breed_raw.split(',') if b.strip()]

        existing_pet = type_collection.find_one({"name": pet_name})
        if existing_pet:
            current_breeds = set(existing_pet.get('breed', []))
            new_breeds = set(breed_list)
            breeds_to_add = list(new_breeds - current_breeds)

            if breeds_to_add:
                type_collection.update_one(
                    {"_id": existing_pet["_id"]},
                    {"$addToSet": {"breed": {"$each": breeds_to_add}}}
                )
        else:
            type_collection.insert_one({
                "name": pet_name,
                "breed": breed_list
            })

        return redirect(url_for('admin_dashboard'))

    return render_template('create_pet.html')


@app.route('/manage_appointments')
def manage_appointments():
    return render_template('manage_appointments.html')



@app.route("/cust_create_pet", methods=["GET", "POST"])
def cust_create_pet():
    if request.method == "POST":
        dob_str = request.form["dob"]  # Format: 'YYYY-MM'
        dob = datetime.strptime(dob_str, "%Y-%m")
        today = datetime.today()

        years = today.year - dob.year
        months = today.month - dob.month

        # Adjust if current month < dob month
        if months < 0:
            years -= 1
            months += 12

        age_str = f"{years}y {months}m"

        data = {
            "cust_id": session.get("user_id"),
            "name": request.form["name"],
            "type": request.form["type"],
            "breed": request.form["breed"],
            "gender": request.form["gender"],
            "allergies": request.form["allergies"],
            "dob": dob_str,          # Save the original month-year string
            "age": age_str           # Save calculated age
        }
        db.Pets.insert_one(data)
        return redirect("/customer_dashboard")

    pet_types = list(db.Pet_type.find())
    return render_template("cust_create_pet.html", pet_types=pet_types)

@app.route("/get_breeds/<type>")
def get_breeds(type):
    pet_type = db.Pet_type.find_one({"name": type})
    if pet_type:
        print(pet_type)
        return jsonify({"breeds": pet_type.get("breed", [])})
    return jsonify({"breeds": []})

@app.route("/logout")
def logout():
    session.clear()  # Clear all session data
    return redirect(url_for("login"))



@app.route('/create_appointment', methods=['GET', 'POST'])
def create_appointment():
    if request.method == 'POST':
        raw_date = request.form['date']
        selected_time = request.form['time']  # e.g., '8:30 AM'
        date_obj = datetime.strptime(raw_date, "%Y-%m-%d")
        formatted_date = date_obj.strftime("%m-%d-%Y")
        appointment = {
            'customer_id': session['user_id'],
            'pet_id': request.form['pet_id'],
            'vet': 'NA', 
            'reason': request.form['reason'],
            'date': formatted_date,
            'time': selected_time,
            'status': 'requested'
        }
        appointments_collection.insert_one(appointment)
        return redirect(url_for('customer_dashboard'))
    customer_id = session.get('user_id')
    pets = list(pets_collection.find({'cust_id': customer_id}))
    vets = list(db.Vet.find({}, {'name': 1})) 
    return render_template('create_appointment.html', customer_pets=pets, vets=vets)


@app.route('/cust_appointments')
def cust_appointments():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    customer_id = session['user_id']
    appointments = list(appointments_collection.find({'customer_id': customer_id}))

    for a in appointments:
        pet = pets_collection.find_one({'_id': ObjectId(a['pet_id'])})
        if pet:
            a['pet_name'] = pet.get('name', 'N/A')
            a['pet_age'] = pet.get('age', 'N/A')
        else:
            a['pet_name'] = 'Unknown'
            a['pet_age'] = 'Unknown'

        # Convert ObjectId to str so you can use in templates
        a['_id'] = str(a['_id'])

    return render_template('cust_appointments.html', appointments=appointments)



@app.route('/view_appointment/<appointment_id>')
def view_appointment(appointment_id):
    appointment = appointments_collection.find_one({'_id': ObjectId(appointment_id)})
    if not appointment:
        return "Appointment not found", 404

    # Get pet details
    pet = pets_collection.find_one({'_id': ObjectId(appointment['pet_id'])})
    appointment['pet_name'] = pet.get('name', 'Unknown') if pet else 'Unknown'
    appointment['pet_age'] = pet.get('age', 'Unknown') if pet else 'Unknown'
    appointment['diagnosis'] = appointment.get('diagnosis', 'TBA')
    appointment['amount'] = appointment.get('amount', 'TBA')
    appointment['vet'] = appointment.get('vet', 'TBA')


    return render_template('view_appointment.html', appointment=appointment)


@app.route('/admin_assign_appointment/<appointment_id>', methods=['POST'])
def assign_appointment(appointment_id):
    vet_name = request.form.get('vet_name')
    if not vet_name:
        flash("No vet selected.", "danger")
        return redirect(url_for('admin_assign_appointments'))

    # Fetch the appointment
    appointment = appointments_collection.find_one({'_id': ObjectId(appointment_id)})
    if not appointment:
        flash("Appointment not found.", "danger")
        return redirect(url_for('admin_assign_appointments'))

    date_selected = appointment.get('date')
    time_selected = appointment.get('time')
    old_vet_name = appointment.get('vet')

    # Free old vet's slot if assigned
    if old_vet_name:
        db.Vet.update_one(
            {'name': old_vet_name},
            {'$set': {f'appointments.{date_selected}.{time_selected}': 0}}
        )

    # Assign new vet's slot
    vet = db.Vet.find_one({'name': vet_name})
    if not vet:
        flash("Selected vet not found.", "danger")
        return redirect(url_for('admin_assign_appointments'))

    # Mark the slot as booked (1)
    db.Vet.update_one(
        {'_id': vet['_id']},
        {'$set': {f'appointments.{date_selected}.{time_selected}': 1}}
    )

    # Update appointment with new vet and status
    appointments_collection.update_one(
        {'_id': ObjectId(appointment_id)},
        {'$set': {'vet': vet_name, 'status': 'assigned'}}
    )

    flash(f"Appointment assigned to Dr. {vet_name}.", "success")
    return redirect(url_for('admin_assign_appointments'))



@app.route('/admin/delete_appointment/<appointment_id>', methods=['POST'])
def delete_appointment(appointment_id):
    appointment = appointments_collection.find_one({'_id': ObjectId(appointment_id)})
    if appointment:
        vet_name = appointment.get('vet')
        date = appointment.get('date')  # Assuming this is in "MM-DD-YY" format
        time_slot = appointment.get('time')

        # Step 2: Find vet and update their schedule
        vet = db.Vet.find_one({'name': vet_name})
        if vet:
            db.Vet.update_one(
                {'_id': vet['_id']},
               {'$set': {f'appointments.{date}.{time_slot}': 0}}
            )
    appointments_collection.update_one(
    {'_id': ObjectId(appointment_id)},
    {'$set': {'status': 'cancelled'}}
)
    flash("Appointment deleted successfully.", "success")
    return redirect(url_for('admin_assign_appointments'))

@app.route('/admin_assign_appointments')
def admin_assign_appointments():
    appointments = list(appointments_collection.find({
        "status": { "$ne": "cancelled" }
    }))
    active_vets = list(db.Vet.find({'status': 'active'}))

    for appt in appointments:
        appt['_id'] = str(appt['_id'])

        # Add pet name
        pet = pets_collection.find_one({'_id': ObjectId(appt['pet_id'])})
        appt['pet_name'] = pet.get('name', 'Unknown') if pet else 'Unknown'

        appointment_date_str = appt.get('date')  # e.g. '2024-08-06'
        appointment_time = appt.get('time')      # e.g. '8:00 AM'
        
        # Convert date string to datetime object
        try:
            appointment_date = datetime.strptime(appointment_date_str, "%m-%d-%Y")
        except Exception:
            # If date is invalid or missing, fallback to no vets available
            appt['available_vets'] = []
            continue
        print(appointment_date)
        # Get weekday name like 'Monday', 'Tuesday', etc.
        weekday = appointment_date.strftime("%A")
        print(weekday)

        available_vets = []
        for vet in active_vets:
            vet_name = vet['name']
            vet_appointments = vet.get('appointments', {})
            
            # Get schedule for the weekday (Monday, Tuesday, ...)
            day_schedule = vet_appointments.get(weekday, {})

            # Check if time slot exists and is free (0)
            if day_schedule.get(appointment_time) == 0:
                available_vets.append(vet_name)

        appt['available_vets'] = available_vets
        

    return render_template(
        'admin_assign_appointments.html',
        appointments=appointments
    )

@app.route('/vet_appointments')
def vet_appointments():
    if 'user_id' not in session or session.get('role') != 'Vet':
        flash("Access denied.", "danger")
        return redirect(url_for('login'))

    vet_id = ObjectId(session['user_id'])

    name=session['user_name']
    appointments = list(appointments_collection.find({'vet': name}))

    # Add pet name to each appointment for display
    for a in appointments:
        a['_id'] = str(a['_id'])
        pet = pets_collection.find_one({'_id': ObjectId(a['pet_id'])})
        a['pet_name'] = pet.get('name', 'Unknown') if pet else 'Unknown'

    return render_template('vet_appointments.html', appointments=appointments)

from datetime import datetime

def convert_to_db_format(date_str):
    try:
        # First try MM-DD-YYYY
        return datetime.strptime(date_str, "%m-%d-%Y").strftime("%Y-%m-%d")
    except ValueError:
        try:
            # If already in YYYY-MM-DD, just validate and return
            datetime.strptime(date_str, "%Y-%m-%d")  # just validate
            return date_str
        except ValueError:
            raise ValueError("Invalid date format. Must be MM-DD-YYYY or YYYY-MM-DD.")

@app.route('/vet_appointment/<appointment_id>', methods=['GET', 'POST'])
def vet_view_appointment(appointment_id):
    if 'user_id' not in session or session.get('role') != 'Vet':
        flash("Access denied.", "danger")
        return redirect(url_for('login'))

    appointment = appointments_collection.find_one({'_id': ObjectId(appointment_id)})
    if not appointment:
        flash("Appointment not found.", "danger")
        return redirect(url_for('vet_appointments'))

    # Fetch related pet and customer info
    pet = pets_collection.find_one({'_id': ObjectId(appointment['pet_id'])})
    customer = customers.find_one({'_id': ObjectId(appointment['customer_id'])})

    # Check if treatment already exists for this appointment
    treatment = treatments_collection.find_one({'appointment_id': ObjectId(appointment_id)})

    if request.method == 'POST':
        # Get form data
        prescription = request.form.get('prescription')
        next_date_str = request.form.get('next_date')
        notes = request.form.get('notes')
        amount = request.form.get('amount')

        # Convert next_date string to datetime or None
        next_date = next_date_str if next_date_str else None

        # If treatment exists, update it; else insert new
        if treatment:
            treatments_collection.update_one(
                {'_id': treatment['_id']},
                {'$set': {
                    'prescription': prescription,
                    'next_date': next_date,
                    'notes': notes,
                    'amount': amount
                }}
            )
            flash("Treatment updated successfully.", "success")
        else:
            treatments_collection.insert_one({
                'appointment_id': ObjectId(appointment_id),
                'pet_id': ObjectId(appointment['pet_id']),
                'customer_id': ObjectId(appointment['customer_id']),
                'prescription': prescription,
                'next_date': next_date,
                'notes': notes,
                'amount': amount
            })
            flash("Treatment added successfully.", "success")
        appointments_collection.update_one(
        {'_id': ObjectId(appointment_id)},
        {'$set': {
            'amount': amount,
            'status': 'diagnosed'
        }}
    )

        return redirect(url_for('vet_appointments'))

    return render_template('vet_appointment_detail.html', appointment=appointment, pet=pet, customer=customer, treatment=treatment)



from datetime import datetime
@app.route('/make_payment/<appointment_id>', methods=['GET', 'POST'])
def make_payment(appointment_id):
    if 'user_id' not in session or session.get('role') != 'Customer':
        flash("Access denied.", "danger")
        return redirect(url_for('login'))

    appointment = appointments_collection.find_one({'_id': ObjectId(appointment_id)})
    treatment = treatments_collection.find_one({'appointment_id': ObjectId(appointment_id)})

    if not appointment or not treatment:
        flash("Appointment or Treatment not found.", "danger")
        return redirect(url_for('dashboard'))

    base_amount = float(treatment.get('amount', 0))
    tax = round(base_amount * 0.18, 2)
    total = round(base_amount + tax, 2)

    if request.method == 'POST':
        # Collect payment info (dummy for now)
        card_name = request.form.get('card_name')
        card_number = request.form.get('card_number')
        cvv = request.form.get('cvv')
        expiry = request.form.get('expiry')
        zip_code = request.form.get('zip_code')


        # Store payment info (no actual payment gateway)
        payments_collection.insert_one({
            'appointment_id': ObjectId(appointment_id),
            'customer_id': appointment['customer_id'],
            'amount': base_amount,
            'tax': tax,
            'total': total,
            'payment_date': datetime.now().strftime("%m-%d-%y"),
            'card_name': card_name,
            'card_number': card_number[-4:],  # last 4 digits
            'zip_code': zip_code
        })

        # Mark appointment as paid
        appointments_collection.update_one(
            {'_id': ObjectId(appointment_id)},
            {'$set': {'status': 'Paid'}}
        )

        flash("Payment successful!", "success")
        return redirect(url_for('customer_dashboard'))

    return render_template('payment.html', appointment=appointment, treatment=treatment, tax=tax, total=total)


@app.route('/customer_payments')
def customer_payments():
    if 'user_id' not in session or session.get('role') != 'Customer':
        flash("Please login to view payments.", "danger")
        return redirect(url_for('login'))

    customer_id = session['user_id']
    print(customer_id)
    # Get all payments for this customer
    payments = list(payments_collection.find({'customer_id': customer_id}))
    print(payments)

    # For each payment, add appointment details
    for payment in payments:
        appointment = appointments_collection.find_one({'_id': payment['appointment_id']})
        if appointment:
            payment['appointment_date'] = appointment.get('date', 'N/A')
            payment['appointment_time'] = appointment.get('time', 'N/A')
        else:
            payment['appointment_date'] = 'N/A'
            payment['appointment_time'] = 'N/A'
            payment['pet_name'] = 'N/A'

    return render_template('customer_payments.html', payments=payments)




@app.route('/admin_payments')
def admin_payments():
    payments = list(payments_collection.find())

    # For each payment, add appointment details
    for payment in payments:
        appointment = appointments_collection.find_one({'_id': payment['appointment_id']})
        if appointment:
            payment['appointment_date'] = appointment.get('date', 'N/A')
            payment['appointment_time'] = appointment.get('time', 'N/A')
        else:
            payment['appointment_date'] = 'N/A'
            payment['appointment_time'] = 'N/A'
            payment['pet_name'] = 'N/A'

    return render_template('admin_payments.html', payments=payments)


@app.route('/customer_pets')
def customer_pets():
    if 'user_id' not in session or session.get('role') != 'Customer':
        flash("Please login to view your pets.", "danger")
        return redirect(url_for('login'))

    customer_id = session['user_id']
    pets = list(pets_collection.find({'cust_id': customer_id}))
    return render_template('customer_pets.html', pets=pets)

@app.route('/customer_pets/delete/<pet_id>', methods=['POST'])
def delete_pet(pet_id):
    if 'user_id' not in session or session.get('role') != 'Customer':
        flash("Access denied.", "danger")
        return redirect(url_for('login'))

    pets_collection.delete_one({'_id': ObjectId(pet_id)})
    flash('Pet deleted successfully.', 'success')
    return redirect(url_for('customer_pets'))


@app.route('/report/view/<appointment_id>')
def view_report(appointment_id):
    if 'user_id' not in session:
        flash("Please login to view the report.", "danger")
        return redirect(url_for('login'))

    appointment = appointments_collection.find_one({'_id': ObjectId(appointment_id)})
    treatment = treatments_collection.find_one({'appointment_id': ObjectId(appointment_id)})
    pet = pets_collection.find_one({'_id': ObjectId(appointment['pet_id'])})
    customer = customers.find_one({'_id': ObjectId(appointment['customer_id'])})

    if not (appointment and treatment and pet and customer):
        flash("Required data not found.", "danger")
        return redirect(url_for('customer_dashboard'))

    return render_template("prescription_report.html", 
                           appointment=appointment, 
                           treatment=treatment, 
                           pet=pet, 
                           customer=customer)


@app.route('/vets_review', methods=['GET', 'POST'])
def vets_review():
    vets = list(db.Vet.find())  # or add filter for pending approval
    return render_template('vets_review.html', vets=vets)

@app.route('/vet_status/<vet_id>/<action>', methods=['POST'])
def vet_status(vet_id, action):
    if action == 'approve':
        db.Vet.update_one({'_id': ObjectId(vet_id)}, {'$set': {'status': 'active'}})
    elif action == 'reject':
        db.Vet.update_one({'_id': ObjectId(vet_id)}, {'$set': {'status': 'inactive'}})
    return redirect(url_for('vets_review'))

@app.route('/cancel_appointment/<appointment_id>', methods=['POST'])
def cancel_appointment(appointment_id):
        
    appointments_collection.delete_one({'_id': ObjectId(appointment_id)})

    flash('Appointment cancelled successfully.', 'success')
    return redirect(url_for('cust_appointments'))


@app.route('/open_slots', methods=['GET', 'POST'])
def open_slots():
    vet_id = session['user_id']

    if request.method == 'POST':
        weekday = request.form['weekday']  # e.g. "Monday"
        selected_times = request.form.getlist('times[]')  # list of selected time slots

        # Create dictionary for that day with all selected slots set to 0 (available)
        appointments_for_day = {slot: 0 for slot in selected_times}

        # Update vet document, set appointments.day = appointments_for_day
        db.Vet.update_one(
            {"_id": ObjectId(vet_id)},
            {"$set": {f"appointments.{weekday}": appointments_for_day}},
            upsert=True
        )

        return redirect(url_for('manage_appointments'))

    return render_template('slots.html')



@app.route('/get_sessions/<date>', methods=['GET'])
def get_sessions(date):
    vet_id = session.get('user_id')
    vet = db.Vet.find_one({"_id": ObjectId(vet_id)})
    date_obj = datetime.strptime(date, "%Y-%m-%d")
    formatted_date = date_obj.strftime("%m-%d-%Y")
    if not vet or 'appointments' not in vet:
        return jsonify({})

    return jsonify(vet['appointments'].get(formatted_date, {}))


@app.route('/edit_appointment', methods=['GET', 'POST'])
def edit_appointment():


    vet_id = session['user_id']
    if request.method == 'POST':
        date_selected = request.form['date']
        date_obj = datetime.strptime(date_selected, "%Y-%m-%d")
        date_selected = date_obj.strftime("%m-%d-%Y")
        selected_sessions = request.form.getlist('times')
        new_sessions = {session: 0 for session in selected_sessions}

        # Replace the entire date's sessions with new_sessions
        db.Vet.update_one(
            {"_id": ObjectId(vet_id)},
            {"$set": {f"appointments.{date_selected}": new_sessions}}
        )

    return render_template('edit_appointment.html')

if __name__ == '__main__':
    app.run(debug=True)
