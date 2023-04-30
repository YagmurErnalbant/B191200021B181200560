from flask import Flask, render_template, request, session, redirect, url_for
import subprocess
import pandas as pd
import pyodbc
import os
import detect_face_shape
from PIL import Image

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
            # Check if the user is an admin
            if user[1] == 'admin':
                session['authenticated'] = True
                session['user_id'] = user[0]
                session['user_name'] = user[1]
                # Redirect the admin to the admin page
                return redirect('/admin')
            else:
                # Set session variables for a regular user
                session['user_id'] = user[0]
                session['user_name'] = user[1]
                session['authenticated'] = True
                return redirect('/submit')

        else:
            return render_template('login.html', error='Invalid email or password')
    else:
        # Render the login template
        return render_template('login.html')

@app.route('/admin')
def admin():
    # Check if the user is authenticated and has the admin role
    if 'authenticated' in session and session['authenticated'] and session['user_name'] == 'admin':
        # Connect to the database and retrieve a list of all registered users
        # Replace 'database_name' and 'table_name' with the actual names of your database and table

        cursor.execute('SELECT * FROM users')
        users = cursor.fetchall()

        # Render the admin template with the list of users
        return render_template('admin.html', users=users)
    else:
        # User is not authenticated or does not have the admin role, redirect to the button page
        return redirect('/login')

@app.route('/add', methods=['POST'])
def add_user():
    # Check if the user is authenticated and has the admin role
    if 'authenticated' in session and session['authenticated'] and session['user_name'] == 'admin':
        # Retrieve the form data
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        # Insert the new user into the database
        query = 'INSERT INTO users (name, email, password) VALUES (?, ?, ?)'
        cursor.execute(query, (name, email, password))
        cnxn.commit()

        # Redirect the admin back to the admin page
        return redirect('/admin')
    else:
        # User is not authenticated or does not have the admin role, redirect to the button page
        return redirect('/login')

@app.route('/delete', methods=['POST'])
def delete(email):
    # Check if the user is authenticated and has the admin role
    if 'authenticated' in session and session['authenticated'] and session['user_name'] == 'admin':
        # Retrieve the form data
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        cursor.execute('DELETE FROM users WHERE name = ?, email = ?, password = ?')
        cnxn.commit()

        # Redirect to the admin dashboard
        return redirect('/admin')
    else:
        # User is not authenticated or does not have the admin role, redirect to the button page
        return redirect('/login')

@app.route('/update', methods=['POST'])
def update():
    # Check if the user is authenticated and has the admin role
    if 'authenticated' in session and session['authenticated'] and session['user_name'] == 'admin':
        # Retrieve the form data
        email = request.form['email']
        name = request.form['name']
        password = request.form['password']

        # Update the user's name and password in the database using their email as the identifier
        query = 'UPDATE users SET name = ?, password = ? WHERE email = ?'
        cursor.execute(query, (name, password, email))
        cnxn.commit()

        # Redirect the admin to the admin page
        return redirect('/admin')
    else:
        # User is not authenticated or does not have the admin role, redirect to the button page
        return redirect('/login')

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
    faceshape = detect_face_shape.detection()
    gender = request.form.get('gender')
    age = request.form.get('age')

    # Get the uploaded image
    image = request.files['image']

    # Construct the path to the image directory
    image_dir = f"C:\\Users\\yagmu\\OneDrive\\Masaüstü\\hairsaloon\\gallery\\{gender}\\{age}\\{faceshape}"

    # Get a list of all image files in the directory
    image_files = [f for f in os.listdir(image_dir) if f.endswith('.jpg') or f.endswith('.png')]

    return render_template('result.html', image_dir=image_dir, image_files=image_files)



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
