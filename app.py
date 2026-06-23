######################################
# VERSUS app.py — full implementation
# CS460 Final Project
######################################

import os

import flask
from flask import Flask, request, render_template, redirect, url_for, flash
import mysql.connector
import flask_login
import bcrypt
import datetime
from dotenv import load_dotenv
import math

load_dotenv()

DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_NAME = os.getenv('DB_NAME')
DB_HOST = os.getenv('DB_HOST')

app = Flask(__name__)
app.secret_key = 'super secret string'  # Change this in production!

def get_conn():
    return mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        autocommit=False,
    )

conn = get_conn()

# ---------------------------------------------------------------------------
# Login manager
# ---------------------------------------------------------------------------

login_manager = flask_login.LoginManager()
login_manager.init_app(app)


def getUserList():
    cursor = conn.cursor()
    cursor.execute("SELECT username FROM Users")
    rows = cursor.fetchall()
    cursor.close()
    return rows


class User(flask_login.UserMixin):
    pass


@login_manager.user_loader
def user_loader(username):
    users = getUserList()
    if not username or username not in str(users):
        return
    user = User()
    user.id = username
    return user


@login_manager.request_loader
def request_loader(request):
    users = getUserList()
    username = request.form.get('username')
    if not username or username not in str(users):
        return
    user = User()
    user.id = username
    cursor = conn.cursor()
    cursor.execute("SELECT password FROM Users WHERE username = '{0}'".format(username))
    data = cursor.fetchall()
    cursor.close()
    if not data:
        return user
    stored_hash = data[0][0]
    entered_pw  = request.form.get('password', '').encode('utf-8')
    user.is_authenticated = bcrypt.checkpw(entered_pw, stored_hash.encode('utf-8'))
    return user


@login_manager.unauthorized_handler
def unauthorized_handler():
    return render_template('unauth.html')


# ---------------------------------------------------------------------------
# Helper queries
# ---------------------------------------------------------------------------

def isUsernameUnique(username):
    cursor = conn.cursor()
    cursor.execute("SELECT username FROM Users WHERE username = '{0}'".format(username))
    rows = cursor.fetchall()
    cursor.close()
    return len(rows) == 0


def isEmailUnique(email):
    cursor = conn.cursor()
    cursor.execute("SELECT email FROM Users WHERE email = '{0}'".format(email))
    rows = cursor.fetchall()
    cursor.close()
    return len(rows) == 0


def getUserIdFromUsername(username):
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM Users WHERE username = '{0}'".format(username))
    row = cursor.fetchone()
    cursor.close()
    return row[0] if row else None


def getUsernameFromUserId(uid):
    cursor = conn.cursor()
    cursor.execute("SELECT username FROM Users WHERE user_id = '{0}'".format(uid))
    row = cursor.fetchone()
    cursor.close()
    return row[0] if row else None


def getCurrentUserAchievements():
    """Return achievement codes earned by the currently logged-in user."""
    if not flask_login.current_user.is_authenticated:
        return []
    uid = getUserIdFromUsername(flask_login.current_user.id)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT achievement_code FROM User_Achievements WHERE user_id = '{0}'".format(uid))
    rows = cursor.fetchall()
    cursor.close()
    return [r[0] for r in rows]


# ---------------------------------------------------------------------------
# Register / Login / Logout
# ---------------------------------------------------------------------------

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    username = request.form['username']
    cursor = conn.cursor()
    cursor.execute("SELECT password FROM Users WHERE username = '{0}'".format(username))
    data = cursor.fetchall()
    cursor.close()
    if data:
        stored_hash = data[0][0]
        entered_pw  = request.form['password'].encode('utf-8')
        if bcrypt.checkpw(entered_pw, stored_hash.encode('utf-8')):
            user = User()
            user.id = username
            flask_login.login_user(user)
            return redirect(url_for('home'))
    return render_template('login.html', error='Invalid username or password.')


@app.route('/register', methods=['GET'])
def register():
    return render_template('register.html')


