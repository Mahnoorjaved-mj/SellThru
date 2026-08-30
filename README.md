# AI Sales Forecasting

Full-stack sales forecasting platform. A **FastAPI** backend serves JWT-authenticated REST APIs backed by **MongoDB**, trains **scikit-learn** Random Forest models for daily demand prediction, and a **React + Vite + Tailwind** frontend visualizes dashboards, predictions, and AI insights.

---

## Tech Stack

| Layer     | Technology                                                        |
| --------- | ----------------------------------------------------------------- |
| Backend   | FastAPI, Uvicorn, Motor (async MongoDB), Pydantic                 |
| ML        | scikit-learn (RandomForestRegressor), pandas, numpy               |
| Auth      | JWT (python-jose), bcrypt, TOTP 2FA (pyotp), OTP email verify     |
| Scheduler | APScheduler (weekly auto-retraining)                              |
| Email     | SMTP + Jinja2 templates                                           |
| Frontend  | React 19, Vite, Tailwind CSS, React Router, Chart.js              |
| Database  | MongoDB                                                           |

---

## Prerequisites

- **Python 3.10+** (installed globally — no virtualenv required)
- **Node.js 18+** and npm
- **MongoDB** running locally at `mongodb://localhost:27017` (or update `MONGO_URI`)

---

## Backend Setup

```bash
cd backend

# Install dependencies globally
pip install -r requirements.txt

# Run the server (reads .env automatically)
python main.py
```

The API starts at **http://127.0.0.1:8000**.

- Swagger docs: http://127.0.0.1:8000/docs
- Health check: http://127.0.0.1:8000/api/health

> `python main.py` runs Uvicorn with auto-reload enabled when `DEBUG=True` in `.env`.

### Environment variables (`backend/.env`)

The `.env` file is **git-ignored** (it holds secrets). Keys used:

| Variable          | Description                                       | Default                          |
| ----------------- | ------------------------------------------------- | -------------------------------- |
| `APP_NAME`        | Application name                                  | `AI Sales Forecasting`           |
| `DEBUG`           | Enables auto-reload                               | `True`                           |
| `APP_BASE_URL`    | Backend base URL (used in email links)            | `http://127.0.0.1:8000`          |
| `FRONTEND_ORIGIN` | Comma-separated allowed CORS origins              | `http://localhost:5173,...`      |
| `MONGO_URI`       | MongoDB connection string                         | `mongodb://localhost:27017`      |
| `MONGO_DB_NAME`   | Database name                                     | `sales_forecasting`              |
| `JWT_SECRET`      | Secret for signing JWTs — **change in prod**      | _(placeholder)_                  |
| `JWT_ALGORITHM`   | JWT signing algorithm                             | `HS256`                          |
| `JWT_EXPIRE_HOURS`| Token lifetime in hours                           | `4`                              |
| `SMTP_HOST`       | SMTP server host                                  | `smtp.gmail.com`                 |
| `SMTP_PORT`       | SMTP server port                                  | `587`                            |
| `SMTP_USER`       | SMTP username (leave blank to disable email)      | _(empty)_                        |
| `SMTP_PASSWORD`   | SMTP password / app password                      | _(empty)_                        |
| `SMTP_FROM_NAME`  | Sender display name                               | `Sales Forecasting Alerts`       |

> If `SMTP_USER`/`SMTP_PASSWORD` are blank, emails (OTP, welcome, password reset) are skipped and logged to the console — useful for local development.

---

## Frontend Setup

```bash
cd frontend

npm install
npm run dev
```

The app runs at **http://localhost:5173**. The Vite dev server proxies `/api` and `/auth`
requests to the backend at `127.0.0.1:8000`, so no API URL config is needed for local dev.

---

## First Run

1. Start MongoDB, then the backend (`python main.py`), then the frontend (`npm run dev`).
2. Register an account at http://localhost:5173 — **the first registered user becomes an admin.**
3. Verify the OTP (check your inbox, or the backend console if SMTP is not configured).
4. As an admin, seed demo data via the dashboard (or `POST /api/sales/seed`), or upload a sales CSV.
5. Train the model from the Predictions page (or `POST /api/forecast/train`), then view forecasts.

> The predictor falls back to a statistical seasonal baseline when no trained model exists yet,
> so the app is usable before the first training run.

### Sales CSV format

Required columns: `date, store_id, product_id, category, quantity, revenue`
Optional flags: `is_holiday, is_promo` (accept `true/1/yes`).
Supported date formats: `YYYY-MM-DD`, `YYYY/MM/DD`, `DD-MM-YYYY`, `MM/DD/YYYY`.

---

## API Overview

| Method | Endpoint                     | Description                          | Auth   |
| ------ | ---------------------------- | ------------------------------------ | ------ |
| POST   | `/auth/register`             | Register + send OTP                  | —      |
| POST   | `/auth/verify-otp`           | Verify OTP, create account           | —      |
| POST   | `/auth/login`                | Login, returns JWT                   | —      |
| POST   | `/auth/forgot-password`      | Request password reset email         | —      |
| POST   | `/auth/reset-password`       | Reset password with token            | —      |
| GET    | `/auth/me`                   | Current user profile                 | Bearer |
| POST   | `/auth/2fa/setup`/`verify`/`disable` | TOTP 2FA management          | Bearer |
| POST   | `/api/sales/upload`          | Upload sales CSV                     | Bearer |
| POST   | `/api/sales/seed`            | Seed synthetic demo data             | Admin  |
| GET    | `/api/sales/summary`         | Dashboard KPIs and charts            | Bearer |
| GET    | `/api/sales/history`         | Paginated sales history              | Bearer |
| GET    | `/api/forecast/predictions`  | Sales forecasts                      | Bearer |
| POST   | `/api/forecast/train`        | Train the ML model                   | Bearer |
| GET    | `/api/forecast/models`       | Model training history               | Bearer |
| GET    | `/api/insights/anomalies`    | Z-score sales anomalies              | Bearer |
| GET    | `/api/insights/trends`       | Trend & promo insights               | Bearer |
| GET    | `/api/health`                | DB + scheduler health                | —      |

---

## Project Structure

```
Sales-Forecasting/
├── backend/
│   ├── config/           # settings + MongoDB connection & indexes
│   ├── controllers/      # business logic (auth, sales, forecast)
│   ├── routes/           # FastAPI routers
│   ├── services/         # ML predictor, email, scheduler
│   ├── models/           # Pydantic schemas + serialization helpers
│   ├── utils/            # auth deps, security, audit logging
│   ├── email_templates/  # Jinja2 HTML emails
│   ├── saved_models/     # trained model pickles (git-ignored, auto-created)
│   ├── .env              # secrets (git-ignored)
│   ├── main.py           # app entrypoint — `python main.py`
│   └── requirements.txt
└── frontend/
    └── src/
        ├── components/   # Layout, Header, Sidebar, ProtectedRoute
        ├── context/      # global state + API client
        └── pages/        # Dashboard, Predictions, Insights, Auth, Data
```
