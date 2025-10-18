"""
Helper script to check if PostgreSQL is already running.
If PostgreSQL is available, it will use it. Otherwise, it will prompt to start docker-compose.
"""

import os
import psycopg2
from dotenv import load_dotenv
import sys

# Load environment variables
load_dotenv()

def check_postgres_connection():
    """Check if PostgreSQL is accessible with current settings."""
    db_host = os.getenv('DB_HOST', 'localhost')
    db_port = os.getenv('DB_PORT', '5432')
    db_name = os.getenv('DB_NAME', 'streaming_service')
    db_user = os.getenv('DB_USER', 'postgres')
    db_password = os.getenv('DB_PASSWORD', 'postgres')

    print("=" * 60)
    print("Checking PostgreSQL Connection")
    print("=" * 60)
    print(f"Host: {db_host}")
    print(f"Port: {db_port}")
    print(f"Database: {db_name}")
    print(f"User: {db_user}")
    print()

    try:
        # Try to connect
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            database=db_name,
            user=db_user,
            password=db_password,
            connect_timeout=3
        )

        # Get PostgreSQL version
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        cursor.close()
        conn.close()

        print("✓ PostgreSQL is RUNNING and accessible!")
        print(f"✓ Version: {version.split(',')[0]}")
        print()
        print("=" * 60)
        print("You can use the existing PostgreSQL instance.")
        print("No need to start docker-compose postgres.")
        print("=" * 60)
        print()
        return True

    except psycopg2.OperationalError as e:
        error_msg = str(e)

        if "does not exist" in error_msg:
            print(f"✗ PostgreSQL is running, but database '{db_name}' does not exist.")
            print()
            print("Options:")
            print(f"1. Create the database manually:")
            print(f"   psql -U {db_user} -c 'CREATE DATABASE {db_name};'")
            print()
            print("2. Or let the application create it on first run")
            print()
            return False
        else:
            print("✗ PostgreSQL is NOT accessible with current settings.")
            print(f"✗ Error: {error_msg}")
            print()
            print("=" * 60)
            print("Options:")
            print("=" * 60)
            print()
            print("Option 1: Use existing PostgreSQL")
            print("-" * 60)
            print("If you have PostgreSQL running elsewhere, update .env:")
            print(f"  DB_HOST=<your-host>")
            print(f"  DB_PORT=<your-port>")
            print(f"  DB_USER=<your-user>")
            print(f"  DB_PASSWORD=<your-password>")
            print()
            print("Option 2: Start PostgreSQL with docker-compose")
            print("-" * 60)
            print("  docker-compose up -d postgres")
            print()
            print("Option 3: Use system PostgreSQL")
            print("-" * 60)
            print("  If you have PostgreSQL installed on your system,")
            print("  make sure it's running and create the database:")
            print(f"  createdb -U {db_user} {db_name}")
            print()
            return False

    except Exception as e:
        print(f"✗ Unexpected error: {str(e)}")
        print()
        return False


def check_postgres_running_on_port(port=5432):
    """Check if any process is listening on PostgreSQL port."""
    import socket

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('localhost', int(port)))
        sock.close()

        if result == 0:
            return True
        else:
            return False
    except Exception as e:
        return False


def main():
    """Main function to check PostgreSQL and provide guidance."""

    # First check if something is listening on the port
    db_port = int(os.getenv('DB_PORT', '5432'))

    print()
    print("Step 1: Checking if PostgreSQL port is in use...")
    print()

    if check_postgres_running_on_port(db_port):
        print(f"✓ Port {db_port} is OPEN (something is listening)")
        print()
        print("Step 2: Checking if we can connect with configured credentials...")
        print()

        if check_postgres_connection():
            print("Next steps:")
            print("1. Run: python test_db_connection.py")
            print("2. Start backend: python app.py")
            sys.exit(0)
        else:
            print("PostgreSQL is running but connection failed.")
            print("Check your credentials in .env file.")
            sys.exit(1)
    else:
        print(f"✗ Port {db_port} is CLOSED (nothing is listening)")
        print()
        print("=" * 60)
        print("PostgreSQL is NOT running")
        print("=" * 60)
        print()
        print("To start PostgreSQL, choose one of these options:")
        print()
        print("Option 1: Docker Compose (Recommended)")
        print("-" * 60)
        print("  docker-compose up -d postgres")
        print("  Then run this script again to verify")
        print()
        print("Option 2: Install PostgreSQL on Windows")
        print("-" * 60)
        print("  Download from: https://www.postgresql.org/download/windows/")
        print("  After installation, create database:")
        print("  createdb -U postgres streaming_service")
        print()
        print("Option 3: Use WSL2 PostgreSQL")
        print("-" * 60)
        print("  wsl -d Ubuntu")
        print("  sudo service postgresql start")
        print()
        sys.exit(1)


if __name__ == "__main__":
    main()
