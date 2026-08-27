# Videoflix Backend

A RESTful backend for **Videoflix**, a video streaming platform in the style of
Netflix. Users register, confirm their account by email and stream videos via
**HLS** in three resolutions. Uploaded videos are converted in the background
with FFmpeg, built with Django and the Django REST Framework.

Authentication runs entirely on **JWT stored in HttpOnly cookies**, so a
browser client never has to store a token itself. The whole stack runs in
**Docker**: PostgreSQL, Redis and Django with a Gunicorn server and two RQ
workers. The frontend is provided by the Developer Akademie and lives in
[project.Videoflix](https://github.com/Developer-Akademie-Backendkurs/project.Videoflix);
everything behind `/api/` is this project.

![Videoflix API documentation](assets/preview.png)

---

## Features

- JWT authentication via **HttpOnly cookies** (register, activate, login, logout, refresh)
- Refresh tokens are **blacklisted** on logout and cannot be reused
- **Account activation by email**, accounts stay inactive until the link is used
- **Password reset by email**, without ever revealing whether an address exists
- Responsive **HTML emails** with the logo embedded in the message itself
- Automatic **HLS conversion** to 480p, 720p and 1080p after an upload
- **Thumbnail** extracted from the middle of the video, no manual upload needed
- Conversion and email delivery run in the background with **Django RQ**,
  emails on a `high` and conversions on a `low` priority queue
- Deleting a video removes its source file, thumbnail and all HLS files
- Auto-generated OpenAPI 3 documentation (Swagger UI & ReDoc) via drf-spectacular

---

## Tech Stack

**Backend**

<p align="left">
  <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/python/python-original.svg" height="40" alt="python logo" />
  <img width="12" />
  <img src="https://cdn.jsdelivr.net/gh/B-Blarr/B-Blarr@main/assets/django.svg" height="40" alt="django logo" />
  <img width="12" />
  <img src="https://cdn.jsdelivr.net/gh/B-Blarr/B-Blarr@main/assets/drf.svg?v=2" height="40" alt="django rest framework logo" />
  <img width="12" />
  <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/postgresql/postgresql-original.svg" height="40" alt="postgresql logo" />
  <img width="12" />
  <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/redis/redis-original.svg" height="40" alt="redis logo" />
  <img width="12" />
  <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/docker/docker-original.svg" height="40" alt="docker logo" />
</p>

| Component        | Version                                       |
| ---------------- | --------------------------------------------- |
| Language         | Python 3.12 (`python:3.12-alpine`)            |
| Framework        | Django 6.1                                    |
| API              | Django REST Framework 3.18.0                  |
| Database         | PostgreSQL 18 (`postgres:18`)                 |
| Cache            | Redis via django-redis 7.0.0                  |
| Background tasks | django-rq 4.1.1 (Redis backed)                |
| Auth             | djangorestframework-simplejwt 5.5.1 (cookies) |
| Video processing | FFmpeg (bundled in the image)                 |
| WSGI server      | Gunicorn 26.0.0 behind WhiteNoise 6.12.0      |
| API docs         | drf-spectacular 0.30.0 (OpenAPI 3)            |

---

## Project Structure

```
videoflix_backend/
├── core/                # Project settings, root URL config, WSGI/ASGI
├── auth_app/            # Registration, activation, login, logout, password reset
│   ├── api/             # serializers.py, views.py, urls.py, authentication.py, utils.py
│   ├── templates/       # HTML emails for activation and password reset
│   ├── utils.py         # Token and link building, email delivery
│   └── signals.py       # Queues the activation email on registration
├── video_app/           # Video model, listing and HLS delivery
│   ├── api/             # serializers.py, views.py, urls.py
│   ├── utils.py         # FFmpeg calls, path helpers, conversion pipeline
│   └── signals.py       # Queues the conversion, cleans up on delete
├── docker-compose.yml
├── backend.Dockerfile
├── backend.entrypoint.sh
└── requirements.txt
```

---

## Getting Started

### Prerequisites

- **Docker Desktop**, nothing else. Python, PostgreSQL, Redis and FFmpeg all
  live inside the containers.

> ⚠️ **Give Docker enough memory.** Encoding 1080p with x264 needs well over
> 1.5 GB of RAM. On Windows with the WSL 2 backend, Docker Desktop has no
> memory slider, the limit comes from `%USERPROFILE%\.wslconfig`:
>
> ```ini
> [wsl2]
> memory=8GB
> swap=2GB
> ```
>
> Apply it with `wsl --shutdown`, then restart Docker Desktop. With too little
> memory the conversion job is killed by the system and the video ends up with
> the status `failed`, without an obvious reason in the logs.

### Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/B-Blarr/Videoflix-Backend.git
   cd Videoflix-Backend
   ```

2. **Set up your environment file**, copy the provided template, then fill in
   your own values. The `.env` file itself is git-ignored.

   Windows (PowerShell):

   ```powershell
   Copy-Item .env.template .env
   ```

   macOS / Linux:

   ```bash
   cp .env.template .env
   ```

   | Variable                   | Description                                             |
   | -------------------------- | ------------------------------------------------------- |
   | `SECRET_KEY`               | Django secret key, required                             |
   | `DJANGO_SUPERUSER_*`       | Admin account created on the first start                |
   | `DEBUG`                    | Present in the template, but currently not read (see below) |
   | `DB_*`                     | PostgreSQL name, user and password                      |
   | `REDIS_LOCATION`           | Connection URL used by the cache                        |
   | `REDIS_HOST/PORT/DB`       | Connection used by the RQ queues                        |
   | `EMAIL_HOST`, `EMAIL_PORT` | SMTP server used to send mail                           |
   | `EMAIL_HOST_USER`          | SMTP user                                               |
   | `EMAIL_HOST_PASSWORD`      | SMTP password                                           |
   | `EMAIL_USE_TLS` / `_SSL`   | Transport encryption, `True` or `False`                 |
   | `DEFAULT_FROM_EMAIL`       | Sender address of all outgoing mail                     |
   | `ALLOWED_HOSTS`            | Comma separated hostnames                               |
   | `CSRF_TRUSTED_ORIGINS`     | Comma separated frontend origins                        |

   Generate a secret key with:

   ```bash
   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
   ```

   Four more settings are read from the environment but are not part of the
   template, because their defaults already work. Add them to your `.env` if
   you need to change them:

   | Variable        | Default                                       | Purpose                                |
   | --------------- | --------------------------------------------- | -------------------------------------- |
   | `FRONTEND_URL`  | `http://127.0.0.1:5500`                       | Base URL used in the email links       |
   | `COOKIE_SECURE` | `False`                                       | Set to `True` when serving over HTTPS  |
   | `EMAIL_BACKEND` | `django.core.mail.backends.smtp.EmailBackend` | Swap it for local development          |
   | `CORS_ALLOWED_ORIGINS` | `http://localhost:5500,http://127.0.0.1:5500` | Origins allowed to send credentials |

   During development it is convenient to print mails to the log instead of
   sending them:

   ```
   EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
   ```

3. **Start the stack**

   ```bash
   docker compose up --build
   ```

   The first start builds the image, waits for PostgreSQL, applies all
   migrations, creates the superuser from your `.env` and launches Gunicorn
   together with two RQ workers.

   The API is now available at `http://127.0.0.1:8000/`.

4. **Follow the logs** in a second terminal, this is where the conversion
   progress shows up and, with the console backend, the emails:

   ```bash
   docker compose logs -f web
   ```

Useful commands while the stack is running:

```bash
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py makemigrations
docker compose exec web python manage.py migrate
docker compose exec web sh
```

> Changes to Python files take effect immediately in the web process, Gunicorn
> reloads them. **The two RQ workers do not reload**, they load their code once
> at startup, so changes to `video_app/utils.py` or `auth_app/utils.py` only
> apply after `docker compose restart web`. Changes to `requirements.txt` need
> `docker compose up --build`.

---

## Adding Videos

Videos are not uploaded through the API, there is no endpoint for it. They are
added in the Django admin at `http://127.0.0.1:8000/admin/`, using the email
address and password of your superuser.

Create a video with a title, description, category and the video file itself.
Saving it queues a background job which

1. extracts a thumbnail from the middle of the video,
2. converts the file to HLS in 480p, 720p and 1080p,
3. and sets the status to `done`.

**Replacing the video file of an existing entry queues the job again.** The old
HLS folder and the replaced source file are removed, so nothing of the previous
video survives. Editing only the title, description or category changes nothing
about the conversion.

All three resolutions are always produced, even when the source is smaller. A
360p upload is therefore scaled up to 1080p, which costs encoding time without
gaining quality. The reason is the frontend: its resolution dropdown is
hardcoded to the three values and the API does not expose which resolutions
exist, so a missing one would leave the player on a black screen.

The status of a video is visible on its detail page in the admin. Any failure
sets the status to `failed` and the job is passed on to RQ, so the traceback
shows up in the dashboard at `http://127.0.0.1:8000/django-rq/`. A video is
never left on `processing`, not even when the job exceeds its timeout: RQ
raises a `JobTimeoutException` that the job handles like any other error.

Timeouts are set in `core/settings.py` and are meant as emergency brakes
against a stuck ffmpeg, not as capacity planning:

| Setting                 | Value | Covers                                    |
| ----------------------- | ----- | ----------------------------------------- |
| `HLS_ENCODE_TIMEOUT`    | 2 h   | one resolution, roughly a 3 hour movie    |
| `HLS_THUMBNAIL_TIMEOUT` | 60 s  | the single thumbnail frame                |
| `HLS_JOB_TIMEOUT`       | 6.5 h | the whole job, passed to `enqueue()`      |

Measured in this container, encoding all three resolutions costs about
1.6 seconds of CPU time per second of video, and 1080p alone about 0.7. On a
small VPS, expect roughly half that throughput.

---

## Frontend

This repository contains the backend only. The matching frontend is provided
by the Developer Akademie:

```bash
git clone https://github.com/Developer-Akademie-Backendkurs/project.Videoflix.git
```

It is plain HTML, CSS and JavaScript, so any static file server will do. The
simplest way is the **Live Server** extension in VS Code: right-click
`index.html` and choose *Open with Live Server*.

> ⚠️ **Open the frontend at `http://127.0.0.1:5500`, not at
> `http://localhost:5500`.** Browsers treat `localhost` and `127.0.0.1` as two
> different sites. Since the API lives on `127.0.0.1:8000`, using `localhost`
> for the frontend makes the auth cookies cross-site, and without
> `SameSite=None; Secure`, which is impossible over plain HTTP, the browser
> discards them. The login returns `200` and you still are not logged in.

The origin the frontend is served from has to be listed in
`CORS_ALLOWED_ORIGINS`. Both `localhost:5500` and `127.0.0.1:5500` are covered
by the default.

---

## Tests

Run the full test suite:

```bash
docker compose exec web python manage.py test
```

Measure test coverage (target: **≥ 95 %**):

```bash
docker compose exec web coverage run --source=auth_app,video_app --omit='*/migrations/*,*/tests/*' manage.py test
docker compose exec web coverage report -m
```

No test ever invokes FFmpeg: every `subprocess` call is mocked. No mail leaves
the machine either, Django swaps the mail backend for an in-memory one during
tests. Where a test needs to observe a queued job, the RQ queues are switched
to synchronous execution with `override_settings`. The suite therefore needs a
running Redis, which the command above provides.

---

## Authentication

The API uses **JWT stored in HttpOnly cookies**, not the `Authorization`
header. Logging in sets two cookies which the browser sends automatically with
every following request:

| Cookie          | Token lifetime | Purpose                     |
| --------------- | -------------- | --------------------------- |
| `access_token`  | 15 minutes     | Authenticates every request |
| `refresh_token` | 7 days         | Obtains a new access token  |

The times above are the lifetimes of the **tokens**. The cookies themselves are
session cookies and are dropped when the browser is closed.

The activation link and the password reset link carry a signed token as
well. Both are built by Django's `default_token_generator` and stop working
after **24 hours**, set through `PASSWORD_RESET_TIMEOUT` in
`core/settings.py`. The reset email names that period in its text, so the
setting and the wording in `auth_app/templates/reset_password.html` have to
be changed together.

Because the cookies are `HttpOnly`, JavaScript cannot read them. A frontend
therefore has to send its requests with `credentials: "include"`, and its
origin has to be listed in `CORS_ALLOWED_ORIGINS`.

The login response returns the user's data, not the tokens:

```json
{
  "detail": "Login successful",
  "user": {
    "id": 1,
    "username": "user@example.com"
  }
}
```

On logout the refresh token is added to a blacklist and both cookies are
deleted, so no new access token can be obtained. An access token that was
copied beforehand stays valid until it expires.

> **Note:** logging in is done with the **email address**. The `username` field
> in the response carries that same address; the API contract defines it this
> way.

---

## API Documentation

Interactive, auto-generated API documentation is available while the server is
running:

| View       | URL                       |
| ---------- | ------------------------- |
| Swagger UI | `/api/schema/swagger-ui/` |
| ReDoc      | `/api/schema/redoc/`      |
| Raw schema | `/api/schema/`            |

The RQ dashboard, showing queued, finished and failed background jobs, is at
`/django-rq/`.

---

## API Endpoints

Base path: `/api/`

### Authentication

| Method | Endpoint                              | Description                             | Auth           |
| ------ | ------------------------------------- | --------------------------------------- | -------------- |
| POST   | `/register/`                          | Create a user and send the activation   | No             |
| GET    | `/activate/{uidb64}/{token}/`         | Activate the account                    | No             |
| POST   | `/login/`                             | Log in and set the auth cookies         | No             |
| POST   | `/logout/`                            | Log out, blacklist and clear the tokens | Refresh cookie |
| POST   | `/token/refresh/`                     | Renew the access token                  | Refresh cookie |
| POST   | `/password_reset/`                    | Send a password reset link              | No             |
| POST   | `/password_confirm/{uidb64}/{token}/` | Set a new password                      | No             |

### Video

| Method | Endpoint                                    | Description                    | Auth          |
| ------ | ------------------------------------------- | ------------------------------ | ------------- |
| GET    | `/video/`                                   | List all videos, newest first  | Authenticated |
| GET    | `/video/{movie_id}/{resolution}/index.m3u8` | HLS playlist of one resolution | Authenticated |
| GET    | `/video/{movie_id}/{resolution}/{segment}/` | A single HLS segment           | Authenticated |

The segment endpoint answers with and without the trailing slash. ffmpeg writes
relative names such as `seg000.ts` into the playlist, so hls.js requests them
without one; serving both spares a `301` redirect per segment.

**Video files are only reachable through these endpoints.** `MEDIA_URL` is
wired up for `media/thumbnails/` alone, so neither the uploaded source file nor
the HLS segments can be fetched directly under `/media/`. Thumbnails stay
public on purpose: the frontend sets `thumbnail_url` as an `img` source, and a
preview image is not worth protecting.

Registering expects three fields:

```json
{
  "email": "user@example.com",
  "password": "securepassword",
  "confirmed_password": "securepassword"
}
```

---

## Conventions & Notes

- **Accounts start out inactive.** Registration creates the user, but logging
  in is refused until the link from the activation email has been used.
- **The email links point at the frontend**, not at this API. The frontend
  reads `uid` and `token` from the query string and calls the backend itself.
  Which addresses are used is controlled by `FRONTEND_URL`.
- **Password reset never reveals whether an address exists.** Both a known and
  an unknown address return the same `200` and the same message; a mail is only
  sent in the first case.
- **Error messages during registration are kept generic** on purpose. The
  wording never states what exactly was wrong with the input.
- **Conversion runs in the background.** The upload returns immediately, the
  HLS files appear a few minutes later. Requesting a playlist before it is
  ready returns `404`, which is the documented behaviour.
- **Queues are prioritised.** Emails go to `high`, video conversion to `low`.
  Both workers check `high` first, so a mail is picked up ahead of a queued
  conversion as soon as one of the two workers is free.
- **The video list is a flat array**, deliberately not paginated, ordered by
  `created_at` descending. The frontend uses the first entry as its hero video.
- **`thumbnail_url` is an absolute URL**, built from the incoming request, so
  the frontend can use it directly as an image source. A video whose conversion
  has not finished yet returns `null` here.
- **Cookie security:** the `secure` flag is controlled by `COOKIE_SECURE`
  rather than by `DEBUG`, because this project serves over plain HTTP even in
  its containerised form.
