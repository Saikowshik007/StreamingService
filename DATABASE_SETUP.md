# PostgreSQL Database Setup Guide

This guide explains how to set up and use the local PostgreSQL database for user progress tracking.

## Overview

The streaming service now uses PostgreSQL as the primary database for tracking user progress. The system is designed with a multi-tier architecture:

1. **PostgreSQL** - Primary database for persistent storage
2. **Redis** - Cache layer for fast reads
3. **Firebase Firestore** - Backup/sync (existing system)

## Architecture

```
User Progress Flow:
┌─────────────┐
│   Client    │
│  (React)    │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────┐
│          Flask Backend                   │
│                                          │
│  ┌────────────┐  ┌──────────────┐      │
│  │  Progress  │  │   Progress   │      │
│  │   Write    │  │     Read     │      │
│  └─────┬──────┘  └──────┬───────┘      │
│        │                 │              │
│        ▼                 ▼              │
│  ┌──────────────────────────────┐      │
│  │      PostgreSQL Database     │      │
│  │  - user_progress             │      │
│  │  - course_progress           │      │
│  │  - lesson_progress           │      │
│  │  - user_activity_log         │      │
│  └──────────────────────────────┘      │
│        │                 │              │
│        ▼                 ▼              │
│  ┌──────────┐      ┌──────────┐       │
│  │  Redis   │      │ Firebase │       │
│  │  Cache   │      │  Backup  │       │
│  └──────────┘      └──────────┘       │
└─────────────────────────────────────────┘
```

## Database Schema

### Tables

#### 1. user_progress
Tracks individual file/lesson progress for each user.

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL PRIMARY KEY | Auto-incrementing ID |
| user_id | VARCHAR(128) | Firebase user ID |
| file_id | VARCHAR(128) | File identifier |
| lesson_id | VARCHAR(128) | Lesson identifier |
| course_id | VARCHAR(128) | Course identifier |
| progress_seconds | INTEGER | Current playback position |
| progress_percentage | DECIMAL(5,2) | Percentage completed |
| completed | BOOLEAN | Whether file is completed |
| last_watched | TIMESTAMP | Last viewing timestamp |
| created_at | TIMESTAMP | Record creation time |
| updated_at | TIMESTAMP | Last update time |

**Unique Constraint:** (user_id, file_id)

#### 2. course_progress
Aggregated progress for entire courses.

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL PRIMARY KEY | Auto-incrementing ID |
| user_id | VARCHAR(128) | Firebase user ID |
| course_id | VARCHAR(128) | Course identifier |
| total_files | INTEGER | Total files in course |
| completed_files | INTEGER | Number of completed files |
| total_duration | INTEGER | Total course duration |
| watched_duration | INTEGER | Total watched duration |
| progress_percentage | DECIMAL(5,2) | Overall progress |
| last_updated | TIMESTAMP | Last update time |
| created_at | TIMESTAMP | Record creation time |

**Unique Constraint:** (user_id, course_id)

#### 3. lesson_progress
Aggregated progress for lessons.

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL PRIMARY KEY | Auto-incrementing ID |
| user_id | VARCHAR(128) | Firebase user ID |
| lesson_id | VARCHAR(128) | Lesson identifier |
| course_id | VARCHAR(128) | Course identifier |
| total_files | INTEGER | Total files in lesson |
| completed_files | INTEGER | Number of completed files |
| progress_percentage | DECIMAL(5,2) | Overall progress |
| last_updated | TIMESTAMP | Last update time |
| created_at | TIMESTAMP | Record creation time |

**Unique Constraint:** (user_id, lesson_id)

#### 4. user_activity_log
Optional activity tracking for analytics.

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL PRIMARY KEY | Auto-incrementing ID |
| user_id | VARCHAR(128) | Firebase user ID |
| file_id | VARCHAR(128) | File identifier |
| lesson_id | VARCHAR(128) | Lesson identifier |
| course_id | VARCHAR(128) | Course identifier |
| activity_type | VARCHAR(50) | Type of activity |
| duration_seconds | INTEGER | Duration of activity |
| timestamp | TIMESTAMP | Activity timestamp |

## Setup Instructions

### 1. Start PostgreSQL with Docker

The easiest way to run PostgreSQL is using Docker Compose:

```bash
# Start only PostgreSQL
docker-compose up -d postgres

# Check if PostgreSQL is running
docker-compose ps

# View PostgreSQL logs
docker-compose logs postgres
```

### 2. Verify Database Connection

Run the test script to verify the database is set up correctly:

```bash
python test_db_connection.py
```

This will:
- Test the database connection
- Initialize the schema (create tables)
- Insert test data
- Retrieve test data
- Verify everything works

### 3. Start the Backend

Start the Flask backend normally:

```bash
python app.py
```

The backend will automatically:
- Connect to PostgreSQL
- Use PostgreSQL as the primary database
- Fall back to Redis cache for faster reads
- Sync to Firebase as a backup

