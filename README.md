# 🎬 Malayalam Movie Bot

A production-ready, high-performance Telegram Movie Catalog and Media Delivery Bot built with **Python 3.12**, **aiogram 3**, and **MongoDB Atlas**. Designed for seamless one-click Koyeb worker deployment with forward-based Telegram media uploads, zero-reupload delivery using `copyMessage`, dual-channel Force Subscribe verification (including instant Request-to-Join support), and dynamic menu and year management.

---

## 📑 Table of Contents

1. [Project Introduction](#1-project-introduction)
2. [Key Features](#2-key-features)
3. [Technology Stack](#3-technology-stack)
4. [Architecture Overview](#4-architecture-overview)
5. [Complete Folder Structure](#5-complete-folder-structure)
6. [BotFather Setup](#6-botfather-setup)
7. [Admin ID Setup](#7-admin-id-setup)
8. [MongoDB Atlas Setup](#8-mongodb-atlas-setup)
9. [Local Installation](#9-local-installation)
10. [Environment Configuration](#10-environment-configuration)
11. [Running Locally](#11-running-locally)
12. [Admin Usage Instructions](#12-admin-usage-instructions)
13. [Adding Movies (Forward-Based Upload)](#13-adding-movies-forward-based-upload)
14. [Configuring Sub 2 (Public vs Private Request)](#14-configuring-sub-2-public-vs-private-request)
15. [Force Subscribe Behaviour & Business Rules](#15-force-subscribe-behaviour--business-rules)
16. [Broadcast Usage](#16-broadcast-usage)
17. [GitHub Upload Instructions](#17-github-upload-instructions)
18. [Koyeb Deployment Guide](#18-koyeb-deployment-guide)
19. [Troubleshooting Guide](#19-troubleshooting-guide)
20. [Security Guidelines](#20-security-guidelines)

---

## 1. Project Introduction

**Malayalam Movie Bot** is a single-bot Telegram solution that provides users with an intuitive, year-wise movie catalog while granting the administrator total control over content, channels, dynamic menus, and broadcasts directly through Telegram buttons.

The bot eliminates the need for expensive file storage and external websites by utilizing Telegram's native `copyMessage` and `copyMessages` APIs to reference and deliver posters, videos, and multi-file albums directly to users with instant speed.

---

## 2. Key Features

- **Single Bot Architecture:** Automatic server-side differentiation between regular users and the configured administrator via Telegram User ID.
- **Dynamic User Panel:** Clean 4-button menu:
  - 🎬 *Latest Malayalam Movies* (Dynamic year-wise catalog)
  - 🎥 *Malayalam Dubbed Movies* (Separate year-wise dubbed catalog)
  - 🔎 *Movie Search Group* (Configurable external Telegram group link)
  - 📢 *Main Movie Channel* (Configurable external Telegram channel link)
- **Forward-Based Admin Upload:** Upload movie posters, multiple video files (720p, 1080p, etc.), and media albums directly inside the Telegram chat without downloading or re-uploading bytes.
- **Dual-Channel Force Subscribe:**
  - **Sub 1 (Fixed):** Permanent Main Movie Channel configured via environment variables. Verified via `getChatMember`.
  - **Sub 2 (Dynamic):** Fully managed via Admin Panel. Supports **Public Channel** or **Private Channel with Join Request** (`creates_join_request=True`).
  - **Instant Request-to-Join Policy:** When Private Sub 2 is enabled, receiving and recording the user's Join Request update is sufficient to satisfy the condition—users do not wait for manual approval.
- **Dynamic Menu Customization:** Reorder buttons, rename labels, enable/disable buttons, or update group/channel URLs on the fly from MongoDB without restarting the bot.
- **Year-Wise Catalog Management:** Automatically creates years upon upload. Admins can rename, toggle visibility, or delete years with confirmation. Users only see years containing active movies.
- **Rate-Limited Broadcast Engine:** Broadcast text, photos, videos, and documents to thousands of registered users with anti-flood pacing (`asyncio.sleep`), automatic retry on rate limits, and detection of blocked users.
- **Real-Time Statistics Dashboard:** Live calculations for total users, today's new users, active vs. blocked users, movie counts by category, total stored media, and broadcast metrics.

---

## 3. Technology Stack

| Component | Technology | Version / Specification |
|---|---|---|
| **Language** | Python | 3.12+ |
| **Bot Framework** | aiogram | 3.14+ |
| **Database** | MongoDB Atlas | MongoDB 6.0+ |
| **Async Mongo Driver** | Motor / PyMongo | Motor 3.6+, PyMongo 4.9+ |
| **Media Delivery** | Telegram Bot API | `copyMessage` & `copyMessages` |
| **Containerization** | Docker | Multi-stage / python:3.12-slim |
| **Hosting Platform** | Koyeb | Long Polling Worker |
| **Testing** | pytest & pytest-asyncio | pytest 8.3+, pytest-asyncio 0.24+ |

---

## 4. Architecture Overview

```
                      ┌───────────────────────────────────────┐
                      │             Telegram API              │
                      └──────────────────┬────────────────────┘
                                         │
                                Long Polling Updates
                                         │
                                         ▼
                      ┌───────────────────────────────────────┐
                      │          AdminAuthMiddleware          │
                      │   (Server-side ADMIN_ID validation)   │
                      └──────────┬─────────────────┬──────────┘
                                 │                 │
                  [Is Admin ID]  │                 │  [Regular User]
                                 ▼                 ▼
        ┌─────────────────────────────┐   ┌─────────────────────────────┐
        │        Admin Panel          │   │         User Panel          │
        ├─────────────────────────────┤   ├─────────────────────────────┤
        │ • Add Movie (Forward FSM)   │   │ • 🎬 Latest Malayalam Movies │
        │ • Manage Movies & Media     │   │ • 🎥 Malayalam Dubbed Movies│
        │ • Dynamic Menu Settings     │   │ • 🔎 Movie Search Group     │
        │ • Release Year Management   │   │ • 📢 Main Movie Channel     │
        │ • Sub 2 Configuration       │   └──────────────┬──────────────┘
        │ • Broadcast Worker          │                  │
        │ • Real-Time Statistics      │                  ▼
        │ • User Management           │   ┌─────────────────────────────┐
        └──────────────┬──────────────┘   │     Force Subscribe Check   │
                       │                  │ (Sub 1 Env + Sub 2 MongoDB) │
                       │                  └──────────────┬──────────────┘
                       │                                 │
                       │                  ┌──────────────┴──────────────┐
                       │                  │                             │
                       │            [Not Joined]                   [Verified]
                       │                  ▼                             ▼
                       │       ┌──────────────────────┐   ┌───────────────────────────┐
                       │       │ 🔒 Join Channels UI  │   │ Telegram copyMessage      │
                       │       │  + TRY AGAIN button  │   │ Zero-download delivery!   │
                       │       └──────────────────────┘   └───────────────────────────┘
                       │                                                ▲
                       └───────────────────┬────────────────────────────┘
                                           │
                                           ▼
                      ┌───────────────────────────────────────┐
                      │             MongoDB Atlas             │
                      │  users | movies | movie_messages      │
                      │  years | menu_settings | subscriptions│
                      │  join_requests | broadcasts | logs    │
                      └───────────────────────────────────────┘
```

---

## 5. Complete Folder Structure

```
Malayalam-Movie-Bot/
├── bot.py                        # Application entry point & long polling loop
├── config.py                     # Environment variables & runtime settings
├── requirements.txt              # Pinned Python dependencies
├── Dockerfile                    # Production Docker container definition
├── Procfile                      # Koyeb worker declaration
├── pytest.ini                    # Pytest configuration
├── .env.example                  # Environment template
├── .gitignore                    # Git ignore rules
├── .dockerignore                 # Docker build ignore rules
├── README.md                     # Comprehensive documentation
│
├── database/                     # MongoDB Atlas operations & repositories
│   ├── mongodb.py                # Database connection & index initialization
│   ├── users.py                  # User profile & registration CRUD
│   ├── movies.py                 # Movie catalog queries & mutations
│   ├── movie_messages.py         # Telegram media references storage
│   ├── years.py                  # Release year catalog operations
│   ├── settings.py               # Dynamic main menu button settings
│   ├── subscriptions.py          # Dynamic Sub 2 configuration
│   ├── join_requests.py          # Private Sub 2 join request tracking
│   ├── broadcasts.py             # Broadcast history & metrics
│   └── activity_logs.py          # Administrative audit logs
│
├── handlers/                     # aiogram 3 Telegram routers
│   ├── start.py                  # /start & user registration
│   ├── user_menu.py              # Main menu button router
│   ├── movie_catalog.py          # Year-wise movie catalog & pagination
│   ├── movie_delivery.py         # Force sub check & media delivery
│   ├── admin_dashboard.py        # /admin command & master dashboard
│   ├── add_movie.py              # Forward-based media upload FSM
│   ├── manage_movies.py          # Edit, update & delete movies
│   ├── manage_years.py           # Add, rename, toggle & delete years
│   ├── menu_settings.py          # Customize button labels, order & links
│   ├── subscription.py           # Configure Sub 2 & chat_join_request
│   ├── broadcast.py              # Controlled broadcast FSM
│   └── statistics.py             # Dashboard statistics & user list
│
├── keyboards/                    # Telegram inline keyboard builders
│   ├── user.py                   # Dynamic user menu & Force Sub markup
│   ├── admin.py                  # Admin dashboard, cancel & confirm markups
│   ├── movies.py                 # Year & movie catalog markups
│   └── pagination.py             # Reusable pagination helper
│
├── services/                     # Business logic services
│   ├── force_sub.py              # Dual-channel subscription verification
│   ├── media_manager.py          # copyMessage / copyMessages delivery
│   ├── broadcast_service.py      # Async broadcast worker with rate limits
│   ├── menu_manager.py           # Dynamic menu retrieval logic
│   └── statistics_service.py     # Real-time metrics aggregation
│
├── middlewares/                  # aiogram middlewares
│   ├── admin_auth.py             # Server-side authorization & IsAdminFilter
│   └── rate_limit.py             # User anti-flood limiter
│
├── utils/                        # Utilities & formatting
│   ├── logger.py                 # Structured logging with token masking
│   ├── validators.py             # Validation for URLs, IDs & years
│   └── helpers.py                # HTML escaping & formatting
│
└── tests/                        # Automated test suite
    ├── conftest.py               # In-memory MongoDB mock fixtures
    ├── test_admin_auth.py        # Admin security tests
    ├── test_force_sub.py         # All 6 Force Subscribe combination tests
    ├── test_movies.py            # Movie CRUD & media reference tests
    └── test_menu.py              # Dynamic menu customization tests
```

---

## 6. BotFather Setup

1. Open Telegram and search for [@BotFather](https://t.me/BotFather).
2. Send `/newbot` to create a new bot.
3. Choose a name (e.g., `Malayalam Movie Bot`) and a username ending in `bot` (e.g., `malayalam_movies_hd_bot`).
4. Copy the generated **HTTP API Token** (e.g., `7123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ`).
5. Configure bot settings in BotFather:
   - Send `/setprivacy` -> Select your bot -> Choose **Disable** (Allows the bot to receive messages/forwards in admin workflows).
   - Send `/setcommands` -> Send:
     ```
     start - Open the main movie catalog
     admin - Open the administrator control panel
     ```

---

## 7. Admin ID Setup

The bot enforces single-administrator authorization based on your numeric Telegram user ID:
1. Search for [@userinfobot](https://t.me/userinfobot) or [@MissRose_bot](https://t.me/MissRose_bot) on Telegram.
2. Send `/start` or `/id`.
3. Note your numeric **Id** (e.g., `123456789`).
4. Set this number as `ADMIN_ID` in your environment configuration.

---

## 8. MongoDB Atlas Setup

1. Sign up or log in at [MongoDB Atlas](https://www.mongodb.com/cloud/atlas).
2. Create a free **M0 Shared Cluster**.
3. Under **Database Access**:
   - Create a database user (e.g., `botadmin`) with password authentication and **Read and write to any database** privileges.
4. Under **Network Access**:
   - Click **Add IP Address** and choose **Allow Access From Anywhere** (`0.0.0.0/0`) so Koyeb cloud workers can connect.
5. In **Clusters**, click **Connect** -> **Drivers** -> Select **Python** (version 3.12 or later).
6. Copy the connection string:
   ```
   mongodb+srv://botadmin:<password>@cluster0.abcde.mongodb.net/?retryWrites=true&w=majority
   ```
   *(Replace `<password>` with your database user password).*

---

## 9. Local Installation

### Prerequisites
- Python 3.12 or higher
- Git

### Steps
```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/malayalam-movie-bot.git
cd malayalam-movie-bot

# Create and activate a virtual environment
python -m venv venv

# On Linux / macOS:
source venv/bin/activate
# On Windows PowerShell:
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 10. Environment Configuration

Copy the example environment file:
```bash
cp .env.example .env
```

Edit `.env` with your actual credentials:
```env
# Telegram Bot Token from @BotFather
BOT_TOKEN=7123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ

# Single Administrator Numeric Telegram User ID
ADMIN_ID=123456789

# MongoDB Atlas Connection URI
MONGO_URI=mongodb+srv://botadmin:YourStrongPassword@cluster0.abcde.mongodb.net/?retryWrites=true&w=majority

# MongoDB Database Name
DATABASE_NAME=malayalam_movie_bot

# Fixed Sub 1 (Main Movie Channel)
# Must begin with -100 for Telegram channels/supergroups
SUB1_CHANNEL_ID=-1001234567890

# Permanent Invite Link for Main Movie Channel
SUB1_INVITE_URL=https://t.me/your_main_channel
```

> [!IMPORTANT]
> **Sub 2 is NOT configured in `.env`**. Sub 2 is managed dynamically from the Admin Panel and stored in MongoDB.

---

## 11. Running Locally

Run the bot with:
```bash
python bot.py
```

Expected log output:
```
2026-11-17 12:00:00 | INFO     | MalayalamMovieBot:bot:28 - Initializing Malayalam Movie Bot...
2026-11-17 12:00:01 | INFO     | MalayalamMovieBot:mongodb:24 - Connecting to MongoDB Atlas...
2026-11-17 12:00:02 | INFO     | MalayalamMovieBot:mongodb:33 - MongoDB connected successfully to database: malayalam_movie_bot
2026-11-17 12:00:02 | INFO     | MalayalamMovieBot:mongodb:50 - Ensuring MongoDB collection indexes...
2026-11-17 12:00:03 | INFO     | MalayalamMovieBot:mongodb:82 - MongoDB indexes verified successfully.
2026-11-17 12:00:03 | INFO     | MalayalamMovieBot:bot:65 - Registered all routers and middlewares.
2026-11-17 12:00:04 | INFO     | MalayalamMovieBot:bot:77 - Starting long polling with allowed updates: ['message', 'callback_query', 'chat_join_request']
```

To run the automated test suite:
```bash
pytest
```

---

## 12. Admin Usage Instructions

1. Open Telegram and send `/admin` (or click **⚡ Open Admin Dashboard** on `/start`).
2. The bot displays the **9-Button Control Panel**:
   - **🎬 Add Movie:** Launch forward-based media upload workflow.
   - **📂 Manage Movies:** Edit titles, change release years, switch categories, append media, or delete movies.
   - **⚙️ Menu Settings:** Customize the 4 main menu buttons (labels, ordering, URLs, enable/disable).
   - **📅 Manage Years:** Add years, rename years, toggle visibility, or delete years.
   - **📢 Add Sub:** Configure, toggle, or remove Sub 2 channel (Public vs Private Request).
   - **📨 Broadcast:** Send messages or media to all registered users with anti-flood controls.
   - **👥 Users:** View user statistics and the 10 most recent registrations.
   - **📊 Statistics:** View live catalog numbers, user counts, and audit logs.
   - **🔧 Bot Settings:** View system status and environment configuration.

---

## 13. Adding Movies (Forward-Based Upload)

This workflow requires **no external website or file re-uploading**:

1. Click **🎬 Add Movie** in the Admin Dashboard.
2. **Select Category:**
   - *Latest Malayalam Movies* OR *Malayalam Dubbed Movies*.
3. **Select or Enter Year:**
   - Tap one of the quick year buttons (e.g., `2026`) or type any 4-digit year as a message.
4. **Enter Movie Title:**
   - Type the name (e.g., `Manjummel Boys`).
5. **Send or Forward Media Files:**
   - Send or forward the **poster** (photo or document).
   - Send or forward the **video files** (e.g., 480p, 720p, 1080p).
   - Forward albums or additional files.
   - The bot replies with a live counter: `✅ Received message #1 (Photo)!`, `✅ Received message #2 (Video)!`.
6. Click **✅ Finish Upload**:
   - The movie metadata and Telegram source message IDs are stored in MongoDB.
   - The movie becomes immediately available in the user catalog.

---

## 14. Configuring Sub 2 (Public vs Private Request)

Sub 2 can be configured dynamically without restarting the bot:

1. Click **📢 Add Sub (Sub 2)** in the Admin Dashboard.
2. Click **➕ Setup Sub 2 Channel**.
3. **Step 1:** Send the numeric Channel ID (e.g., `-1001987654321`). Make sure the bot is an Administrator in this channel.
4. **Step 2:** Choose the Channel Type:
   - **🌐 Public Channel:** Users must join directly. Membership is verified via `getChatMember`.
   - **🔒 Private Channel (Join Request):** The channel uses join requests. The bot auto-generates a link with `creates_join_request=True` or accepts your custom link.
5. **Step 3:** Confirm the invite link.

### Switching Modes & Toggling
- Click **🔴 Disable Sub 2 / 🟢 Enable Sub 2** to temporarily pause or resume Sub 2 checks.
- Click **🔄 Switch to Private / Switch to Public** to toggle verification modes.
- Click **🗑 Remove Sub 2** to completely delete the Sub 2 requirement.

---

## 15. Force Subscribe Behaviour & Business Rules

When a user taps on any movie in the catalog:

1. **Sub 1 Verification (Mandatory):**
   - The bot calls Telegram's `getChatMember` on `SUB1_CHANNEL_ID`.
   - Status must be `member`, `administrator`, or `creator`.
2. **Sub 2 Verification (if enabled):**
   - **If Public:** Verified via `getChatMember`.
   - **If Private (Request to Join):** The bot checks MongoDB for a recorded `chat_join_request` for that user.
3. **Business Rule for Join Requests:**
   - *The administrator does NOT need to approve the join request before movie access.*
   - Receiving and recording the user's Join Request update is sufficient to satisfy Sub 2.
   - The bot does not call `approveChatJoinRequest` automatically.
4. **If Verification Fails:**
   - The movie is NOT delivered.
   - The bot displays:
     ```
     🔒 JOIN REQUIRED CHANNELS

     To access this movie, you must join our official channel(s) below.
     [📢 Join Main Movie Channel]
     [➕ Join Additional Channel]
     [🔄 TRY AGAIN]
     ```
5. **When User Clicks `🔄 TRY AGAIN`:**
   - Performs a fresh check on both channels.
   - If satisfied: Delivers all movie media files instantly using `copyMessage`.
   - If still missing: Shows an alert specifying which channel(s) still need to be joined.

---

## 16. Broadcast Usage

1. Click **📨 Broadcast** in the Admin Dashboard.
2. The bot displays the total count of active eligible users.
3. Send or forward any message:
   - Plain text
   - Photo with caption
   - Video with caption
   - Document or audio
4. Review the preview and click **🚀 Confirm Broadcast**.
5. The worker delivers messages with anti-flood pacing (`asyncio.sleep(0.05)`) and handles rate limits:
   - Automatically catches `TelegramRetryAfter` and sleeps the required seconds.
   - Catches `TelegramForbiddenError` (when a user blocked the bot) and marks the user as `blocked` in MongoDB.
6. A final summary report is delivered:
   ```
   📊 Broadcast Execution Report
   • Total Target Users: 10,000
   • ✅ Delivered Successfully: 9,500
   • 🚫 Blocked Bots / Inaccessible: 450
   • ⚠️ Other Failures: 50
   ```

---

## 17. GitHub Upload Instructions

Run the following commands in your project directory:

```bash
# 1. Initialize Git repository
git init

# 2. Stage all files (Verify that .env is NOT staged!)
git add .

# 3. Check status to ensure .env is ignored
git status

# 4. Commit initial codebase
git commit -m "Complete Telegram Movie Bot production release"

# 5. Set default branch to main
git branch -M main

# 6. Add your GitHub remote repository
git remote add origin https://github.com/YOUR_USERNAME/malayalam-movie-bot.git

# 7. Push code to GitHub
git push -u origin main
```

---

## 18. Koyeb Deployment Guide

Deploying on Koyeb as a Docker Worker ensures 24/7 reliability without competing polling instances:

### Step 1: Create a Koyeb Account
Go to [koyeb.com](https://www.koyeb.com) and log in.

### Step 2: Create a New App
1. Click **Create App**.
2. Select **GitHub** as the deployment method.
3. Select your repository: `YOUR_USERNAME/malayalam-movie-bot`.
4. Branch: `main`.

### Step 3: Configure Service Type
1. Choose **Worker** (not Web Service, because long polling does not listen on an HTTP port).
2. Builder: **Dockerfile** (Koyeb detects `Dockerfile` automatically).

### Step 4: Add Environment Variables
In the Koyeb environment variable editor, add:

| Key | Example Value | Description |
|---|---|---|
| `BOT_TOKEN` | `7123456789:ABC...` | From @BotFather |
| `ADMIN_ID` | `123456789` | Your numeric Telegram ID |
| `MONGO_URI` | `mongodb+srv://...` | MongoDB Atlas URI |
| `DATABASE_NAME` | `malayalam_movie_bot` | Database name |
| `SUB1_CHANNEL_ID` | `-1001234567890` | Fixed Channel ID |
| `SUB1_INVITE_URL` | `https://t.me/your_main_channel` | Fixed Channel Link |

### Step 5: Deploy
1. Click **Deploy**.
2. Koyeb will build the Docker container and start `python bot.py`.
3. Check the **Runtime Logs** to confirm successful MongoDB connection and polling startup:
   ```
   MongoDB connected successfully to database: malayalam_movie_bot
   Starting long polling with allowed updates: ['message', 'callback_query', 'chat_join_request']
   ```

> [!IMPORTANT]
> Ensure only **ONE** instance/replica is running. Telegram long polling allows only one active connection per bot token.

---

## 19. Troubleshooting Guide

### Issue: Bot not responding to `/admin`
- **Cause:** Your Telegram user ID does not match `ADMIN_ID`.
- **Solution:** Send `/id` to [@userinfobot](https://t.me/userinfobot), verify your numeric ID, and update `ADMIN_ID` in `.env` / Koyeb.

### Issue: `TelegramBadRequest: Chat not found` during Sub 1 verification
- **Cause:** The bot is not an Administrator in the Sub 1 channel, or the channel ID is incorrect.
- **Solution:** Ensure `SUB1_CHANNEL_ID` begins with `-100` and the bot is added to the channel as an Administrator with invite permissions.

### Issue: Users receive Force Sub prompt even after requesting to join Sub 2
- **Cause:** Telegram has not delivered `chat_join_request` updates.
- **Solution:** Verify that the Sub 2 invite link has `creates_join_request=True` enabled and the bot is an Administrator in the Sub 2 channel.

### Issue: `TelegramConflictError: Terminated by other getUpdates request`
- **Cause:** Two bot instances are running simultaneously with the same `BOT_TOKEN` (e.g., local machine + Koyeb).
- **Solution:** Stop your local test process or terminate redundant workers.

### Issue: Media delivery fails with `message can't be copied`
- **Cause:** The original forwarded message was deleted from the admin's chat or channel.
- **Solution:** Keep the source channel/messages intact, or use the built-in `file_id` fallback.

---

## 20. Security Guidelines

1. **Never commit `.env` to Git:** `.env` is listed in `.gitignore`.
2. **Server-Side Enforcement:** Every administrative callback and command is verified through `AdminAuthMiddleware` and `IsAdminFilter`.
3. **Secret Masking:** Application logs filter out bot tokens and database passwords automatically.
4. **No Arbitrary Code Execution:** The bot accepts structured inputs and validates years, URLs, and numeric IDs with strict type-checking.
5. **Non-Root Container:** The Dockerfile executes the bot under a restricted non-root user (`botuser`).
