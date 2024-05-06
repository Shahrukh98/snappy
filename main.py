import os
import requests
import datetime
import hashlib
import json
import webbrowser

import dotenv
from psycopg2 import connect, Error
from psycopg2.extensions import connection

dotenv.load_dotenv()

WEBDRIVER_PATH='/usr/bin/chromedriver'
LAST_LOGIN_FILENAME='./last_login.txt'

AUTH_URL="https://accounts.snapchat.com/login/oauth2/authorize"
TOKEN_REQUEST_URL="https://accounts.snapchat.com/login/oauth2/access_token"

ORGANIZATION_URL="https://adsapi.snapchat.com/v1/me/organizations"
ACCOUNT_URL="https://adsapi.snapchat.com/v1/organizations/{}/adaccounts"
SEGMENTS_URL="https://adsapi.snapchat.com/v1/adaccounts/{}/segments"
SEGMENT_USER_URL="https://adsapi.snapchat.com/v1/segments/{}/users"

SEGMENT_URL="https://adsapi.snapchat.com/v1/segments/{}"
SEGMENT_USERS_URL="https://adsapi.snapchat.com/v1/segments/{}/all_users"

# Snapchat access token expires token expires in 30 minutes by default,
# Its not supposed to be greater than 30. As a precautionary measure, it's set 5 minutes lesser.
REFRESH_ACCESS_TOKEN_INTERVAL_IN_MINUTES=25

# To make more segments, just make a new entry in SEGMENTS
SEGMENTS = [
    {
        "segment_name": "Alex Segment",
        "dummy_user_name": "Alex",
        "quantity": 100
    },
    {
        "segment_name": "Brad Segment",
        "dummy_user_name": "Brad",
        "quantity": 100
    }
]

#region Snapchat Token Setup

# This region contains the code to setup Snapchat token.

def get_snapchat_code():
    webbrowser.open(f"{AUTH_URL}?response_type=code&client_id={os.environ.get('SNAPCHAT_CLIENT_ID')}&redirect_uri={os.environ.get('SNAPCHAT_REDIRECT_URI')}&scope={os.environ.get('SNAPCHAT_SCOPE')}")
    code = input("Enter the code:")
    return code

def request_access_token(code: str = "", refresh_token: str = ""):
        """
        Helper for `setup_snapchat_token`
        It requests for access token from snapchat.
        If the access_token is being requested for the first time, use code argument.
        Else if, access_token is expired, use the refresh token to get new access token.
        """
        payload = {
            "client_id": os.environ.get("SNAPCHAT_CLIENT_ID"),
            "client_secret": os.environ.get("SNAPCHAT_CLIENT_SECRET"),
            "redirect_uri": os.environ.get("SNAPCHAT_REDIRECT_URI")
        }
        
        if len(refresh_token):
            payload["grant_type"] = "refresh_token"
            payload["refresh_token"] = refresh_token
        else:
            payload["grant_type"] = "authorization_code"
            payload["code"] = code

        token_request = requests.post(TOKEN_REQUEST_URL, payload)

        return token_request.json()

def get_previous_login_details():
    """
    Helper for **setup_snapchat_token** It retreives the previous login details, if it exists.
    """ 
    if not os.path.isfile(LAST_LOGIN_FILENAME):
        print("No Previous Login Details Found...")
        return 

    file = open(LAST_LOGIN_FILENAME, 'r')
    raw_text = file.readlines()
    
    file.close()

    return {
        "last_login_timestamp": int(raw_text[0].strip()),
        "access_token": raw_text[1].strip(),
        "refresh_token": raw_text[2].strip()
    }

def save_login_details(login_time: int, access_token: str, refresh_token: str):
    """
    Helper for `setup_snapchat_token`
    It stores the given login details.
        login_time: int
        access_token: str
        refresh_token: str
    """
    file = open(LAST_LOGIN_FILENAME, 'w')
    file.write(f"{login_time}\n{access_token}\n{refresh_token}")
    file.close()

def setup_snapchat_token():
    """This function runs in the beginning of the script and gets the token for requesting snapchat ad account."""
    previous_login_details = get_previous_login_details()

    if previous_login_details:
        current_timetamp = int(datetime.datetime.now().timestamp())
        previous_login_timestamp = previous_login_details["last_login_timestamp"]
        timestamp_diff = (current_timetamp - previous_login_timestamp) / 60

        print(f"If the last login is more than {REFRESH_ACCESS_TOKEN_INTERVAL_IN_MINUTES} minutes late, then your access token will be refreshed!")
        print(f"Last Login: {datetime.datetime.fromtimestamp(previous_login_timestamp)}")

        print(f"Time elapsed since login: {int(timestamp_diff)} minutes")

        if timestamp_diff > REFRESH_ACCESS_TOKEN_INTERVAL_IN_MINUTES:
            print("Token expired! Refreshing...")
            response_json = request_access_token(refresh_token=previous_login_details["refresh_token"])
            save_login_details(current_timetamp, response_json["access_token"], response_json["refresh_token"])
            access_token = response_json["access_token"]
        else:
            print("Token still valid! Continuing...")
            access_token = previous_login_details["access_token"]
        return access_token

    else:
        print("First run...")
        current_timetamp = int(datetime.datetime.now().timestamp())
        # code = request_snapchat_code_using_selenium()
        code = get_snapchat_code()

        print("Retrieved One-Time-Use Code")
        response_json = request_access_token(code=code)

        print("Successfully retrieved access token. Storing ...")
        save_login_details(current_timetamp, response_json['access_token'], response_json['refresh_token'])
        access_token = response_json["access_token"]
        return access_token

