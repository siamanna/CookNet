import os
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, redirect, url_for, session, g, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with a strong secret key
DATABASE = 'recipes.db'
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

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
                        id INTEGER PRIMARY KEY,
                        username TEXT UNIQUE NOT NULL,
                        email TEXT UNIQUE NOT NULL,
                        password TEXT NOT NULL)''')

        db.execute('''CREATE TABLE IF NOT EXISTS recipes (
                        id INTEGER PRIMARY KEY,
                        user_id INTEGER NOT NULL,
                        title TEXT NOT NULL,
                        ingredients TEXT NOT NULL,
                        directions TEXT NOT NULL,
                        image TEXT,
                        FOREIGN KEY (user_id) REFERENCES users (id))''')
        db.commit()


# Route: Homepage
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))  # Redirect to login if not logged in
    return render_template('index.html', username=session['username'])


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
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash ("Username or Email already exists!")
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
            return redirect(url_for('index'))  # Redirect to homepage after login
        else:
            return "Invalid email or password!"
    return render_template('login.html')


# Route: Dashboard (Post Recipes)
@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    db = get_db()
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        db.execute("INSERT INTO recipes (user_id, title, content) VALUES (?, ?, ?)",
                   (session['user_id'], title, content))
        db.commit()

    recipes = db.execute("SELECT * FROM recipes WHERE user_id = ?", (session['user_id'],)).fetchall()
    return render_template('dashboard.html', recipes=recipes, username=session['username'])

@app.route('/about')
def about():
    return render_template('aboutme.html')

@app.route('/contact')
def contact():
    return render_template('mail.html')

@app.route('/post_recipe', methods=['GET', 'POST'])
def post_recipe():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form['title']
        ingredients = request.form['ingredients']
        directions = request.form['directions']
        file = request.files['image']

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

            db = get_db()
            db.execute("INSERT INTO recipes (user_id, title, ingredients, directions, image) VALUES (?, ?, ?, ?, ?)",
                       (session['user_id'], title, ingredients, directions, file_path))
            db.commit()
            flash("Recipe posted successfully!")
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid file format. Please upload an image.")

    return render_template('post_recipe.html')


# Route: Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


if __name__ == '__main__':
    init_db()
    app.run(debug=True)
