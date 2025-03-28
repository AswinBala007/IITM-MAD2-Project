# Quiz Master - V2

A multi-user quiz platform for exam preparation across multiple courses.

## Features

- Multi-user support with admin and regular user roles
- Course management with subjects and chapters
- Quiz creation and management
- Real-time quiz taking with timer
- Performance analytics and reports
- Daily reminders and monthly activity reports
- CSV exports for quiz data
- Caching for improved performance

## Tech Stack

- Backend: Flask (Python)
- Frontend: Vue.js with Bootstrap
- Database: SQLite
- Caching: Redis
- Background Tasks: Celery
- Authentication: JWT

## Setup Instructions

### Prerequisites

- Python 3.8+
- Node.js 14+
- Redis Server
- SQLite3

### Backend Setup

1. Create and activate virtual environment:
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Initialize database:
```bash
flask db upgrade
```

4. Start Redis server:
```bash
redis-server
```

5. Start Celery worker:
```bash
celery -A app.celery worker --loglevel=info
```

6. Start Celery beat for scheduled tasks:
```bash
celery -A app.celery beat --loglevel=info
```

7. Run Flask development server:
```bash
flask run
```

### Frontend Setup

1. Install dependencies:
```bash
cd frontend
npm install
```

2. Run development server:
```bash
npm run serve
```

## Default Admin Credentials

- Username: admin@quizmaster.com
- Password: admin123

## API Documentation

API documentation can be found at `/api/docs` when running the development server.

## License

MIT License