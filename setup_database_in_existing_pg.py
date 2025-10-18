"""
Setup script to create streaming_service database in existing PostgreSQL instance.
This connects to your existing JobTrak PostgreSQL and creates a separate database.
"""

import psycopg2
from dotenv import load_dotenv
import os
import sys

# Load environment variables
load_dotenv()

def create_streaming_database():
    """Create streaming_service database in existing PostgreSQL."""

    db_host = os.getenv('DB_HOST', 'localhost')
    db_port = os.getenv('DB_PORT', '5432')
    db_name = os.getenv('DB_NAME', 'streaming_service')
    db_user = os.getenv('DB_USER', 'jobtrak_user')
    db_password = os.getenv('DB_PASSWORD', 'jobtrak_secure_password_2024')

    print("=" * 70)
    print("Creating Streaming Service Database in Existing PostgreSQL")
    print("=" * 70)
    print(f"PostgreSQL Host: {db_host}:{db_port}")
    print(f"Database User: {db_user}")
    print(f"New Database: {db_name}")
    print()

    try:
        # Connect to the existing PostgreSQL (to the default 'postgres' database)
        print("Step 1: Connecting to existing PostgreSQL instance...")
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            database='postgres',  # Connect to default database first
            user=db_user,
            password=db_password
        )
        conn.autocommit = True
        cursor = conn.cursor()

        print("✓ Connected to PostgreSQL successfully")
        print()

        # Check if database already exists
        print(f"Step 2: Checking if database '{db_name}' exists...")
        cursor.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s",
            (db_name,)
        )
        exists = cursor.fetchone()

        if exists:
            print(f"✓ Database '{db_name}' already exists")
            print()
        else:
            # Create the database
            print(f"Step 3: Creating database '{db_name}'...")
            cursor.execute(f'CREATE DATABASE {db_name}')
            print(f"✓ Database '{db_name}' created successfully")
            print()

        cursor.close()
        conn.close()

        # Now connect to the new database and verify
        print("Step 4: Connecting to streaming_service database...")
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            database=db_name,
            user=db_user,
            password=db_password
        )
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        cursor.close()
        conn.close()

        print(f"✓ Successfully connected to '{db_name}' database")
        print()

        print("=" * 70)
        print("✓ Setup Complete!")
        print("=" * 70)
        print()
        print("Your existing PostgreSQL now has TWO databases:")
        print(f"  1. jobtrak           (your existing JobTrak database)")
        print(f"  2. {db_name}  (new streaming service database)")
        print()
        print("Both databases:")
        print(f"  - Use the same PostgreSQL instance ({db_host}:{db_port})")
        print(f"  - Use the same user ({db_user})")
        print(f"  - Are completely isolated from each other")
        print()
        print("Next Steps:")
        print("  1. Run: python test_db_connection.py")
        print("  2. Start backend: python app.py")
        print("  3. Scan courses (no Firebase quota limits!)")
        print()
        return True

    except psycopg2.OperationalError as e:
        print("✗ Failed to connect to PostgreSQL")
        print(f"✗ Error: {str(e)}")
        print()
        print("Troubleshooting:")
        print(f"  1. Make sure JobTrak PostgreSQL is running:")
        print(f"     docker ps | grep jobtrak-postgres")
        print()
        print(f"  2. Verify credentials in .env match JobTrak settings")
        print()
        print(f"  3. Check if PostgreSQL is accessible:")
        print(f"     docker exec jobtrak-postgres pg_isready")
        print()
        return False

    except Exception as e:
        print(f"✗ Unexpected error: {str(e)}")
        return False


if __name__ == "__main__":
    success = create_streaming_database()
    sys.exit(0 if success else 1)
