# Snappy

Snappy is a small project designed to make custom segment on your Snapchat Ad Platform.

# What this project does ?

Using the snapchat marketing API, this program allows you to create your own custom segments that can be used to target certain audience for ads.

The script allows you to add custom segments based on the input at the start of the script. You can also choose to delete the segments. If the segments exists already, it updates the details.

Based on the initial input, dummy user data is generated and stored in the database. On segment creation, the users are grouped with their segment and added with details in the snapchat account and then stored in the database. On deletion, the segments are removed from the snapchat account and then from the database.

# How to run

1. Setup a virtual environment to install the packages in the requirements.txt.2
2. Using the .env.example, create a .env file with your own Snapchat credentials and database details.
3. Run the script. 