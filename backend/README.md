# Quiz Master Backend

This is the backend server for the Quiz Master application. It provides APIs for user authentication, quiz management, and administrative functions.

## Features

- User and admin authentication
- Quiz creation and management
- Quiz attempt tracking
- Performance optimizations with Redis caching
- Background jobs using Celery

## Prerequisites

- Python 3.9 or higher
- Redis server
- SQLite (for development)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd IITM-MAD2-Project/backend
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install the dependencies:
```bash
pip install -r requirements.txt
```

4. Install and start Redis server:
```bash
# On Ubuntu/Debian
sudo apt-get install redis-server
sudo systemctl start redis-server

# On macOS with Homebrew
brew install redis
brew services start redis

# On Windows (using WSL or Redis for Windows)
# Please refer to Redis documentation
```

## Configuration

You can configure the application using environment variables:

- `REDIS_URL`: Redis connection URL (default: `redis://localhost:6379/0`)
- `SMTP_SERVER`: Email server for sending notifications
- `SMTP_PORT`: Email server port
- `EMAIL_USERNAME`: Email username for sending notifications
- `EMAIL_PASSWORD`: Email password

## Running the Application

1. Start the Flask server:
```bash
flask run
```

2. Start Celery worker (in a separate terminal):
```bash
celery -A celery_worker.celery worker --loglevel=info
```

3. Start Celery beat for scheduled tasks (in a separate terminal):
```bash
celery -A celery_worker.celery beat --loglevel=info
```

## Performance Improvements

### Redis Caching

The application uses Redis for caching frequently accessed data:

- Subject and chapter lists
- Quiz questions
- User information
- Dashboard statistics

Cache expiration times are set based on the volatility of the data:
- User profiles: 5 minutes
- Quiz questions: 15 minutes
- Subjects and chapters: 1 hour

### Celery Background Tasks

Celery is used for running background and scheduled jobs:

1. **Daily Reminders** - Sends notifications to users at 6 PM every day about:
   - Unvisited quiz platform
   - New quizzes
   - Unattempted quizzes

2. **Monthly Reports** - Generates and sends detailed activity reports on the 1st of each month containing:
   - Total quizzes attempted
   - Average scores
   - Highest scores
   - Quiz details

3. **CSV Exports** - Generates CSV files with user quiz attempt data:
   - Quiz details
   - Scores
   - Timing information
   - Chapter and subject information

## API Endpoints

### Authentication
- `POST /auth/register` - Register a new user
- `POST /auth/login` - Login and get access token
- `GET /auth/me` - Get current user profile
- `PUT /auth/profile` - Update user profile

### User Routes
- `GET /user/subjects` - Get all subjects
- `GET /user/quizzes/<subject_id>` - Get quizzes for a subject
- `POST /user/quiz/<quiz_id>/start` - Start a quiz attempt
- `GET /user/quiz/<quiz_id>` - Get quiz questions
- `POST /user/quiz/submit` - Submit quiz answers
- `GET /user/history` - Get user quiz history
- `POST /user/export/csv` - Request CSV export
- `GET /user/export/status/<job_id>` - Check export status
- `GET /user/export/jobs` - List all export jobs
- `GET /user/export/download/<job_id>` - Download completed export

### Admin Routes
- `GET /admin/statistics` - Get dashboard statistics
- `GET /admin/subjects` - Get all subjects
- `POST /admin/subjects` - Create a subject
- `PUT /admin/subjects/<subject_id>` - Update a subject
- `DELETE /admin/subjects/<subject_id>` - Delete a subject
- `GET /admin/subjects/<subject_id>/chapters` - Get chapters for a subject
- `POST /admin/subjects/<subject_id>/chapters` - Create a chapter
- `GET /admin/chapters/<chapter_id>/quizzes` - Get quizzes for a chapter
- `POST /admin/chapters/<chapter_id>/quizzes` - Create a quiz
- `GET /admin/quizzes/<quiz_id>/questions` - Get questions for a quiz
- `POST /admin/quizzes/<quiz_id>/questions` - Create a question
- `PUT /admin/questions/<question_id>` - Update a question
- `DELETE /admin/questions/<question_id>` - Delete a question
- `PUT /admin/quizzes/<quiz_id>` - Update a quiz
- `DELETE /admin/quizzes/<quiz_id>` - Delete a quiz
- `GET /admin/users/<user_id>/attempts` - Get user quiz attempts
- `GET /admin/search/users` - Search users
- `GET /admin/search/subjects` - Search subjects
- `GET /admin/search/quizzes` - Search quizzes 