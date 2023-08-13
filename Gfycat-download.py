import os
import requests
import time
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Constants
CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
USERNAME = os.getenv('USERNAME')
PASSWORD = os.getenv('PASSWORD')
DOWNLOAD_PATH = os.getenv('DOWNLOAD_PATH')

# Create the directory if it doesn't exist
os.makedirs(DOWNLOAD_PATH, exist_ok=True)

# Set up logging
log_file_path = os.path.join(DOWNLOAD_PATH, 'download_log.log')
logging.basicConfig(filename=log_file_path, level=logging.INFO)

# Obtain access token using password grant
token_url = 'https://api.gfycat.com/v1/oauth/token'
token_data = {
    'grant_type': 'password',
    'client_id': CLIENT_ID,
    'client_secret': CLIENT_SECRET,
    'username': USERNAME,
    'password': PASSWORD
}
token_r = requests.post(token_url, json=token_data)
token = token_r.json().get('access_token')

if not token:
    logging.error("Failed to obtain access token")
    exit()

# Get user's GIFs
url = 'https://api.gfycat.com/v1/me/gfycats'
headers = {
    'Authorization': f'Bearer {token}',
}

response = requests.get(url, headers=headers)
gifs = []
cursor = None

# Loop to handle pagination
while True:
    params = {}
    if cursor:
        params['cursor'] = cursor

    response = requests.get(url, headers=headers, params=params)

    # Check for successful response
    if response.status_code == 200:
        response_data = response.json()
        gifs += response_data.get('gfycats', [])
        cursor = response_data.get('cursor')
        if not cursor:
            break  # No more pages
    else:
        error_message = f"Error fetching GIFs: {response.text}"
        print(error_message)
        logging.error(error_message)
        break

# Download gfycats with timeouts
for gif in gifs:
    # Construct the URL for the .mp4 version
    gif_url = f"https://giant.gfycat.com/{gif['gfyName']}.mp4"
    download_path = os.path.join(DOWNLOAD_PATH, f"{gif['gfyName']}.mp4")

    # Get the creation date from the API response
    create_date_api = gif['createDate']

    # Check if the file already exists
    if os.path.exists(download_path):
        # Get the creation date of the existing file
        create_date_file = os.path.getctime(download_path)

        # If the creation dates match, skip this file
        if abs(create_date_api - create_date_file) < 1:
            skip_message = f"File {gif['gfyName']}.mp4 already exists with the correct creation date. Skipping download."
            print(skip_message)
            logging.info(skip_message)
            continue
        else:
            # Update the creation date of the existing file
            os.utime(download_path, (create_date_api, create_date_api))
            update_message = f"Updated creation date for {gif['gfyName']}.mp4."
            print(update_message)
            logging.info(update_message)

    response = requests.get(gif_url, stream=True)
    with open(download_path, 'wb') as file:
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                file.write(chunk)

    # Set the file's timestamps
    os.utime(download_path, (create_date_api, create_date_api))

    success_message = f"Downloaded {gif['gfyName']}.mp4 to {download_path}"
    print(success_message)
    logging.info(success_message)
    time.sleep(5)  # 5-second timeout between downloads
