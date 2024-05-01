import os

import dotenv
from psycopg2 import connect, Error

dotenv.load_dotenv()

## For each name 10 entries are made in the database
DUMMY_NAMES = ["alex", "brad"]

def setup_database(connection):
    try:
        migration_file = './migration.sql'
        with open(migration_file, 'r') as f:
            sql_script = f.read()

        with connection.cursor() as cursor:
            cursor.execute(sql_script)
            connection.commit()
            print(f"Migration {migration_file} executed successfully")

    except Error as e:
        print(f"Error executing migration {migration_file}: {e}")

def generate_users(connection):
    try:
        with connection.cursor() as cursor:
            sql = """
                INSERT INTO users (username, email) 
                SELECT %s, %s
                WHERE NOT EXISTS (SELECT 1 FROM users WHERE email = %s)
            """
            dummy_users = [ (f"{i}{j}", f"{i}{j}@gmail.com")   for j in range(10)  for i in DUMMY_NAMES ] 

            for _ , (username, email) in enumerate(dummy_users):
                cursor.execute(sql, (username, email,email))

            connection.commit()

    except Error as e:
        print(f"Error adding users: {e}")



def main():
    try:
        connection = connect(
            user=os.environ.get("MYSQL_USER"),
            password=os.environ.get("MYSQL_PASS"),
            host=os.environ.get("MYSQL_HOST"),
            port=os.environ.get("MYSQL_PORT"),
            database=os.environ.get("MYSQL_B")
        )
        setup_database(connection)
        generate_users(connection)

        connection.close()
        print("PostgreSQL connection closed")

    except Error as e:
        print(f"Error connecting to PostgreSQL: {e}")


if __name__ == "__main__":
    main()