#endregion


#region Database Interaction

def setup_database(connection: connection):
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

def generate_users(connection: connection):
    try:
        with connection.cursor() as cursor:
            sql = """
                INSERT INTO users (username, email) 
                SELECT %s, %s
                WHERE NOT EXISTS (SELECT 1 FROM users WHERE email = %s)
            """
            dummy_users = []

            for segment in SEGMENTS:
                curr_users = [ ( f"{segment['dummy_user_name']}{i}", f"{segment['dummy_user_name'].lower()}{i}@gmail.com" ) for i in range(segment["quantity"]) ]
                dummy_users.extend(curr_users)

            for _ , (username, email) in enumerate(dummy_users):
                cursor.execute(sql, (username, email,email))

            connection.commit()

    except Error as e:
        print(f"Error adding users: {e}")

def get_user_for_segment(connection: connection, segment_user_name: str):
    try:
        with connection.cursor() as cursor:
            sql = "select * from users where username ilike %s;"
            cursor.execute(sql,  ('%' + segment_user_name + '%',))
            users = cursor.fetchall()

            return users
    except Error as e:
        print(f"Error getting users: {e}")

def store_segment_details(connection: connection, segment_id: str, segment_name: str, segment_users: list):
    try:
        with connection.cursor() as cursor:
            sql_insert_segment = """
                INSERT INTO segments (segment_id, segment_name) 
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING
            """
            cursor.execute(sql_insert_segment, (segment_id,segment_name))
            
            connection.commit()

            segment_membership_data = [ (user[0], segment_id) for user in segment_users ]
            
            sql_insert_membership = """
                INSERT INTO segment_membership (user_id, segment_id)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING
            """

            cursor.executemany(sql_insert_membership, segment_membership_data)
            
            connection.commit()

    except Error as e:
        print(f"Error getting users: {e}")
    
def remove_segment_from_db(connection: connection, segment_id: str):
    try:
        with connection.cursor() as cursor:
            sql_delete_segment_users = """
                DELETE FROM segment_membership where segment_id = %s
            """
            cursor.execute(sql_delete_segment_users, (segment_id,))
            connection.commit()

            sql_delete_segment = """
                DELETE FROM segments where segment_id = %s 
            """
            cursor.execute(sql_delete_segment, (segment_id,))            
            connection.commit()

    except Error as e:
        print(f"Error getting users: {e}")

#endregion

#region Snapchat Ops

def add_update_segment_to_snapchat_acc(organization_id: str, account_id: str, access_token: str, segment_details: dict, update: bool, segment_id: str = ""):
    if update:
        payload = {
            "segments": [
                {
                    "id": segment_id,
                    "name": segment_details["name"],
                    "organization_id": organization_id,
                    "description": f"Special segment for all {segment_details['dummy_user_name']}s",
                    "retention_in_days": 180
                }
            ]
        }
        
        update_req = requests.put(
            SEGMENTS_URL.format(account_id), 
            json.dumps(payload), 
            headers={ "Authorization": f"Bearer {access_token}", "Content-Type": "application/json"} 
        )
        
        print(f"Updated segment: {segment_details['name']}")
        print(update_req.json())

        payload = {
            "users": [
                {
                    "schema": ["EMAIL_SHA256"],
                    "data": [ [hashlib.sha256(user[2].strip().lower().encode()).hexdigest()] for user in segment_details["users"]  ]
                }
            ]
        }

        user_add_req = requests.post(
            SEGMENT_USER_URL.format(segment_id),  
            json.dumps(payload), 
            headers= { "Authorization": f"Bearer {access_token}", "Content-Type": "application/json" }
        )

        print(f"User added to segment: {segment_details['name']}")
        print(user_add_req.json())

        return {
            "segment_id": segment_id,
            "segment_name": segment_details["name"],
            "segment_users": segment_details["users"] 
        }
    
    else:
        payload = {
            "segments": [
                {
                    "ad_account_id": account_id,
                    "description": f"Special segment for all {segment_details['dummy_user_name']}s",
                    "name": segment_details["name"],
                    "retention_in_days": 180,
                    "source_type": "FIRST_PARTY"
                }
            ]
        }

        creation_req = requests.post(
            SEGMENTS_URL.format(account_id), 
            json.dumps(payload), 
            headers= { "Authorization": f"Bearer {access_token}", "Content-Type": "application/json" }
        )
        
        req_json = creation_req.json()

        print(f"Segment added: {segment_details['name']}")
        print(req_json)

        segment_id = req_json['segments'][0]['segment']['id']

        payload = {
            "users": [
                {
                    "schema": ["EMAIL_SHA256"],
                    "data": [ [hashlib.sha256(user[2].strip().lower().encode()).hexdigest()] for user in segment_details["users"]  ]
                }
            ]
        }

        user_add_req = requests.post(
            SEGMENT_USER_URL.format(segment_id),  
            json.dumps(payload), 
            headers= { "Authorization": f"Bearer {access_token}", "Content-Type": "application/json" }
        )

        print(f"User added to segment: {segment_details['name']}")
        print(user_add_req.json())


        return {
            "segment_id": segment_id,
            "segment_name": segment_details["name"],
            "segment_users": segment_details["users"] 
        }

