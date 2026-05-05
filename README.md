# statistics-for-strava – Login Gateway

A password-protected login screen for [robiningelbrecht/strava-statistics](https://github.com/robiningelbrecht/strava-statistics), built with **nginx `auth_request`** and **Python Flask**.

Protects your personal Strava statistics dashboard from public access — with a clean, Strava-themed login UI.

## Features

- 🔐 Password-protected access — no one sees your stats without logging in
- 👥 Multi-user support — each user can be routed to their own strava-statistics container
- 🍪 HMAC-signed cookies (30-day sessions by default)
- 🎨 Strava-themed glassmorphism login page
- ⚙️ Zero config files — everything via environment variables

## How it works

```
Browser → nginx (port 80/443)
              │
              ├─ GET /login  ──────────────► Flask auth service
              ├─ POST /login ──────────────► Flask auth service
              │                                   │ sets HMAC cookie
              │                                   ▼
              └─ GET /* ──► auth_request ──► /auth/verify
                                │                 │ returns X-Auth-Backend
                                │                 ▼
                                └──────────► strava-statistics app
```

## Quick start

Add the `auth` and `nginx` services to your existing `strava-statistics` `docker-compose.yml`:

```yaml
  auth:
    image: python:3.12-alpine
    container_name: strava-auth
    restart: unless-stopped
    working_dir: /app
    volumes:
      - ./auth:/app
      - pip-cache:/root/.cache/pip
    environment:
      USERS: "${USERS}"
      COOKIE_SECRET: "${COOKIE_SECRET}"
      COOKIE_DAYS: "30"
      APP_BACKEND: "app:8080"
    command: sh -c "pip install flask --quiet && python app.py"

  nginx:
    image: nginx:alpine
    container_name: strava-nginx
    restart: unless-stopped
    ports:
      - "80:80"
    volumes:
      - ./auth/nginx.conf:/etc/nginx/conf.d/default.conf:ro
    depends_on:
      - app
      - auth

volumes:
  pip-cache: {}
```

Then remove the `ports` mapping from your `app` service — nginx handles that now.

Create a `.env` file (never commit this):

```env
USERS=yourname:YourPassword
COOKIE_SECRET=change-this-to-a-long-random-string
```

Copy the `auth/` folder from this repo next to your `docker-compose.yml` and restart the stack.

## Configuration

All configuration lives in `.env`:

| Variable | Description | Example |
|---|---|---|
| `USERS` | Comma-separated `user:password` or `user:password:host:port` | `alice:Secret1` |
| `COOKIE_SECRET` | Random string for signing cookies — `openssl rand -hex 32` | |
| `COOKIE_DAYS` | Session length in days | `30` |
| `APP_BACKEND` | Default backend if not set per-user | `app:8080` |
| `LANGUAGE` | Login page language: `en` or `hu` | `en` |

### Multiple users, each with their own strava-statistics container

If someone else in your household also uses Strava, you can run a separate `strava-statistics` instance for them and route each user to their own container:

```env
USERS=alice:Password1:app-alice:8080,bob:Password2:app-bob:8080
```

nginx reads the `X-Auth-Backend` header returned by the auth service and proxies dynamically — no nginx restart needed when adding users.

## Bypassing auth for Strava webhooks

If you use the strava-statistics webhook feature, add this to `auth/nginx.conf` before the catch-all `location /`:

```nginx
location = /strava/webhook {
    proxy_pass http://app:8080;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

## Customising the login page

Edit `auth/templates/login.html`. The background image is at the top of the `<style>` block:

```css
background-image: url('https://images.unsplash.com/photo-XXXXXXXXXXXXXXXX?w=1920&q=85');
```

Replace with any cycling photo from [Unsplash](https://unsplash.com/s/photos/cycling).

## Security notes

- Cookies are `HttpOnly` and `SameSite=Strict`
- Signatures use `hmac.compare_digest` to prevent timing attacks
- Never commit your `.env` file — it is in `.gitignore`

## License

MIT