@app.route('/register', methods=['POST'])
def register_user():
    username = request.form.get('username', '').strip()
    email    = request.form.get('email', '').strip()
    password = request.form.get('password', '')
    bio      = request.form.get('bio', '').strip()

    if not username or not email or not password:
        return render_template('register.html', error='All fields except bio are required.')
    if not isUsernameUnique(username):
        return render_template('register.html', error='Username already taken.')
    if not isEmailUnique(email):
        return render_template('register.html', error='Email already registered.')

    pw_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO Users (username, email, password, bio) VALUES ('{0}', '{1}', '{2}', '{3}')".format(
            username, email, pw_hash, bio))
    conn.commit()
    cursor.close()

    user = User()
    user.id = username
    flask_login.login_user(user)
    return render_template('hello.html', name=username, message='Account created!',
                           achievements=getCurrentUserAchievements())


# ---------------------------------------------------------------------------
# Home / Logout
# ---------------------------------------------------------------------------

@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        flask_login.logout_user()
        return redirect(url_for('home'))
    try:
        username = flask_login.current_user.id
        return render_template('hello.html', name=username, message='Welcome to VERSUS',
                               achievements=getCurrentUserAchievements())
    except AttributeError:
        return render_template('hello.html', message=None, achievements=[])


# ---------------------------------------------------------------------------
# Bracket creation
# ---------------------------------------------------------------------------

@app.route('/create', methods=['GET', 'POST'])
@flask_login.login_required
def create_bracket():
    if request.method == 'POST':
        uid           = getUserIdFromUsername(flask_login.current_user.id)
        title         = request.form.get('title')
        description   = request.form.get('description', '')
        entrant_count = int(request.form.get('entrant_count'))

        cursor = conn.cursor()
        # All inserts in one transaction; on failure roll back
        try:
            cursor.execute(
                "INSERT INTO Brackets (host_id, title, description, entrant_count) "
                "VALUES ('{0}', '{1}', '{2}', '{3}')".format(
                    uid, title, description, entrant_count))
            cursor.execute("SELECT LAST_INSERT_ID()")
            bracket_id = cursor.fetchone()[0]

            entrant_ids = []
            for seed in range(1, entrant_count + 1):
                name = request.form.get('entrant_' + str(seed))
                cursor.execute(
                    "INSERT INTO Entrants (bracket_id, seed, name) VALUES ('{0}', '{1}', '{2}')".format(
                        bracket_id, seed, name))
                cursor.execute("SELECT LAST_INSERT_ID()")
                entrant_ids.append(cursor.fetchone()[0])

            # Round 1: seed pairs 1v2, 3v4, ...
            round_1_slots = entrant_count // 2
            for slot in range(1, round_1_slots + 1):
                a = entrant_ids[(slot - 1) * 2]
                b = entrant_ids[(slot - 1) * 2 + 1]
                cursor.execute(
                    "INSERT INTO Matchups (bracket_id, round, slot, entrant_a_id, entrant_b_id) "
                    "VALUES ('{0}', 1, '{1}', '{2}', '{3}')".format(bracket_id, slot, a, b))

            # Shells for later rounds
            slots     = round_1_slots // 2
            round_num = 2
            while slots >= 1:
                for slot in range(1, slots + 1):
                    cursor.execute(
                        "INSERT INTO Matchups (bracket_id, round, slot) VALUES ('{0}', '{1}', '{2}')".format(
                            bracket_id, round_num, slot))
                slots     //= 2
                round_num  += 1

            conn.commit()
        except Exception as e:
            conn.rollback()
            cursor.close()
            return render_template('create.html', error=str(e))
        cursor.close()
        return redirect(url_for('view_bracket', bracket_id=bracket_id))
    return render_template('create.html')


# ---------------------------------------------------------------------------
# Browse
# ---------------------------------------------------------------------------

