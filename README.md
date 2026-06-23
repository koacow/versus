# VERSUS

A simple tournament bracket creation and management application. Built with Flask and MySQL.

## What is in here

- `app.py` — Flask app with register, login, logout, create bracket, browse, view, etc
- `schema.sql` — database schema and stored procedures
- `templates/` — HTML templates
- `static/` — static files (CSS)
- `requirements.txt` — Python dependencies

## Setup

1. Install MySQL and start the server. Create the database from the
   skeleton schema:

   ```
   mysql -u root -p < schema.sql
   ```

2. Create a `.env` file following the format in `.env.example`:

   ```
   DB_USER=your_username
   DB_PASSWORD=your_password
   DB_NAME=your_database
   DB_HOST=localhost
   SECRET_KEY=your_secret_key
   ```

3. Create a Python virtual environment and install the dependencies:

   ```
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

4. Run the app:

   ```
   python app.py
   ```

5. Open http://127.0.0.1:5000/ in your browser. Register an account,
   create a bracket, and view it.

