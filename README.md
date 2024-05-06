# Snappy

Snappy is a small project designed to make custom segment on your Snapchat Ad Platform.

# What this project does ?

Using the snapchat marketing API, this program allows you to create your own custom segments that can be used to target certain audience for ads.

The script allows you to add custom segments based on the input at the start of the script. You can also choose to delete the segments. If the segments exists already, it updates the details.

Based on the initial input, dummy user data is generated and stored in the database. On segment creation, the users are grouped with their segment and added with details in the snapchat account and then stored in the database. On deletion, the segments are removed from the snapchat account and then from the database.

You need to manually accept authorize on the initial run. Based on your snapchat credentials, it will give you a one time code that script will require to generate an access token and refresh token. Once you use the one time code, it will store the login details and use those for subsequent token generations.

This script assumes that you have only one organization with one ad account already set up in that organization. We can make it to work for specific organization and specific ad account with small tweaks.

# How to run

1. Setup a virtual environment to install the packages in the requirements.txt.2
2. Using the .env.example, create a .env file with your own Snapchat credentials and database details.
3. Run the script. 