@app.route('/browse', methods=['GET'])
def browse():
    cursor = conn.cursor()
    cursor.execute(
        "SELECT b.bracket_id, b.title, b.status, b.entrant_count, b.created_at, u.username "
        "FROM Brackets b JOIN Users u ON b.host_id = u.user_id "
        "ORDER BY b.created_at DESC")
    brackets = cursor.fetchall()
    cursor.close()
    return render_template('browse.html', brackets=brackets)


# ---------------------------------------------------------------------------
# Bracket view (with predictions, voting, comments)
# ---------------------------------------------------------------------------

def getBracketInfo(bracket_id):
    cursor = conn.cursor()
    cursor.execute(
        "SELECT b.bracket_id, b.title, b.description, b.status, b.entrant_count, u.username, b.host_id "
        "FROM Brackets b JOIN Users u ON b.host_id = u.user_id "
        "WHERE b.bracket_id = '{0}'".format(bracket_id))
    row = cursor.fetchone()
    cursor.close()
    return row


def getMatchupsForBracket(bracket_id):
    cursor = conn.cursor()
    cursor.execute(
        "SELECT m.matchup_id, m.round, m.slot, "
        "       ea.name, eb.name, ew.name, m.votes_a, m.votes_b, "
        "       m.entrant_a_id, m.entrant_b_id, m.winner_entrant_id "
        "FROM Matchups m "
        "LEFT JOIN Entrants ea ON ea.entrant_id = m.entrant_a_id "
        "LEFT JOIN Entrants eb ON eb.entrant_id = m.entrant_b_id "
        "LEFT JOIN Entrants ew ON ew.entrant_id = m.winner_entrant_id "
        "WHERE m.bracket_id = '{0}' "
        "ORDER BY m.round, m.slot".format(bracket_id))
    rows = cursor.fetchall()
    cursor.close()
    return rows


def getUserPredictionsForBracket(user_id, bracket_id):
    """Returns {matchup_id: predicted_winner_id} for this user/bracket."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT p.matchup_id, p.predicted_winner_id "
        "FROM Predictions p "
        "JOIN Matchups m ON p.matchup_id = m.matchup_id "
        "WHERE p.user_id = '{0}' AND m.bracket_id = '{1}'".format(user_id, bracket_id))
    rows = cursor.fetchall()
    cursor.close()
    return {r[0]: r[1] for r in rows}


def getUserVotesForBracket(user_id, bracket_id):
    """Returns set of matchup_ids the user has already voted on."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT v.matchup_id FROM Votes v "
        "JOIN Matchups m ON v.matchup_id = m.matchup_id "
        "WHERE v.user_id = '{0}' AND m.bracket_id = '{1}'".format(user_id, bracket_id))
    rows = cursor.fetchall()
    cursor.close()
    return {r[0] for r in rows}


def getCommentsForMatchup(matchup_id):
    cursor = conn.cursor()
    cursor.execute(
        "SELECT c.body, u.username, c.created_at "
        "FROM Comments c JOIN Users u ON c.user_id = u.user_id "
        "WHERE c.matchup_id = '{0}' ORDER BY c.created_at".format(matchup_id))
    rows = cursor.fetchall()
    cursor.close()
    return rows


