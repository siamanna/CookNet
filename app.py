import os
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, redirect, url_for, session, g, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import imghdr
import bleach

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Secure random secret key
DATABASE = 'recipes.db'
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB upload limit

# Function to check allowed file extensions
def allowed_file(filename):
    if '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS:
        # Further validate the file content
        return True
    return False

def validate_image(stream):
    header = stream.read(512)  # Read first 512 bytes
    stream.seek(0)  # Reset stream pointer
    format = imghdr.what(None, header)
    if not format:
        return False
    if format.lower() in ALLOWED_EXTENSIONS:
        return True
    return False

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
                        name TEXT,
                        age INTEGER,
                        bio TEXT,
                        profile_image TEXT,
                        facebook TEXT,
                        instagram TEXT,
                        x TEXT,
                        linkedin TEXT,
                        website TEXT,
                        FOREIGN KEY (user_id) REFERENCES users (id)
                      )''')

        db.execute('''CREATE TABLE IF NOT EXISTS recipes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        title TEXT NOT NULL,
                        ingredients TEXT NOT NULL,
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
        username = bleach.clean(request.form['username'])
        email = bleach.clean(request.form['email'])
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
        email = bleach.clean(request.form['email'])
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
        bio = bleach.clean(request.form['bio'])
        # Handle profile image upload
        file = request.files.get('profile_image')
        profile_image = user_profile['profile_image'] if user_profile else None
        if file and allowed_file(file.filename):
            if validate_image(file.stream):
                filename = secure_filename(file.filename)
                profile_image = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(profile_image)
            else:
                flash('Invalid image file.')
                return redirect(url_for('profile'))
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

# Route: Dashboard (Displays All Recipes)
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    db = get_db()

    # Fetch recipes from all users
    recipes = db.execute('''SELECT recipes.*, users.username 
                             FROM recipes 
                             JOIN users ON recipes.user_id = users.id 
                             ORDER BY recipes.id DESC''').fetchall()

    return render_template('dashboard.html', recipes=recipes, username=session['username'])

# Route: Post Recipe
@app.route('/post_recipe', methods=['GET', 'POST'])
def post_recipe():
    if 'user_id' not in session:
        flash('Please log in to post a recipe.')
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = bleach.clean(request.form['title'])
        ingredients = bleach.clean(request.form['ingredients'])
        directions = bleach.clean(request.form['directions'])
        image = None

        if 'image' in request.files:
            file = request.files['image']
            if file and allowed_file(file.filename) and validate_image(file.stream):
                filename = secure_filename(file.filename)
                image = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(image)
            else:
                flash('Invalid image file.')
                return redirect(url_for('post_recipe'))

        db = get_db()
        db.execute("INSERT INTO recipes (user_id, title, ingredients, directions, image) VALUES (?, ?, ?, ?, ?)",
                   (session['user_id'], title, ingredients, directions, image))
        db.commit()
        flash("Recipe posted successfully!")
        return redirect(url_for('dashboard'))

    return render_template('post_recipe.html')

# Route: Edit Recipe
@app.route('/edit_recipe/<int:recipe_id>', methods=['GET', 'POST'])
def edit_recipe(recipe_id):
    if 'user_id' not in session:
        flash('Please log in to edit recipes.')
        return redirect(url_for('login'))

    db = get_db()
    recipe = db.execute("SELECT * FROM recipes WHERE id = ? AND user_id = ?", (recipe_id, session['user_id'])).fetchone()

    if not recipe:
        flash('Recipe not found or you do not have permission to edit it.')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        title = bleach.clean(request.form['title'])
        ingredients = bleach.clean(request.form['ingredients'])
        directions = bleach.clean(request.form['directions'])
        image = recipe['image']  # Keep existing image by default

        if 'image' in request.files:
            file = request.files['image']
            if file and allowed_file(file.filename):
                if validate_image(file.stream):
                    filename = secure_filename(file.filename)
                    image = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(image)
                else:
                    flash('Invalid image file.')
                    return redirect(url_for('edit_recipe', recipe_id=recipe_id))

        db.execute('''UPDATE recipes 
                      SET title = ?, ingredients = ?, directions = ?, image = ?
                      WHERE id = ? AND user_id = ?''',
                   (title, ingredients, directions, image, recipe_id, session['user_id']))
        db.commit()
        flash('Recipe updated successfully!')
        return redirect(url_for('dashboard'))

    return render_template('edit_recipe.html', recipe=recipe)

# Route: About Me (Display Profile)
@app.route('/aboutme')
def aboutme():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    db = get_db()
    profile = db.execute("SELECT * FROM profiles WHERE user_id = ?", (session['user_id'],)).fetchone()
    
    return render_template('aboutme.html', profile=profile)

# Route: Contact
@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        # Handle contact form submission (e.g., send email)
        # Implement your email sending logic here
        flash('Your message has been sent successfully!')
        return redirect(url_for('thankyou'))
    return render_template('mail.html')

# Route: Thank You Page
@app.route('/thankyou')
def thankyou():
    return render_template('thankyou.html')

# Route: Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# Route: Delete Recipe
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

@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    if 'user_id' not in session:
        flash('Please log in to edit your profile.')
        return redirect(url_for('login'))

    db = get_db()
    user_id = session['user_id']

    # Fetch existing profile
    profile = db.execute("SELECT * FROM profiles WHERE user_id = ?", (user_id,)).fetchone()

    if request.method == 'POST':
        # Sanitize and retrieve form data
        name = bleach.clean(request.form.get('name', ''))
        age = bleach.clean(request.form.get('age', ''))
        bio = bleach.clean(request.form.get('bio', ''))
        facebook = bleach.clean(request.form.get('facebook', ''))
        instagram = bleach.clean(request.form.get('instagram', ''))
        x = bleach.clean(request.form.get('x', ''))
        linkedin = bleach.clean(request.form.get('linkedin', ''))
        website = bleach.clean(request.form.get('website', ''))

        # Handle profile image upload
        profile_image = profile['profile_image'] if profile else None
        if 'profile_image' in request.files:
            file = request.files['profile_image']
            if file and allowed_file(file.filename):
                if validate_image(file.stream):
                    filename = secure_filename(file.filename)
                    # Ensure the uploads directory exists
                    if not os.path.exists(app.config['UPLOAD_FOLDER']):
                        os.makedirs(app.config['UPLOAD_FOLDER'])
                    image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(image_path)
                    profile_image = image_path
                else:
                    flash('Invalid image file.')
                    return redirect(url_for('edit_profile'))
            elif file.filename == '' and not profile:
                # If no file is uploaded and no existing profile image, make it required
                flash('Profile image is required.')
                return redirect(url_for('edit_profile'))

        if profile:
            # Update existing profile
            db.execute('''UPDATE profiles 
                          SET name = ?, age = ?, bio = ?, profile_image = ?, 
                              facebook = ?, instagram = ?, x = ?, linkedin = ?, website = ?
                          WHERE user_id = ?''',
                       (name, age, bio, profile_image, facebook, instagram, x, linkedin, website, user_id))
        else:
            # Create new profile
            db.execute('''INSERT INTO profiles 
                          (user_id, name, age, bio, profile_image, facebook, instagram, x, linkedin, website)
                          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                       (user_id, name, age, bio, profile_image, facebook, instagram, x, linkedin, website))
        db.commit()
        flash('Profile updated successfully!')
        return redirect(url_for('dashboard'))

    return render_template('edit_profile.html', profile=profile)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
