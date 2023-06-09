from flask import Flask, render_template, request, session, redirect, url_for
import subprocess
import pandas as pd
import pyodbc
import os
import cv2
import detect_face_shape
from PIL import Image
import numpy as np
import dlib
import urllib.request
import base64

#!! B191200021 B181200560
#!! You need to install http://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2 and place in the main folder alongside haar cascade.

app = Flask(__name__)

app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'

cnxn = pyodbc.connect('DRIVER={ODBC Driver 17 for SQL Server};SERVER=DESKTOP-U9C3P6H;DATABASE=hairsaloonusers;Trusted_Connection=yes')
cursor = cnxn.cursor()

# Create the users table if it doesn't exist
query = '''
IF OBJECT_ID('users', 'U') IS NULL
    CREATE TABLE users (
        id INT IDENTITY PRIMARY KEY,
        name VARCHAR(255),
        email VARCHAR(255),
        password VARCHAR(255)
    )
'''

cursor.execute(query)
cnxn.commit()

@app.route('/')
def default():
    return redirect('/register')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Retrieve the form data
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        # Validate the form data
        import re
        if not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            return render_template('register.html', error='Invalid email')
        if len(password) < 8:
            return render_template('register.html', error='Password must be at least 8 characters long')

        # Insert a new row into the users table
        query = 'USE hairsaloonusers INSERT INTO users (name, email, password) VALUES (?, ?, ?)'
        cursor.execute(query, (name, email, password))
        cnxn.commit()

        print(f'Inserted {name}, {email}, {password} into the users table')

        # Redirect to the login page
        return redirect('/login')
    else:
        # Render the register template
        return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Retrieve the form data
        email = request.form['email']
        password = request.form['password']

        # Check if the email and password match an entry in the users table
        query = 'SELECT * FROM users WHERE email = ? AND password = ?'
        cursor.execute(query, (email, password))
        user = cursor.fetchone()

        # If a match is found, log the user in
        if user:
            # Set session variables for the user
            session['user_id'] = user[0]
            session['user_name'] = user[1]
            session['authenticated'] = True
            return redirect('/submit')

        else:
            return render_template('login.html', error='Invalid email or password')
    else:
        # Render the login template
        return render_template('login.html')

@app.route('/submit', methods=['GET', 'POST'])
def submit():
    if 'authenticated' in session and session['authenticated']:
        # User is authenticated, render the button page template
        return render_template('submit.html', name=session['user_name'])
    else:
        # User is not authenticated, redirect to the login page
        return redirect('/login')
    
@app.route('/save_user', methods=['POST'])
def save_user():
    # Get the uploaded image
    image = request.files['image']
    image.save('hairsaloon/user_images/image.png')
    session['gender'] = request.form.get('gender')
    session['age'] = request.form.get('age')
    session['faceshape'] = detect_face_shape.detection()  # Assuming detect_face_shape.detection() returns the face shape
    # Construct the path to the image directory
    image_dir = fr"hairsaloon/static/{session['gender']}/{session['age']}/{session['faceshape']}.csv"

    df = pd.read_csv(image_dir)
    return render_template('result.html', image_dir=image_dir, name=session['user_name'], faceshape=session['faceshape'], df=df)

@app.route('/choose_image', methods=['POST'])
def choose_image():
  row_number = int(request.form['row_number'])
  filepath =('hairsaloon/user_images/image1.png')
  image = ('hairsaloon/user_images/image.png')
  image_dir = fr"hairsaloon/static/{session['gender']}/{session['age']}/{session['faceshape']}.csv"
  df = pd.read_csv(image_dir)
  image_dir = df.iloc[row_number]['hairstyle']
  urllib.request.urlretrieve(image_dir, filepath)
  # Load the input images
  image1 = cv2.imread(filepath)
  image2 = cv2.imread(image)
  # Convert the images to grayscale
  gray1 = cv2.cvtColor(image1, cv2.COLOR_BGR2GRAY)
  gray2 = cv2.cvtColor(image2, cv2.COLOR_BGR2GRAY)
  # Load the pre-trained face detector and landmark predictor from dlib
  detector = dlib.get_frontal_face_detector()
  predictor = dlib.shape_predictor('hairsaloon/shape_predictor_68_face_landmarks.dat')
  # Detect faces and landmarks in the images
  faces1 = detector(gray1)
  faces2 = detector(gray2)
  # Make sure that exactly one face is detected in each image
  if len(faces1) != 1 or len(faces2) != 1:
      print("Error: Exactly one face should be detected in each image.")
      exit()
  # Extract the facial landmarks for the first face
  landmarks1 = predictor(gray1, faces1[0])
  landmarks1 = np.array([(p.x, p.y) for p in landmarks1.parts()])
  # Extract the facial landmarks for the second face
  landmarks2 = predictor(gray2, faces2[0])
  landmarks2 = np.array([(p.x, p.y) for p in landmarks2.parts()])
  # Calculate the affine transformation matrix for the faces alignment
  transformation_matrix = cv2.estimateAffinePartial2D(landmarks2, landmarks1)[0]
  # Apply the affine transformation to the second face
  face2_aligned = cv2.warpAffine(image2, transformation_matrix, (image1.shape[1], image1.shape[0]), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
  # Swap the faces while preserving the hairstyle
  image_swapped = image1.copy()
  image_swapped[faces1[0].top():faces1[0].bottom(), faces1[0].left():faces1[0].right()] = face2_aligned[faces1[0].top():faces1[0].bottom(), faces1[0].left():faces1[0].right()]
  # Save the processed images
  cv2.imwrite('hairsaloon/processed/proccessed_image.jpg', image_swapped) 
  _, img_encoded = cv2.imencode('.jpg', image_swapped)
  image_base64 = base64.b64encode(img_encoded).decode('utf-8')
  print("Faces saved as 'processed_image.jpg'")
  return render_template('Hairstyle.html', image_base64=image_base64)

@app.route('/result')
def result():

    image_dir = fr"hairsaloon/static/{session['gender']}/{session['age']}/{session['faceshape']}.csv"
    df = pd.read_csv(image_dir)
    return render_template('result.html', image_dir=image_dir, name=session['user_name'], faceshape=session['faceshape'], df=df)

@app.route('/logout')
def logout():
    # Remove the authenticated user's information from the session
    session.pop('authenticated', None)
    session.pop('email', None)
    session.pop('name', None)
    
    # Redirect to the login page
    return redirect('/login')
  
if __name__ == '__main__':
    app.run(host="localhost", port=int("5000"))