def getChampion(bracket_id):
    """Return entrant name of the champion (winner of the final matchup)."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT e.name FROM Matchups m "
        "JOIN Entrants e ON m.winner_entrant_id = e.entrant_id "
        "WHERE m.bracket_id = '{0}' "
        "ORDER BY m.round DESC LIMIT 1".format(bracket_id))
    row = cursor.fetchone()
    cursor.close()
    return row[0] if row else None


@app.route('/bracket<int:bracket_id>', methods=['GET'])
def view_bracket(bracket_id):
    bracket  = getBracketInfo(bracket_id)
    if not bracket:
        return "Bracket not found", 404
    matchups = getMatchupsForBracket(bracket_id)

    # Determine current user context
    uid             = None
    user_preds      = {}
    user_votes      = set()
    is_host         = False
    if flask_login.current_user.is_authenticated:
        uid        = getUserIdFromUsername(flask_login.current_user.id)
        user_preds = getUserPredictionsForBracket(uid, bracket_id)
        user_votes = getUserVotesForBracket(uid, bracket_id)
        is_host    = (uid == bracket[6])

    # Attach comments to round-1 matchups
    comments_by_matchup = {}
    for m in matchups:
        if m[1] == 1:  # round 1
            comments_by_matchup[m[0]] = getCommentsForMatchup(m[0])

    champion = getChampion(bracket_id) if bracket[3] == 'completed' else None

    return render_template('bracket.html',
                           bracket=bracket,
                           matchups=matchups,
                           uid=uid,
                           user_preds=user_preds,
                           user_votes=user_votes,
                           is_host=is_host,
                           comments_by_matchup=comments_by_matchup,
                           champion=champion,
                           achievements=getCurrentUserAchievements())


# ---------------------------------------------------------------------------
# Predictions
# ---------------------------------------------------------------------------

@app.route('/bracket<int:bracket_id>/predict', methods=['POST'])
@flask_login.login_required
def submit_predictions(bracket_id):
    uid = getUserIdFromUsername(flask_login.current_user.id)
    cursor = conn.cursor()
    try:
        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        # Gather all round-1 matchup IDs for this bracket
        cursor.execute(
            "SELECT matchup_id FROM Matchups WHERE bracket_id = '{0}' AND round = 1".format(bracket_id))
        matchup_ids = [r[0] for r in cursor.fetchall()]

        for mid in matchup_ids:
            winner_id = request.form.get('pred_{0}'.format(mid))
            if not winner_id:
                continue
            # INSERT OR IGNORE — let the trigger reject if bracket not predictions_open
            cursor.execute(
                "INSERT IGNORE INTO Predictions (user_id, matchup_id, predicted_winner_id, submitted_at) "
                "VALUES ('{0}', '{1}', '{2}', '{3}')".format(uid, mid, winner_id, now))
        conn.commit()
    except mysql.connector.Error as e:
        conn.rollback()
        cursor.close()
        return redirect(url_for('view_bracket', bracket_id=bracket_id,
                                error=e.msg))
    cursor.close()
    return redirect(url_for('view_bracket', bracket_id=bracket_id))


# ---------------------------------------------------------------------------
# Voting (atomic: INSERT vote + UPDATE counter in one trip)
# ---------------------------------------------------------------------------

@app.route('/bracket<int:bracket_id>/vote/<int:matchup_id>', methods=['POST'])
@flask_login.login_required
def vote(bracket_id, matchup_id):
    uid       = getUserIdFromUsername(flask_login.current_user.id)
    entrant_id = request.form.get('entrant_id')
    cursor = conn.cursor()
    try:
        # Determine which counter to bump before acquiring any lock
        cursor.execute(
            "SELECT entrant_a_id, entrant_b_id FROM Matchups WHERE matchup_id = '{0}'".format(matchup_id))
        row = cursor.fetchone()
        if not row:
            raise ValueError("Matchup not found")
        a_id, b_id = row

        cursor.execute("START TRANSACTION;")
        cursor.execute("""
        INSERT INTO Votes (user_id, matchup_id, voted_for_entrant_id) VALUES ('{0}', '{1}', '{2}');
        """.format(uid, matchup_id, entrant_id))
        if int(entrant_id) == a_id:
            cursor.execute("UPDATE Matchups SET votes_a = votes_a + 1 WHERE matchup_id = '{0}';".format(matchup_id))
        else:
            cursor.execute("UPDATE Matchups SET votes_b = votes_b + 1 WHERE matchup_id = '{0}';".format(matchup_id))
        cursor.execute("COMMIT;")
        conn.commit()
    except mysql.connector.Error:
        conn.rollback()
    cursor.close()
    return redirect(url_for('view_bracket', bracket_id=bracket_id))


# ---------------------------------------------------------------------------
# Close round (host only — calls stored procedure)
# ---------------------------------------------------------------------------

@app.route('/bracket<int:bracket_id>/close_round', methods=['POST'])
@flask_login.login_required
def close_round(bracket_id):
    uid    = getUserIdFromUsername(flask_login.current_user.id)
    bracket = getBracketInfo(bracket_id)
    if not bracket or bracket[6] != uid:
        return "Forbidden", 403

    status = bracket[3]
    if not status.startswith('round_'):
        return redirect(url_for('view_bracket', bracket_id=bracket_id))

    current_round = int(status.split('_')[1])
    cursor = conn.cursor()
    cursor.callproc('close_round', [bracket_id, current_round])
    conn.commit()
    cursor.close()
    return redirect(url_for('view_bracket', bracket_id=bracket_id))


# ---------------------------------------------------------------------------
# Advance bracket to round_1 (host only — opens voting)
# ---------------------------------------------------------------------------

@app.route('/bracket<int:bracket_id>/start', methods=['POST'])
@flask_login.login_required
def start_bracket(bracket_id):
    uid     = getUserIdFromUsername(flask_login.current_user.id)
    bracket = getBracketInfo(bracket_id)
    if not bracket or bracket[6] != uid:
        return "Forbidden", 403
    if bracket[3] != 'predictions_open':
        return redirect(url_for('view_bracket', bracket_id=bracket_id))
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE Brackets SET status = 'round_1' WHERE bracket_id = '{0}'".format(bracket_id))
    conn.commit()
    cursor.close()
    return redirect(url_for('view_bracket', bracket_id=bracket_id))


# ---------------------------------------------------------------------------
# Comments
# ---------------------------------------------------------------------------

@app.route('/bracket<int:bracket_id>/comment/<int:matchup_id>', methods=['POST'])
@flask_login.login_required
def add_comment(bracket_id, matchup_id):
    uid  = getUserIdFromUsername(flask_login.current_user.id)
    body = request.form.get('body', '').strip()
    if body:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO Comments (user_id, matchup_id, body) VALUES ('{0}', '{1}', '{2}')".format(
                uid, matchup_id, body.replace("'", "''")))
        conn.commit()
        cursor.close()
    return redirect(url_for('view_bracket', bracket_id=bracket_id))


# ---------------------------------------------------------------------------
# Profile pages
# ---------------------------------------------------------------------------

@app.route('/user/<username>')
def profile(username):
    cursor = conn.cursor()
    cursor.execute(
        "SELECT user_id, username, bio, created_at FROM Users WHERE username = '{0}'".format(username))
    user_row = cursor.fetchone()
    cursor.close()
    if not user_row:
        return "User not found", 404

    target_uid = user_row[0]

    # Aggregate prediction stats
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*), SUM(COALESCE(is_correct, 0)), SUM(COALESCE(points_earned, 0)) "
        "FROM Predictions WHERE user_id = '{0}'".format(target_uid))
    stats = cursor.fetchone()
    cursor.close()
    pred_count   = stats[0] or 0
    correct_count = int(stats[1] or 0)
    total_points  = int(stats[2] or 0)

    # Achievements
    cursor = conn.cursor()
    cursor.execute(
        "SELECT a.achievement_code, a.name, a.description, ua.achieved_at "
        "FROM User_Achievements ua JOIN Achievements a USING(achievement_code) "
        "WHERE ua.user_id = '{0}'".format(target_uid))
    achievements = cursor.fetchall()
    cursor.close()

    # Hosted brackets
    cursor = conn.cursor()
    cursor.execute(
        "SELECT bracket_id, title, status, entrant_count, created_at "
        "FROM Brackets WHERE host_id = '{0}' ORDER BY created_at DESC".format(target_uid))
    hosted = cursor.fetchall()
    cursor.close()

    # Followers (who follows this user)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT u.username FROM Follows f JOIN Users u ON f.follower_id = u.user_id "
        "WHERE f.followed_id = '{0}'".format(target_uid))
    followers = [r[0] for r in cursor.fetchall()]
    cursor.close()

    # Following (who this user follows)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT u.username FROM Follows f JOIN Users u ON f.followed_id = u.user_id "
        "WHERE f.follower_id = '{0}'".format(target_uid))
    following = [r[0] for r in cursor.fetchall()]
    cursor.close()

    # Is the current logged-in user already following this profile?
    current_uid    = None
    already_follows = False
    if flask_login.current_user.is_authenticated:
        current_uid = getUserIdFromUsername(flask_login.current_user.id)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT 1 FROM Follows WHERE follower_id = '{0}' AND followed_id = '{1}'".format(
                current_uid, target_uid))
        already_follows = cursor.fetchone() is not None
        cursor.close()

    return render_template('profile.html',
                           user_row=user_row,
                           pred_count=pred_count,
                           correct_count=correct_count,
                           total_points=total_points,
                           achievements=achievements,
                           hosted=hosted,
                           followers=followers,
                           following=following,
                           already_follows=already_follows,
                           current_uid=current_uid,
                           nav_achievements=getCurrentUserAchievements())


# ---------------------------------------------------------------------------
# User search
# ---------------------------------------------------------------------------

@app.route('/search', methods=['GET'])
def search_users():
    q = request.args.get('q', '').strip()
    results = []
    if q:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT user_id, username, bio FROM Users "
            "WHERE username LIKE '%{0}%' ORDER BY username".format(q))
        results = cursor.fetchall()
        cursor.close()

    # Which of the returned users does the current user already follow?
    following_ids = set()
    current_uid   = None
    if flask_login.current_user.is_authenticated:
        current_uid = getUserIdFromUsername(flask_login.current_user.id)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT followed_id FROM Follows WHERE follower_id = '{0}'".format(current_uid))
        following_ids = {r[0] for r in cursor.fetchall()}
        cursor.close()

    return render_template('search.html',
                           q=q,
                           results=results,
                           following_ids=following_ids,
                           current_uid=current_uid,
                           achievements=getCurrentUserAchievements())


# ---------------------------------------------------------------------------
# Follow / Unfollow
# ---------------------------------------------------------------------------

@app.route('/follow/<username>', methods=['POST'])
@flask_login.login_required
def follow_user(username):
    follower_uid = getUserIdFromUsername(flask_login.current_user.id)
    followed_uid = getUserIdFromUsername(username)
    if followed_uid and follower_uid != followed_uid:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT IGNORE INTO Follows (follower_id, followed_id) "
                "VALUES ('{0}', '{1}')".format(follower_uid, followed_uid))
            conn.commit()
        except mysql.connector.Error:
            conn.rollback()
        cursor.close()
    return redirect(url_for('profile', username=username))


@app.route('/unfollow/<username>', methods=['POST'])
@flask_login.login_required
def unfollow_user(username):
    follower_uid = getUserIdFromUsername(flask_login.current_user.id)
    followed_uid = getUserIdFromUsername(username)
    if followed_uid:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM Follows WHERE follower_id = '{0}' AND followed_id = '{1}'".format(
                follower_uid, followed_uid))
        conn.commit()
        cursor.close()
    return redirect(url_for('profile', username=username))


# ---------------------------------------------------------------------------
# Leaderboard — window functions: RANK, DENSE_RANK, PERCENT_RANK
# ---------------------------------------------------------------------------

@app.route('/leaderboard')
def leaderboard():
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            u.username,
            COALESCE(SUM(p.points_earned), 0)            AS total_points,
            RANK()         OVER (ORDER BY COALESCE(SUM(p.points_earned), 0) DESC) AS rnk,
            DENSE_RANK()   OVER (ORDER BY COALESCE(SUM(p.points_earned), 0) DESC) AS dense_rnk,
            ROUND(PERCENT_RANK() OVER (ORDER BY COALESCE(SUM(p.points_earned), 0) DESC) * 100, 1) AS pct_rnk
        FROM Users u
        LEFT JOIN Predictions p ON u.user_id = p.user_id
        GROUP BY u.user_id, u.username
        ORDER BY total_points DESC
    """)
    rows = cursor.fetchall()
    cursor.close()

    current_username = flask_login.current_user.id if flask_login.current_user.is_authenticated else None
    return render_template('leaderboard.html', rows=rows, current_username=current_username,
                           achievements=getCurrentUserAchievements())


