# Mastodon Private Message Bot

A Python application that automatically listens for and responds to private messages on Mastodon using the streaming API.

## Features

- Connects directly to Mastodon's streaming API
- Listens for private messages in real-time
- Automatically responds to incoming direct messages
- Reconnects automatically if the connection is lost

## Prerequisites

- Python 3.12 or higher
- A Mastodon account
- A Mastodon access token with appropriate permissions

## Installation

1. Clone this repository:
   ```
   git clone <repository-url>
   cd perverse
   ```

2. Install the required dependencies:
   ```
   pip install -e .
   ```
   
   Or if you're using Poetry:
   ```
   poetry install
   ```

## Configuration

1. Copy the example environment file:
   ```
   cp .env.example .env
   ```

2. Edit the `.env` file and add your Mastodon instance and access token:
   ```
   MASTODON_INSTANCE=your-instance.social
   MASTODON_ACCESS_TOKEN=your_access_token_here
   
   # Optional: Set logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
   LOG_LEVEL=INFO
   ```

### How to obtain a Mastodon access token

1. Log in to your Mastodon instance
2. Go to Settings > Development > New Application
3. Fill in the application details:
   - Name: Mastodon PM Bot (or any name you prefer)
   - Website: (optional)
   - Redirect URI: (leave as is)
   - Scopes: Select at minimum:
     - `read:statuses`
     - `write:statuses`
     - `read:notifications`
4. Click "Submit"
5. On the next page, copy the "Access token"

## Usage

Run the bot with:

```
python main.py
```

The bot will connect to the Mastodon streaming API and start listening for direct messages. When a direct message is received, it will automatically respond.

## Customizing Responses

To customize how the bot responds to messages, modify the `process_message` method in the `MastodonBot` class in `main.py`. This method receives the message data and should return the response text.

```python
def process_message(self, message_data):
    # Extract relevant information from the message
    content = message_data.get("content", "")
    account = message_data.get("account", {})
    sender_name = account.get("display_name", "")
    
    # Generate a response (customize this based on your needs)
    response = f"Hello {sender_name}, thanks for your message! This is an automated response."
    
    return response
```

You can implement more complex logic here, such as:
- Keyword-based responses
- Integration with external APIs
- Natural language processing

## Logging Configuration

The application uses Python's built-in logging system. You can control the verbosity of logs by setting the `LOG_LEVEL` environment variable in your `.env` file:

```
LOG_LEVEL=INFO
```

Available logging levels:
- `DEBUG`: Detailed information, typically useful for diagnosing problems
- `INFO`: Confirmation that things are working as expected (default)
- `WARNING`: Indication that something unexpected happened, but the application is still working
- `ERROR`: Due to a more serious problem, the application has not been able to perform some function
- `CRITICAL`: A serious error, indicating that the application itself may be unable to continue running

For more detailed logs during development or troubleshooting, set `LOG_LEVEL=DEBUG`.

## Troubleshooting

- **Connection issues**: Ensure your Mastodon instance URL is correct and includes only the domain (e.g., `mastodon.social`, not `https://mastodon.social`)
- **Authentication errors**: Verify your access token has the required scopes
- **Missing dependencies**: Make sure all required packages are installed
- **Debugging**: Set `LOG_LEVEL=DEBUG` in your `.env` file to see more detailed logs