def delete_segments_from_snapchat_acc(access_token: str, segment_id: str, segment_name: str):
    remove_users_req = requests.delete(f"{SEGMENT_USERS_URL.format(segment_id)}", headers={ "Authorization": f"Bearer {access_token}" })
    print(f"Removed all user for segment: {segment_name}")
    print(remove_users_req.json())

    delete_segment_req = requests.delete(SEGMENT_URL.format(segment_id), headers={ "Authorization": f"Bearer {access_token}" })    
    print(f"Removed segment: {segment_name}")
    print(delete_segment_req.json())

#endregion


def main():
    try:
        access_token = setup_snapchat_token()

        connection = connect(
            user=os.environ.get("MYSQL_USER"),
            password=os.environ.get("MYSQL_PASS"),
            host=os.environ.get("MYSQL_HOST"),
            port=os.environ.get("MYSQL_PORT"),
            database=os.environ.get("MYSQL_DB")
        )
        # Setup database and add users
        setup_database(connection)
        generate_users(connection)

        for segment in SEGMENTS:    
            users = get_user_for_segment(connection, segment["dummy_user_name"])


        print("Getting organizations...")
        orgs = requests.get(ORGANIZATION_URL, headers={"Authorization": f"Bearer {access_token}"} )
        orgs_json = orgs.json()

        org_id = orgs_json["organizations"][0]["organization"]["id"] if len(orgs_json["organizations"]) else None

        if not org_id:
            raise Exception("No Organization for given user!")
        
        print("Getting Ad Accounts...")
        accounts = requests.get(ACCOUNT_URL.format(org_id), headers={"Authorization": f"Bearer {access_token}"} )
        accounts_json = accounts.json()
        acc_id = accounts_json["adaccounts"][0]["adaccount"]["id"] if len(accounts_json["adaccounts"]) else None

        if not acc_id:
            raise Exception("No Ad Account for given organization!")

        print("Getting Segments...")
        segments = requests.get(SEGMENTS_URL.format(acc_id), headers={"Authorization": f"Bearer {access_token}"} )
        segments_json = segments.json()
        print(segments_json)

        segments = { entry["segment"]["name"]: entry["segment"]["id"]  for entry in segments_json["segments"] }
        segment_payloads = []

        for segment in SEGMENTS:
            users = get_user_for_segment(connection, segment["dummy_user_name"].lower())
            segment_payloads.append(
                {
                    "name": segment["segment_name"],
                    "dummy_user_name": segment["dummy_user_name"],
                    "users": users
                }
            )
        

        print("""Choose:\n
              1. Add Segments (Update if already exist)\n
              2. Delete all segments\n
              3. Exit\n
        """)

        decision = "0"
                
        while(decision not in "123"):
            decision = input("Enter choice: ")

            if decision not in "12":
                print("Choose 1 or 2")

        if decision == "1":
            for s_payload in segment_payloads:
                update = s_payload["name"] in segments.keys()

                details = add_update_segment_to_snapchat_acc(
                    organization_id= org_id,
                    account_id=acc_id,
                    access_token=access_token,
                    segment_details=s_payload,
                    update=update,
                    segment_id= segments.get(s_payload['name'])
                )

                store_segment_details(connection, details["segment_id"], details["segment_name"], details["segment_users"])
        
        elif decision == "2":
            for s_payload in segment_payloads:
                delete_segments_from_snapchat_acc(
                    access_token=access_token,
                    segment_id=segments[s_payload['name']],
                    segment_name=s_payload['name']
                )

                remove_segment_from_db(connection, segments[s_payload['name']])
            
        else:
            print("Exiting!!")
        
        print("PostgreSQL connection closed")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()