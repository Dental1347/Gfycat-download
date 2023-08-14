import os
import httpx
import asyncio
import logging
import time
from dotenv import load_dotenv

load_dotenv()
CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
GUSERNAME = os.getenv('GUSERNAME')
PASSWORD = os.getenv('PASSWORD')
DOWNLOAD_PATH = os.getenv('DOWNLOAD_PATH')

# Create the directory if it doesn't exist
os.makedirs(DOWNLOAD_PATH, exist_ok=True)

# Set up logging
log_file_path = os.path.join(DOWNLOAD_PATH, 'download_log.log')
logging.basicConfig(filename=log_file_path, level=logging.INFO)

async def download_file(client, gif, download_path, create_date_api):
    # Check if the file already exists
    if os.path.exists(download_path):
        create_date_file = os.path.getctime(download_path)
        if abs(create_date_api - create_date_file) < 1:
            return False

    # Try different subdomains
    subdomains = ['giant', 'fat', 'zippy']
    for subdomain in subdomains:
        url = f"https://{subdomain}.gfycat.com/{gif['gfyName']}.mp4"
        response = await client.get(url)
        if response.status_code == 200 and not response.text.startswith('<Error>'):
            with open(download_path, 'wb') as file:
                file.write(response.content)
            os.utime(download_path, (create_date_api, create_date_api))
            return True

    logging.error(f"Failed to download {gif['gfyName']}.mp4 from all subdomains.")
    return False

async def download_gifs(client, gifs):
    tasks = []
    for gif in gifs:
        download_path = os.path.join(DOWNLOAD_PATH, f"{gif['gfyName']}.mp4")
        create_date_api = gif['createDate']
        task = download_file(client, gif, download_path, create_date_api)
        tasks.append(task)

    await asyncio.gather(*tasks)

async def main():
    async with httpx.AsyncClient() as client:
        token_url = 'https://api.gfycat.com/v1/oauth/token'
        token_data = {
            'grant_type': 'password',
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
            'username': GUSERNAME,
            'password': PASSWORD
        }
        token_r = await client.post(token_url, json=token_data)
        token = token_r.json().get('access_token')

        if not token:
            logging.error("Failed to obtain access token")
            return

        url = 'https://api.gfycat.com/v1/me/gfycats'
        headers = {'Authorization': f'Bearer {token}'}
        cursor = None

        while True:
            params = {}
            if cursor:
                params['cursor'] = cursor

            response = await client.get(url, headers=headers, params=params)
            if response.status_code == 200:
                response_data = response.json()
                gifs = response_data.get('gfycats', [])
                cursor = response_data.get('cursor')
                await download_gifs(client, gifs)
                if not cursor:
                    break
            else:
                error_message = f"Error fetching GIFs: {response.text}"
                print(error_message)
                logging.error(error_message)
                break

asyncio.run(main())
