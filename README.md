# UniSync

UniSync is a Flask and MySQL student information platform. Administrators configure real public web sources. A Python maintenance process fetches permitted pages, extracts page text with BeautifulSoup, asks an explicitly configured OpenAI-compatible LLM for evidence-backed structured data, validates it with Pydantic, creates proposals, and waits for human approval before anything is published. The application starts with no sources and no student records.

## Architecture

HTML/CSS/vanilla JS use Flask routes and JSON APIs. Flask-SQLAlchemy persists admins, sources, published records, proposals, scan runs, and review events in MySQL. Requests and BeautifulSoup perform extraction; the Discovery and Review agents use the shared real LLM client. APScheduler runs separately from the Flask process. A scan failure is persisted as a failed run and never becomes a fabricated record.

## Requirements and setup

Use Python 3.11 or newer and a running MySQL 8 compatible server. From PowerShell in this directory:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env`. Set `DATABASE_URL` to a MySQL SQLAlchemy URL, for example `mysql+pymysql://unisync_user:your_password@127.0.0.1:3306/unisync?charset=utf8mb4` (create the database and a least-privilege database user in MySQL first). Set a random `SECRET_KEY`, e.g. generate one with `python -c "import secrets; print(secrets.token_urlsafe(48))"`. Provide your actual provider-issued `LLM_API_KEY`, `LLM_MODEL`, and `LLM_BASE_URL`. The base URL is the OpenAI-compatible API root, normally ending `/v1`. Leave credential fields empty until you have genuine credentials; extraction will fail visibly while unconfigured. For HTTPS deployment set `ADMIN_SESSION_COOKIE_SECURE=true`.

## Initialize and create the administrator

```powershell
flask --app run.py init-db
flask --app run.py create-admin
```

The table initialization creates an empty data store. Admin creation prompts for a username and password (at least 12 characters); it does not seed a default account. SQLAlchemy models are the canonical schema/migration source in this mini-project. For future schema changes, use Alembic/Flask-Migrate in a deployment workflow; `init-db` does not alter existing tables.

## Run the application

In one PowerShell window:

```powershell
flask --app run.py run
```

Open `http://127.0.0.1:5000`. Sign in at `/admin/login`, configure one or more genuine public URLs, and use Test or Scan. The Test action makes a real HTTP request and reports its result. A full scan needs a functioning MySQL database and LLM API. Review proposals at `/admin/proposals`; accept, reject, or flag them. Only accepted proposals are visible in public listings.

In a second window, run the independent scheduler:

```powershell
python -m app.scheduler.scheduler
```

`CHECK_INTERVAL_MINUTES` controls the interval (minimum 5); `TIMEZONE` defaults to `Asia/Kolkata`. The scheduler checks configured enabled sources and writes run history. Manual maintenance is available from the admin overview. Starting this process is required for recurring checks; Flask does not start background schedulers.

## Sources and extraction

Add the actual source URL through the admin UI; UniSync has no invented/preloaded URLs. URLs must resolve to public IP addresses. Robots rules are checked when available; requests have timeouts; redirects to private addresses are blocked. Pages that require login, CAPTCHA bypass, paywalls, or client-side rendering are unsupported and recorded as failed. Optional CSS selectors can target a relevant page section. The fetcher collects the configured page and follows at most three keyword-relevant same-domain links per scan, with robots and URL checks on each page. It does not crawl unrelated domains. The extraction agent works from the actual configured page text and evidence quotes must occur in that text. Missing facts remain null.

## API

- `GET /api/records?q=keyword&category=notice&sort=newest&page=1`
- `GET /api/records/<id>` (approved/current only)
- `GET /api/categories`

Search, categories, sorting, pagination, detail views, and counts are database-backed. No local JavaScript record fixtures are used.

## Tests

```powershell
pytest -q
```

Tests use isolated in-memory SQLite only in the test process where possible; it is not an application or production storage option. Live MySQL, source site access, and LLM credentials are external integrations and require separate configured verification.

## Troubleshooting

- **Database configuration missing/unavailable:** verify `DATABASE_URL`, MySQL service, schema/database existence, and credentials; run `flask --app run.py init-db` after configuration.
- **LLM not configured/authentication/rate limit:** set a valid provider key/model/base URL. UniSync does not substitute fake AI results.
- **Source failed:** inspect Scan history for the HTTP, robots, connectivity, or parsing error. A successful fetch with zero relevant records is different from a failed fetch.
- **Scheduler not running:** start `python -m app.scheduler.scheduler` as a separate long-running process.
- **Can't sign in:** create an account with `flask --app run.py create-admin`; no default credentials exist.

## Current limits

The source parser handles ordinary accessible HTML; JavaScript-rendered pages may not expose their content. Automated page crawling is deliberately bounded to the configured URL and same-domain link discovery; linked detail-page fetching and selector-specific per-record parsing are not yet implemented. Source maintenance proposes adds and supported updates; archival detection is limited to explicit deadline expiry. Human review is mandatory, including when the Review Agent is unavailable (the proposal is flagged).
