from flask import Flask, render_template, request, redirect,jsonify, session, url_for
import cv2
import numpy as np
import datetime
import base64
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from google.cloud.firestore_v1.base_query import FieldFilter
from flask_session import Session


app = Flask(__name__)
cred = credentials.Certificate("moodbook.json")
firebase_admin.initialize_app(cred)
db = firestore.client()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Load pre-trained face and smile cascade classifiers
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
smile_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_smile.xml')

# Open log file in append mode
log_file = open('emotion_log.txt', 'a')

@app.route('/')
def intro():
    return render_template('intro.html')

@app.route('/signup')
def signup():
    return render_template('registration final.html')

@app.route('/register', methods=['POST'])
def register():
    name = request.form.get('name')
    surname = request.form.get('surname')
    age = request.form.get('age')
    gender = request.form.get('gender')
    email = request.form.get('email')
    password = request.form.get('password')
    confirm_password = request.form.get('confirm_password')

    if password and confirm_password and password == confirm_password:
        user_data = {
            'name': name,
            'surname': surname,
            'age': age,
            'gender': gender,
            'email': email,
            'password': password,
        }
        # Add a new document with auto-generated ID to a 'users' collection
        db.collection("users").document(request.form["email"]).set(user_data)
        # Passwords match, redirect to home page
        return redirect('/login')
    else:
        # Passwords don't match or one of them is missing
        return render_template('registration.html', error="Passwords do not match")

@app.route('/login')
def login():
    return render_template('login final.html')

@app.route('/login', methods=['POST'])
def authenticate():
    email = request.form.get('email')
    password = request.form.get('password')
 
    #var1 = tostring(email)
    #<p>{{var1}}</p>
    # Query Firestore for user with provided username
    users_ref = db.collection('users')
    query = users_ref.where('email', '==', email).where('password', '==', password).limit(1).stream()
    user = next(query, None)
    if user:
        # Successful login, redirect to home page with email as URL parameter
        return redirect(url_for('home', email=email))
    else:
        # Incorrect email or password
        return 'Incorrect email or password'
    
    # This part of the code will never be reached, so you can remove it
    # User does not exist
    # return render_template('login.html', error='User does not exist. Please sign up.')

@app.route('/home')
def home():
    image_data = request.args.get('image')
    email=request.args.get('email')
    print(f"Image data: {image_data} Email: {email}")
    if email:
        return render_template('home.html', image_data=image_data, email=email)
    else:
        return render_template('home.html' )
    # Use the email to customize the user's experience, retrieve data, etc.

@app.route('/add_entry', methods=['POST'])
def handle_ajax_request():
    # Process the data as needed
    data = request.get_json()
    # Process data and post it to Firebase
    #user_ref = db.collection('users').where('email', '==', user_email).limit(1)
    #entry_ref = db.collection('users').document(user_id).collection('entries').add({})
    
    #currentemail=db.collection('users').document(session['email']).get()
    date = data.get('date')
    category = data.get('category')
    feedback = data.get('feedback')
    email = data.get('email') 
    #email=session['email']
    #email = data.get('email')
    #user_ref = db.collection('users').where('email', '==', email).limit(1)
    #user_data = user_ref.stream()
    #for user in user_data:
    # Insert the data into Firestore
    doc_ref = db.collection("entries").document()
    entry = {
        "id": doc_ref.id,  
        "date": date,  
        "category": category,  
        "feedback": feedback,
        "email": email
    }
    doc_ref.set(entry)
    # Return a response which includes the ID of the newly created document
    return jsonify({'id': category}) 
#write a code to get the data back

@app.route('/entries')
def get_entries():
    email = current_user.email
    print(email)
        # Get the entries for this user from Firestore
    entries_ref = db.collection('users').where('email','==', email).limit(1)
    entries = entries_ref.get()
    
    # Initialize a list to store the entries
    all_entries = []

    # Loop through each entry and append it to the list
    for entry in entries:
        entry_data = entry.to_dict()
        all_entries.append(entry_data)

    # Render a template to display the entries
    return render_template('home.html', entries=all_entries)   

@app.route('/get_entries', methods=['GET'])
def get_entries_fake():
    """Get entries from the database"""
    user_email = session['email']
    print(f"User Email is :{user_email}")
    # Retrieve all documents under collection 'entries' where the field 'email' matches the current user's email
    user_doc = db.collection('users')
    user_data = user_doc.get()
    for data in user_data:
        print('{} => {}'.format(doc.id, doc.to_dict()))    
    
    return (jsonify([doc.to_dict() for doc in user_data]))
        
    # Get the user's email from the session or wherever it's stored after login
    # For demonstration purposes, let's assume it's stored as a variable 'user_email'
    user_email = request.form.get('email')  # Modify this to get email from login session

    # Retrieve user's ID from Firestore using email
    user_ref = db.collection('users').where('email', '==', user_email).limit(1)
    user_data = user_ref.stream()
    for user in user_data:
        user_id = user.id

        # Retrieve entries from Firestore under the user's ID
        entries_ref = db.collection('users').document(user_id).collection('entries').get()
        entries = [doc.to_dict() for doc in entries_ref]

        return jsonify({'entries': entries})

    return jsonify({'error': 'User not found'})

@app.route('/logout')
def logout():
    # Clear the session, effectively logging the user out
    session["email"]= None
    return redirect('/intro')
           
@app.route('/detect_emotion', methods=['POST'])
def detect_emotion():
    try:
        # Decode base64 image from request
        image_data = request.json['image'].split(',')[1]
        nparr = np.frombuffer(base64.b64decode(image_data), np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        # Convert image to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Detect faces in the image
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5)

        # Detect smiles or frowns in each face
        for (x, y, w, h) in faces:
            face_roi = gray[y:y+h, x:x+w]
            smile = smile_cascade.detectMultiScale(face_roi, scaleFactor=1.7, minNeighbors=20)

            # Check if smile or frown is detected
            if len(smile) > 0:
                detected_emotion = 'Smile'
            else:
                detected_emotion = 'Frown'
                
            print(f"Detected emotion: {detected_emotion}")  # Debugging statement

            # Log the detected emotion with timestamp
            log_entry = f"{detected_emotion} detected at {datetime.datetime.now()}\n"
            print(log_entry)  # Debugging statement
            log_file.write(log_entry)
            log_file.flush()  # Ensure data is written immediately
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True)