# ---------------------------------------------------------------------------
# Champion path — recursive CTE
# ---------------------------------------------------------------------------

@app.route('/bracket<int:bracket_id>/champion_path')
def champion_path(bracket_id):
    bracket = getBracketInfo(bracket_id)
    if not bracket or bracket[3] != 'completed':
        return redirect(url_for('view_bracket', bracket_id=bracket_id))

    cursor = conn.cursor()
    # Find the final-round matchup to get the champion's entrant_id
    cursor.execute(
        "SELECT winner_entrant_id FROM Matchups "
        "WHERE bracket_id = '{0}' ORDER BY round DESC LIMIT 1".format(bracket_id))
    row = cursor.fetchone()
    if not row:
        cursor.close()
        return redirect(url_for('view_bracket', bracket_id=bracket_id))
    champion_id = row[0]

    # Recursive CTE: walk matchups from the final back through each round
    # by following winner_entrant_id to the matchup where it was either entrant_a or entrant_b
    cursor.execute("""
        WITH RECURSIVE path AS (
            -- Anchor: the final matchup (highest round)
            SELECT m.matchup_id, m.round, m.slot,
                   ea.name AS entrant_a, eb.name AS entrant_b,
                   ew.name AS winner, m.votes_a, m.votes_b
            FROM Matchups m
            JOIN Entrants ea ON ea.entrant_id = m.entrant_a_id
            JOIN Entrants eb ON eb.entrant_id = m.entrant_b_id
            JOIN Entrants ew ON ew.entrant_id = m.winner_entrant_id
            WHERE m.bracket_id = {0}
              AND m.round = (SELECT MAX(round) FROM Matchups WHERE bracket_id = {0})
              AND m.winner_entrant_id = {1}

            UNION ALL

            -- Recursive step: find the matchup in the previous round
            -- where the champion was the winner
            SELECT m.matchup_id, m.round, m.slot,
                   ea.name, eb.name,
                   ew.name, m.votes_a, m.votes_b
            FROM Matchups m
            JOIN Entrants ea ON ea.entrant_id = m.entrant_a_id
            JOIN Entrants eb ON eb.entrant_id = m.entrant_b_id
            JOIN Entrants ew ON ew.entrant_id = m.winner_entrant_id
            JOIN path p ON m.round = p.round - 1
                       AND m.bracket_id = {0}
                       AND m.winner_entrant_id = {1}
        )
        SELECT * FROM path ORDER BY round
    """.format(bracket_id, champion_id))
    path_rows = cursor.fetchall()
    cursor.close()

    champion_name = getChampion(bracket_id)
    return render_template('champion_path.html', bracket=bracket, path=path_rows,
                           champion_name=champion_name, achievements=getCurrentUserAchievements())


# ---------------------------------------------------------------------------
# Admin SQL console
# ---------------------------------------------------------------------------

@app.route('/admin', methods=['GET', 'POST'])
@flask_login.login_required
def admin():
    if flask_login.current_user.id != 'admin':
        return "Forbidden", 403
    result = None
    error  = None
    sql    = ''
    if request.method == 'POST':
        sql = request.form.get('sql', '')
        cursor = conn.cursor()
        try:
            cursor.execute(sql)
            if cursor.description:
                cols   = [d[0] for d in cursor.description]
                result = {'cols': cols, 'rows': cursor.fetchall()}
            else:
                conn.commit()
                result = {'cols': ['rows_affected'], 'rows': [(cursor.rowcount,)]}
        except mysql.connector.Error as e:
            conn.rollback()
            error = str(e)
        cursor.close()
    return render_template('admin.html', result=result, error=error, sql=sql)


if __name__ == '__main__':
    app.debug = True
    app.run(port=5001, debug=True)