## Environment Variables

Make sure your `.env` file contains the following PostgreSQL configuration:

```env
# PostgreSQL Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=streaming_service
DB_USER=postgres
DB_PASSWORD=postgres
```

For Docker deployment, the `docker-compose.yml` file already includes these environment variables.

## API Endpoints

The existing API endpoints now use PostgreSQL:

### Update Progress
```
POST /learn/api/progress
Authorization: Bearer <firebase-token>

{
  "file_id": "file123",
  "progress_seconds": 120,
  "progress_percentage": 50.0,
  "completed": false
}
```

### Get File Progress
```
GET /learn/api/progress/file/<file_id>
Authorization: Bearer <firebase-token>

Response:
{
  "user_id": "firebase_user_id",
  "file_id": "file123",
  "progress_seconds": 120,
  "progress_percentage": 50.0,
  "completed": false,
  "last_watched": "2025-10-18T12:34:56"
}
```

### Get Course Progress
```
GET /learn/api/progress/course/<course_id>
Authorization: Bearer <firebase-token>

Response:
{
  "user_id": "firebase_user_id",
  "course_id": "course123",
  "total_files": 10,
  "completed_files": 5,
  "progress_percentage": 50.0,
  "last_updated": "2025-10-18T12:34:56"
}
```

## Data Flow

### Writing Progress

1. Client sends progress update with Firebase user ID token
2. Backend validates Firebase token and extracts user ID
3. **Primary:** Write to PostgreSQL (durable storage)
4. **Cache:** Write to Redis (fast reads)
5. **Backup:** Async sync to Firebase (existing system)

### Reading Progress

1. Client requests progress with Firebase user ID token
2. Backend tries Redis first (fastest)
3. If not in Redis, try PostgreSQL (primary database)
4. If not in PostgreSQL, fall back to Firebase
5. Cache the result in Redis for future reads

## User ID Tracking

The system uses **Firebase User IDs** to track progress:

- When a user logs in via Firebase Authentication, they receive a unique user ID
- The client sends this user ID in the Authorization header as a Bearer token
- The backend validates the token and extracts the user ID
- All progress is stored with this user ID as the primary key

Example user_id: `"firebase_uid_abc123xyz"`

## Automatic Progress Aggregation

The database automatically calculates aggregated progress:

- **Lesson Progress:** Automatically calculated when file progress is updated
- **Course Progress:** Automatically calculated when file progress is updated
- Uses database triggers and stored procedures for consistency

## Database Management

### Connect to PostgreSQL

```bash
# Using Docker
docker exec -it learning-platform-postgres psql -U postgres -d streaming_service

# List tables
\dt

# View user progress
SELECT * FROM user_progress LIMIT 10;

# View course progress
SELECT * FROM course_progress;

# Exit
\q
```

### Backup Database

```bash
# Backup
docker exec learning-platform-postgres pg_dump -U postgres streaming_service > backup.sql

# Restore
docker exec -i learning-platform-postgres psql -U postgres streaming_service < backup.sql
```

### Reset Database

```bash
# Stop and remove PostgreSQL container and volume
docker-compose down -v postgres

# Start fresh
docker-compose up -d postgres

# Run test script to initialize schema
python test_db_connection.py
```

## Monitoring

### Check Database Size

```sql
SELECT pg_size_pretty(pg_database_size('streaming_service'));
```

### Check Table Sizes

```sql
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### View Active Connections

```sql
SELECT * FROM pg_stat_activity WHERE datname = 'streaming_service';
```

## Troubleshooting

### Connection Refused

If you get connection refused errors:

1. Check Docker is running: `docker ps`
2. Check PostgreSQL is running: `docker-compose ps`
3. Check logs: `docker-compose logs postgres`
4. Restart PostgreSQL: `docker-compose restart postgres`

### Schema Not Initialized

If tables are missing:

1. Run the test script: `python test_db_connection.py`
2. This will automatically create the schema

### Performance Issues

If the database is slow:

1. Check connection pool settings in `database.py`
2. Increase max connections if needed
3. Add more indexes for frequently queried columns
4. Monitor with: `SELECT * FROM pg_stat_statements;`

## Production Considerations

For production deployment:

1. **Change default credentials** in `.env` and `docker-compose.yml`
2. **Enable SSL** for PostgreSQL connections
3. **Set up regular backups** with pg_dump or pgBackRest
4. **Monitor database metrics** with tools like pgAdmin or Datadog
5. **Scale with read replicas** if needed
6. **Use managed PostgreSQL** services (AWS RDS, Google Cloud SQL, etc.)

## Security Notes

- The default credentials are for development only
- Change `DB_PASSWORD` to a strong password in production
- Use environment variables, never hardcode credentials
- Restrict database access to backend services only
- Enable SSL/TLS for database connections
- Regularly update PostgreSQL for security patches
