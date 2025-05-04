from django.core.management import execute_from_command_line
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'taxmate_backend.settings')
django.setup()

from django.db import connection

def check_database_connection():
    try:
        with connection.cursor() as cursor:
            # Check if database exists
            cursor.execute("SELECT DATABASE()")
            db_name = cursor.fetchone()[0]
            print(f"Connected to database: {db_name}")

            # List all tables
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = %s
            """, [db_name])
            
            tables = cursor.fetchall()
            print("\nAvailable tables:")
            for table in tables:
                print(f"- {table[0]}")

            # Check specific tables
            required_tables = [
                'user_queries',
                'taxmate_chatbot_faqstatic',
                'taxmate_chatbot_taxslab',
                'taxmate_chatbot_deduction',
                'taxmate_chatbot_qualifyingpayment'
            ]

            print("\nChecking required tables:")
            for table in required_tables:
                cursor.execute(f"""
                    SELECT COUNT(*) 
                    FROM information_schema.tables 
                    WHERE table_schema = %s 
                    AND table_name = %s
                """, [db_name, table])
                
                exists = cursor.fetchone()[0] > 0
                print(f"- {table}: {'✓ Present' if exists else '✗ Missing'}")

    except Exception as e:
        print(f"Error connecting to database: {str(e)}")

if __name__ == "__main__":
    check_database_connection()