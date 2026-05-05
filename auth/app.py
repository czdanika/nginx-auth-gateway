from flask import Flask, request, redirect, render_template, make_response
import hmac
import hashlib
import os
import time

app = Flask(__name__)

# USERS env format: "dani:Strava,anna:Password2"
# Each user can optionally have a backend: "dani:Strava:app:8080"
# Default backend fallback: APP_BACKEND (default: app:8080)

SECRET          = os.environ.get('COOKIE_SECRET', 'change-this-secret-key')
COOKIE_NAME     = 'strava_auth'
COOKIE_DAYS     = int(os.environ.get('COOKIE_DAYS', '30'))
DEFAULT_BACKEND = os.environ.get('APP_BACKEND', 'app:8080')
LANGUAGE        = os.environ.get('LANGUAGE', 'en').lower()

TRANSLATIONS = {
    'en': {
        'lang':        'en',
        'title':       'Strava Statistics',
        'subtitle':    'Enter your credentials to sign in',
        'username':    'Username',
        'password':    'Password',
        'button':      'Sign in',
        'error':       'Invalid credentials. Please try again.',
        'footer':      'Statistics for Strava',
    },
    'hu': {
        'lang':        'hu',
        'title':       'Strava Statisztikák',
        'subtitle':    'Add meg az adataidat a belépéshez',
        'username':    'Felhasználónév',
        'password':    'Jelszó',
        'button':      'Belépés',
        'error':       'Hibás adatok. Próbáld újra.',
        'footer':      'Statistics for Strava',
    },
}

def get_i18n() -> dict:
    return TRANSLATIONS.get(LANGUAGE, TRANSLATIONS['en'])


def load_users() -> dict:
    """Returns {username: {'password': ..., 'backend': ...}}"""
    users = {}
    for entry in os.environ.get('USERS', '').split(','):
        entry = entry.strip()
        if not entry:
            continue
        parts = entry.split(':')
        if len(parts) >= 2:
            username = parts[0].strip().lower()
            password = parts[1].strip()
            backend  = ':'.join(parts[2:]).strip() if len(parts) > 2 else DEFAULT_BACKEND
            users[username] = {'password': password, 'backend': backend}
    return users


def make_token(username: str) -> str:
    expire  = str(int(time.time()) + COOKIE_DAYS * 86400)
    payload = f"{expire}:{username}"
    sig     = hmac.new(SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{expire}.{username}.{sig}"


def verify_token(token: str):
    """Returns username on success, None on failure."""
    try:
        expire, username, sig = token.split('.', 2)
        if int(expire) < time.time():
            return None
        payload  = f"{expire}:{username}"
        expected = hmac.new(SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
        if hmac.compare_digest(sig, expected):
            return username
        return None
    except Exception:
        return None


@app.route('/auth/verify')
def verify():
    token    = request.cookies.get(COOKIE_NAME, '')
    username = verify_token(token)
    if username:
        users   = load_users()
        backend = users.get(username, {}).get('backend', DEFAULT_BACKEND)
        resp    = make_response('', 200)
        resp.headers['X-Auth-User']    = username
        resp.headers['X-Auth-Backend'] = backend
        return resp
    return '', 401


@app.route('/login', methods=['GET'])
def login():
    return render_template('login.html', error=False, i18n=get_i18n())


@app.route('/login', methods=['POST'])
def login_post():
    username = request.form.get('username', '').strip().lower()
    password = request.form.get('password', '')
    users    = load_users()

    if username in users and users[username]['password'] == password:
        token = make_token(username)
        resp  = make_response(redirect('/'))
        resp.set_cookie(
            COOKIE_NAME, token,
            max_age=COOKIE_DAYS * 86400,
            httponly=True,
            samesite='Strict',
        )
        return resp
    return render_template('login.html', error=True, i18n=get_i18n()), 401


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
