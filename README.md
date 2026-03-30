# Project Vesta // Merchive

A high-performance video streaming bridge designed to stream content directly from Telegram channels to a web-based interface. This project is specifically optimized for deployment on Railway.app, utilizing asynchronous streaming and byte-range requests to ensure a stable experience within cloud resource constraints.

--- 

## Technical Overview

Merchive acts as a transparent proxy between Telegram's servers and the client's browser. It eliminates the need for intermediate storage by streaming encrypted media chunks directly from the Telegram MTProto API into an HTTP/2 compatible stream.

### Key Optimization Strategies

* **Byte-Range Support (206 Partial Content)**: Allows the browser to request specific segments of a video. This enables seeking (skipping forward/backward) and prevents the server from timing out on large files.
* **Memory Management**: Byte chunks are processed as a generator, ensuring that Railway's RAM usage remains low even when streaming high-definition video.
* **Connection Persistence**: Maintains a warm session with the Telegram API to reduce latency during initial playback.

---

## Project Structure 

```text
merchive/
├── api/
│   ├── auth.py
│   ├── database.py
│   ├── get_session.py
│   ├── main.py
│   ├── models.py
│   └── telegram_logic.py
├── public/
│   ├── css/
│   │   └── style.css
│   ├── js/
│   │   ├── api.js
│   │   ├── main.js
│   │   └── uploader.js
│   ├── admin.html
│   ├── index.html
│   ├── login.html
│   └── player.html
├── Dockerfile
├── package.json
├── requirements.txt
└── vercel.json
```

---

## Technology Stack

* **Backend**: Python 3.11+ using FastAPI
* **Telegram Client**: Telethon (MTProto API)
* **Database**: Supabase (PostgreSQL) for metadata management
* **Frontend**: Vanilla JavaScript and HTML5 Video API
* **Deployment**: Railway.app

---

## Infrastructure Requirements

### Environment Variables
The following variables must be configured in your production environment or .env file:

* **TG_API_ID**: Your Telegram API ID.
* **TG_API_HASH**: Your Telegram API Hash.
* **TG_SESSION**: A Telethon String Session (required for cloud environments).
* **CHANNEL_ID**: The ID of the Telegram channel where media is hosted.
* **SUPABASE_URL**: Your Supabase project URL.
* **SUPABASE_KEY**: Your Supabase anonymous/public key.
* **ADMIN_SECRET**: The password for administrative access.

---

## Developer Setup

### Local Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/iantolentino/merchive
   cd merchive
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure local environment:
   Create a .env file in the root directory and populate it with the required variables listed above.

4. Execute the development server:
   ```bash
   uvicorn api.main:app --reload
   ```

### Deployment on Railway.app

1. Connect your repository to a new Railway project.
2. In the Variables tab, set **PYTHONPATH** to `.` (this ensures the /api directory is correctly indexed).
3. The service will automatically detect the start command from the package.json or use:
   `python3 -m uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}`

---

## API Documentation

### Video Streaming
* **Endpoint**: `/api/video/stream/{message_id}`
* **Method**: GET
* **Description**: Initiates a streaming response for the media associated with the provided Telegram message ID. Supports Range headers.

### Video Metadata
* **Endpoint**: `/api/videos/list`
* **Method**: GET
* **Description**: Retrieves a JSON list of all indexed videos from the Supabase database.

---

## Troubleshooting

### HTTP2_PROTOCOL_ERROR
If you encounter this error in the browser console, it is typically caused by the browser's aggressive cache management or the Railway proxy closing an idle connection. The current implementation mitigates this by using 1MB chunk sizes and 256KB request sizes from Telegram to keep data flowing consistently.

### ModuleNotFoundError
Ensure that the **PYTHONPATH** environment variable is set to `.` in your deployment settings. This allows the main script to locate the database and authentication modules within the /api directory.
