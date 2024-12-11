import os
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, redirect, url_for, session, g, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf import CSRFProtect

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Secure random secret key
DATABASE = 'recipes.db'
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
csrf = CSRFProtect(app)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Function to check allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# Database connection
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(error):
    db = g.pop('db', None)
    if db is not None:
        db.close()


# Initialize database tables
def init_db():
    with app.app_context():
        db = get_db()
        db.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        email TEXT UNIQUE NOT NULL,
                        password TEXT NOT NULL
                      )''')

        db.execute('''CREATE TABLE IF NOT EXISTS profiles (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER UNIQUE NOT NULL,
                        bio TEXT,
                        profile_image TEXT,
                        FOREIGN KEY (user_id) REFERENCES users (id)
                      )''')

        db.execute('''CREATE TABLE IF NOT EXISTS recipes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        title TEXT NOT NULL,
                        ingredients TEXT NOT NULL, -- Ensure this line exists
                        directions TEXT NOT NULL,
                        image TEXT,
                        FOREIGN KEY (user_id) REFERENCES users (id)
                      )''')
        db.commit()


# Route: Landing Page
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')


# Route: Register
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])

        db = get_db()
        try:
            db.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
                       (username, email, password))
            db.commit()
            flash("Registration successful! Please log in.")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash("Username or Email already exists!")
            return redirect(url_for('register'))
    return render_template('register.html')


# Route: Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        db = get_db()
        user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            # Check if user has a profile
            profile = db.execute("SELECT * FROM profiles WHERE user_id = ?", (user['id'],)).fetchone()
            if profile:
                return redirect(url_for('dashboard'))
            else:
                return redirect(url_for('profile'))
        else:
            flash("Invalid email or password!")
            return redirect(url_for('login'))
    return render_template('login.html')


# Route: Profile Creation
@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    db = get_db()
    user_profile = db.execute("SELECT * FROM profiles WHERE user_id = ?", (session['user_id'],)).fetchone()
    
    if request.method == 'POST':
        bio = request.form['bio']
        # Handle profile image upload
        file = request.files.get('profile_image')
        profile_image = user_profile['profile_image'] if user_profile else None
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            profile_image = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(profile_image)
        if user_profile:
            # Update existing profile
            db.execute("UPDATE profiles SET bio = ?, profile_image = ? WHERE user_id = ?",
                       (bio, profile_image, session['user_id']))
        else:
            # Insert new profile
            db.execute("INSERT INTO profiles (user_id, bio, profile_image) VALUES (?, ?, ?)",
                       (session['user_id'], bio, profile_image))
        db.commit()
        flash("Profile updated successfully!")
        return redirect(url_for('dashboard'))
    
    return render_template('profile.html', bio=user_profile['bio'] if user_profile else "", profile_image=user_profile['profile_image'] if user_profile else "")


# Route: Dashboard (Recipe Management)
@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    db = get_db()
    if request.method == 'POST':
        title = request.form['title']
        ingredients = request.form['ingredients']
        directions = request.form['directions']
        image = None
        if 'image' in request.files:
            file = request.files['image']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                image = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(image)
        db.execute("INSERT INTO recipes (user_id, title, ingredients, directions, image) VALUES (?, ?, ?, ?, ?)",
                   (session['user_id'], title, ingredients, directions, image))
        db.commit()
        flash("Recipe posted successfully!")
        return redirect(url_for('dashboard'))

    recipes = db.execute("SELECT * FROM recipes WHERE user_id = ?", (session['user_id'],)).fetchall()
    return render_template('dashboard.html', recipes=recipes, username=session['username'])


# Route: About Me (Display Profile)
@app.route('/aboutme')
def aboutme():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    db = get_db()
    profile = db.execute("SELECT * FROM profiles WHERE user_id = ?", (session['user_id'],)).fetchone()
    
    return render_template('aboutme.html', profile=profile)


# Route: Contact
@app.route('/contact')
def contact():
    return render_template('mail.html')


# Route: Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# New Route: Delete Recipe
@app.route('/delete_recipe/<int:recipe_id>', methods=['POST'])
def delete_recipe(recipe_id):
    if 'user_id' not in session:
        flash('Please log in to delete recipes.')
        return redirect(url_for('login'))
    
    db = get_db()
    
    # Verify ownership of the recipe
    recipe = db.execute("SELECT * FROM recipes WHERE id = ? AND user_id = ?", (recipe_id, session['user_id'])).fetchone()
    
    if recipe:
        db.execute("DELETE FROM recipes WHERE id = ?", (recipe_id,))
        db.commit()
        flash('Recipe deleted successfully.')
    else:
        flash('Recipe not found or you do not have permission to delete it.')
    
    return redirect(url_for('dashboard'))


if __name__ == '__main__':
    init_db()
    app.run(debug=True)
