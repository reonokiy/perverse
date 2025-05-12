import os
import json
import asyncio
import logging
import aiohttp
import websockets
import re

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
# Get log level from environment variable, default to INFO if not set
log_level_name = os.getenv("LOG_LEVEL", "INFO").upper()
log_level = getattr(logging, log_level_name, logging.INFO)

logging.basicConfig(
    level=log_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
logger.info(f"Logging level set to: {logging.getLevelName(log_level)}")


# Mastodon API configuration
MASTODON_INSTANCE = os.getenv("MASTODON_INSTANCE")
ACCESS_TOKEN = os.getenv("MASTODON_ACCESS_TOKEN")

# API endpoints
API_BASE_URL = f"https://{MASTODON_INSTANCE}"
STREAMING_URL = f"wss://{MASTODON_INSTANCE}/api/v1/streaming"


def extract_acct_from_url(url: str) -> str | None:
    """
    Extract the acct (@username@domain) from a Mastodon profile URL.

    Args:
        url (str): The profile URL.

    Returns:
        str: The extracted acct.
    """
    pattern = r"https?://([^/]+)/@([^/]+)"
    match = re.match(pattern, url)

    if match:
        domain = match.group(1)
        username = match.group(2)
        return f"@{username}@{domain}"
    else:
        return None


class MastodonBot:
    def __init__(self, access_token):
        self.access_token = access_token
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        self.client = aiohttp.ClientSession(headers=self.headers, base_url=API_BASE_URL)

    async def get_account_info(self):
        """Get information about the authenticated account"""
        url = f"{API_BASE_URL}/api/v1/accounts/verify_credentials"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers) as response:
                response.raise_for_status()
                return await response.json()

    async def lookup_account(self, url: str):
        """Lookup an account by URL"""
        async with self.client as session:
            async with session.get(
                "/api/v1/accounts/lookup", headers=self.headers, params={"url": url}
            ) as response:
                response.raise_for_status()
                return await response.json()

    def get_full_account_address(self, account_info):
        """
        Get the full account address in the format @username@domain

        The Mastodon API returns different information depending on whether
        the account is local or remote:
        - For local accounts, we need to extract the domain from the account URL
        - For remote accounts, the acct field might already contain the domain

        Args:
            account_info: The account information from the API

        Returns:
            str: The full account address
        """
        username = account_info.get("username")

        # Check if acct already contains the domain (for remote accounts)
        acct = account_info.get("acct", "")
        if "@" in acct:
            return f"@{acct}"

        # For local accounts, extract domain from the URL
        url = account_info.get("url", "")
        if url:
            # URL format is typically https://domain/@username
            try:
                from urllib.parse import urlparse

                domain = urlparse(url).netloc
                return f"@{username}@{domain}"
            except Exception as e:
                logger.error(f"Error parsing URL {url}: {e}")

        # Fallback to the instance we're connected to
        return f"@{username}@{MASTODON_INSTANCE}"

    async def get_conversations(self):
        """Get recent direct message conversations"""
        url = f"{API_BASE_URL}/api/v1/conversations"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers) as response:
                response.raise_for_status()
                return await response.json()

    async def post_status(self, status, visibility="direct", in_reply_to_id=None):
        """Post a new status (message)"""
        url = f"{API_BASE_URL}/api/v1/statuses"
        data = {"status": status, "visibility": visibility}

        if in_reply_to_id:
            data["in_reply_to_id"] = in_reply_to_id

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=self.headers, json=data) as response:
                response.raise_for_status()
                logger.debug(f"Response status: {response}")
                return await response.json()

    async def process_message(self, message_data):
        """Process an incoming direct message and generate a response"""
        # Extract relevant information from the message
        content = message_data.get("content", "")
        account = message_data.get("account", {})
        sender_name = account.get("display_name", "")

        # Log the received message
        logger.info(f"Received message from {sender_name}: {content}")

        # Generate a response (customize this based on your needs)
        response = f"Hello {sender_name}, thanks for your message! This is an automated response."

        return response

    async def listen_to_direct_messages(self):
        """Connect to the streaming API and listen for direct messages"""
        stream_url = f"{STREAMING_URL}?stream=direct&access_token={self.access_token}"

        while True:
            try:
                async with websockets.connect(stream_url) as websocket:
                    logger.info("Connected to Mastodon streaming API")

                    while True:
                        message = await websocket.recv()
                        data = json.loads(message)
                        logger.debug(f"Received message: {data}")

                        # Check if this is a conversation event
                        if data.get("event") == "conversation":
                            payload = json.loads(data.get("payload", "{}"))

                            visibility = payload.get("last_status", {}).get(
                                "visibility"
                            )
                            accounts: list[str] = [
                                acct
                                for acct in [
                                    extract_acct_from_url(account.get("url", ""))
                                    for account in payload.get("accounts", [])
                                ]
                                if acct is not None
                            ]
                            status_id: str = payload.get("last_status", {}).get("id")
                            status_text: str = payload.get("last_status", {}).get(
                                "text", ""
                            )
                            logger.info(f"Direct message received: {status_text}")

                            # if status_text contains /ping, return pong
                            if "/ping" in status_text:
                                response = " ".join(accounts) + " pong!"

                                # Reply to the message
                                await self.post_status(
                                    status=response,
                                    visibility=visibility,
                                    in_reply_to_id=status_id,
                                )

                                logger.info(f"Sent response: {response}")

            except (
                websockets.exceptions.ConnectionClosed,
                websockets.exceptions.ConnectionClosedError,
                websockets.exceptions.ConnectionClosedOK,
            ) as e:
                logger.error(f"WebSocket connection closed: {e}")
                await asyncio.sleep(5)  # Wait before reconnecting

            except Exception as e:
                logger.error(f"Error in streaming connection: {e}")
                await asyncio.sleep(10)  # Wait longer before reconnecting


async def main():
    """Main function to run the Mastodon bot"""
    if not MASTODON_INSTANCE or not ACCESS_TOKEN:
        logger.error(
            "Missing environment variables. Please set MASTODON_INSTANCE and MASTODON_ACCESS_TOKEN"
        )
        return

    bot = MastodonBot(ACCESS_TOKEN)

    try:
        # Get account information to verify credentials
        account_info = await bot.get_account_info()
        full_address = bot.get_full_account_address(account_info)
        logger.info(f"Authenticated as: {full_address}")

        # Start listening for direct messages
        await bot.listen_to_direct_messages()

    except Exception as e:
        logger.error(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
