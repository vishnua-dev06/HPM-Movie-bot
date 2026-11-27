# 🎬 Malayalam Movie Bot

A production-ready, high-performance Telegram Movie Catalog and Media Delivery Bot built with **Python 3.12**, **aiogram 3**, and **MongoDB Atlas**. Designed for seamless one-click Koyeb worker deployment with forward-based Telegram media uploads, zero-reupload delivery using `copyMessage`, dual-channel Force Subscribe verification (including instant Request-to-Join support), dynamic menu and year management, **dedicated User Log Channel integration**, **multiple administrator management**, and an **enterprise-grade Advanced Broadcast Engine** scalable to 100,000–300,000 users with crash recovery.

---

## 📑 Table of Contents

1. [Project Introduction](#1-project-introduction)
2. [Key Features](#2-key-features)
3. [Technology Stack](#3-technology-stack)
4. [Architecture Overview](#4-architecture-overview)
5. [Complete Folder Structure](#5-complete-folder-structure)
6. [BotFather Setup](#6-botfather-setup)
7. [Admin Configuration (Multiple Trusted Admins)](#7-admin-configuration-multiple-trusted-admins)
8. [User Log Channel Setup](#8-user-log-channel-setup)
9. [MongoDB Atlas Setup](#9-mongodb-atlas-setup)
10. [Local Installation](#10-local-installation)
11. [Environment Configuration](#11-environment-configuration)
12. [Running Locally](#12-running-locally)
13. [Admin Usage Instructions](#13-admin-usage-instructions)
14. [Adding Movies (Forward-Based Upload)](#14-adding-movies-forward-based-upload)
15. [Configuring Sub 2 (Public vs Private Request)](#15-configuring-sub-2-public-vs-private-request)
16. [Force Subscribe Behaviour & Business Rules](#16-force-subscribe-behaviour--business-rules)
17. [Advanced Broadcast Engine (100k–300k Users)](#17-advanced-broadcast-engine-100k300k-users)
18. [Admin Management Section](#18-admin-management-section)
19. [GitHub Upload Instructions](#19-github-upload-instructions)
20. [Koyeb Deployment Guide](#20-koyeb-deployment-guide)
21. [Railway Deployment Guide](#21-railway-deployment-guide)
22. [Automated Testing & Quality Assurance](#22-automated-testing--quality-assurance)
23. [Troubleshooting Guide](#23-troubleshooting-guide)
24. [Security Guidelines](#24-security-guidelines)

---

## 1. Project Introduction

**Malayalam Movie Bot** is a single-bot Telegram solution that provides users with an intuitive, year-wise movie catalog while granting administrators total control over content, channels, dynamic menus, admins, and broadcasts directly through Telegram buttons.

The bot eliminates the need for expensive file storage and external websites by utilizing Telegram's native `copyMessage` and `copyMessages` APIs to reference and deliver posters, videos, and multi-file albums directly to users with instant speed.

---

## 2. Key Features

- **Multiple Administrator Management:** Server-side authorization supporting multiple trusted admins via environment variables (`ADMIN_IDS`) and dynamic runtime addition/removal through the Admin Panel with primary owner protection.
- **Dedicated User Log Channel:** Automatically posts a formatted notification to a private channel whenever a new user starts the bot for the first time. Non-blocking and failsafe.
- **Advanced High-Performance Broadcast Engine:**
  - Multi-message collection: Broadcast text, photos, videos, documents, audio, voice notes, stickers, animations, and media albums in a single broadcast.
  - Interactive Preview: Review content copies directly in chat before confirming.
  - Scalable to 100,000–300,000 users using database batch streaming (`BROADCAST_BATCH_SIZE=500`) and controlled concurrency (`BROADCAST_CONCURRENCY=5`).
  - Durable state in MongoDB with **crash/restart recovery**: Automatically resumes unfinished broadcasts after application restarts.
  - Rate limiting, `RetryAfter` handling, and exponential backoff retry.
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
                      │  (Multi-Admin Server-Side Validation) │
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
        │ • Multiple Admin Management │                  │
        │ • User Log Channel Settings │                  ▼
        │ • Advanced Broadcast Worker │   ┌─────────────────────────────┐
        │ • Real-Time Statistics      │   │  First Time User -> Log Ch  │
        └──────────────┬──────────────┘   │  Force Subscribe Check      │
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
                      │  admins | broadcasts | user_activity  │
                      │  broadcast_recipients | log_settings  │
                      └───────────────────────────────────────┘
```

---

## 5. Complete Folder Structure

```
Malayalam-Movie-Bot/
├── bot.py                        # Entry point, recovery hook & polling loop
├── config.py                     # Environment variables & multi-admin settings
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
│   ├── mongodb.py                # Database connection, indexes & admin seed
│   ├── admins.py                 # Multi-admin authorization repository
│   ├── users.py                  # User profile, tracking & batch streaming
│   ├── movies.py                 # Movie catalog queries & mutations
│   ├── movie_messages.py         # Telegram media references storage
│   ├── years.py                  # Release year catalog operations
│   ├── settings.py               # Dynamic main menu button settings
│   ├── subscriptions.py          # Dynamic Sub 2 configuration
│   ├── join_requests.py          # Private Sub 2 join request tracking
│   ├── broadcasts.py             # Durable broadcast jobs & state
│   ├── broadcast_recipients.py   # Recipient-level delivery tracking
│   ├── user_activity.py          # User activity event repository
│   ├── log_channel.py            # User Log Channel persistence
│   └── activity_logs.py          # Administrative audit logs
│
├── handlers/                     # aiogram 3 Telegram routers
│   ├── start.py                  # /start, registration & log channel alert
│   ├── user_menu.py              # Main menu button router
│   ├── movie_catalog.py          # Year-wise movie catalog & pagination
│   ├── movie_delivery.py         # Force sub check & media delivery
│   ├── admin_dashboard.py        # /admin command & master dashboard
│   ├── admin_management.py       # Add, remove, view multiple administrators
│   ├── log_channel_settings.py   # Log channel config, toggles & test tool
│   ├── add_movie.py              # Forward-based media upload FSM
│   ├── manage_movies.py          # Edit, update & delete movies
│   ├── manage_years.py           # Add, rename, toggle & delete years
│   ├── menu_settings.py          # Customize button labels, order & links
│   ├── subscription.py           # Configure Sub 2 & chat_join_request
│   ├── broadcast.py              # Multi-message broadcast FSM & preview
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
│   ├── broadcast_service.py      # High-performance async broadcast engine
│   ├── log_channel_service.py    # Log channel alerts & connection testing
│   ├── menu_manager.py           # Dynamic menu retrieval logic
│   └── statistics_service.py     # Real-time metrics aggregation
│
├── middlewares/                  # aiogram middlewares
│   ├── admin_auth.py             # Server-side multi-admin authorization
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
    ├── test_admin_management.py  # Multiple admin operations tests
    ├── test_user_logging.py      # User Log Channel tests
    ├── test_broadcast.py         # Advanced broadcast engine tests
    ├── test_force_sub.py         # All 6 Force Subscribe combination tests
    ├── test_movies.py            # Movie CRUD & media reference tests
    └── test_menu.py              # Dynamic menu customization tests
```

---

## 6. BotFather Setup

1. Open Telegram and search for [@BotFather](https://t.me/BotFather).
2. Send `/newbot` to create a new bot.
3. Choose a name and username ending in `bot`.
4. Copy the generated **HTTP API Token**.
5. Configure privacy and commands in BotFather:
   - Send `/setprivacy` -> Select your bot -> Choose **Disable** (Allows the bot to receive messages/forwards during uploads and broadcasts).
   - Send `/setcommands` -> Send:
     ```
     start - Open the main movie catalog
     admin - Open the administrator control panel
     ```

---

## 7. Admin Configuration (Multiple Trusted Admins)

The bot supports multiple administrators simultaneously:

1. Obtain the numeric Telegram IDs of all trusted administrators using [@userinfobot](https://t.me/userinfobot).
2. In `.env`, configure `ADMIN_IDS` with comma- or space-separated values:
   ```env
   ADMIN_IDS=123456789,987654321,555555555
   ```
3. The first administrator listed automatically becomes the **Primary Owner**.
4. Additional administrators can be dynamically added or removed at any time through the **Admin Management** panel in Telegram!

---

## 8. User Log Channel Setup

The bot can send real-time alerts to a private Telegram channel whenever a new user starts the bot:

1. Create a private Telegram Channel (e.g., `Movie Bot Logs`).
2. Add your bot as an **Administrator** in this channel with **Post Messages** permissions.
3. Get the numeric Channel ID (usually starts with `-100`, e.g., `-1001987654321`). You can forward a message from the channel to [@userinfobot].
4. Set `LOG_CHANNEL_ID` in your `.env` file, or configure it directly in the Admin Panel under **📡 Log Channel Settings** -> **Configure Channel ID**.
5. Click **🧪 Test Connection** in the Admin Panel to verify that the bot can post to the channel.

### Log Message Format
```
🆕 NEW USER STARTED THE BOT

User ID: 123456789
Username: @example_user
First Name: Example
Last Name: User
Profile: Telegram Profile Link
Registered Date: 27 November 2026
Registered Time: 10:30 AM UTC
Language Code: en
```

---

## 9. MongoDB Atlas Setup

1. Sign up or log in at [MongoDB Atlas](https://www.mongodb.com/cloud/atlas).
2. Create a free **M0 Shared Cluster**.
3. Under **Database Access**, create a user with read/write access.
4. Under **Network Access**, add `0.0.0.0/0` (Allow Access From Anywhere) for cloud deployment.
5. In **Clusters** -> **Connect** -> **Drivers** -> Copy the connection string:
   ```
   mongodb+srv://<username>:<password>@cluster0.abcde.mongodb.net/?retryWrites=true&w=majority
   ```

---

## 10. Local Installation

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

## 11. Environment Configuration

Copy the example environment template:
```bash
cp .env.example .env
```

Edit `.env` with your credentials:
```env
# Telegram Bot Token from @BotFather
BOT_TOKEN=7123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ

# Multiple Administrator Numeric Telegram User IDs
ADMIN_IDS=123456789,987654321

# MongoDB Atlas Connection URI
MONGO_URI=mongodb+srv://botadmin:YourPassword@cluster0.abcde.mongodb.net/?retryWrites=true&w=majority
DATABASE_NAME=malayalam_movie_bot

# Fixed Sub 1 (Main Movie Channel)
SUB1_CHANNEL_ID=-1001234567890
SUB1_INVITE_URL=https://t.me/your_main_channel

# User Log Channel ID (Optional)
LOG_CHANNEL_ID=-1001987654321

# Advanced Broadcast Engine Configuration
BROADCAST_CONCURRENCY=5
BROADCAST_BATCH_SIZE=500
BROADCAST_DELAY_SECONDS=0.05
```

---

## 12. Running Locally

Run the bot:
```bash
python bot.py
```

Run tests:
```bash
pytest
```

---

## 13. Admin Usage Instructions

Send `/admin` to open the control panel. All authorized administrators have access to:

1. **🎬 Add Movie:** Launch forward-based media upload workflow.
2. **📂 Manage Movies:** Edit titles, change release years, switch categories, append media, or delete movies.
3. **⚙️ Menu Settings:** Customize the 4 main menu buttons (labels, ordering, URLs, enable/disable).
4. **📅 Manage Years:** Add years, rename years, toggle visibility, or delete years.
5. **📢 Add Sub (Sub 2):** Configure, toggle, or remove Sub 2 channel (Public vs Private Request).
6. **📨 Advanced Broadcast:** Multi-message collection, live preview, and high-performance delivery.
7. **👥 Admin Management:** Add trusted admins, remove secondary admins, view all authorized admins.
8. **📡 Log Channel Settings:** Configure Log Channel ID, toggle status, and test connection.
9. **👥 Users:** View user statistics and recent registrations.
10. **📊 Statistics:** Real-time catalog and operations dashboard.
11. **🔧 Bot Settings:** View system status and environment configuration.

---

## 14. Adding Movies (Forward-Based Upload)

1. Click **🎬 Add Movie** in the Admin Dashboard.
2. **Select Category:** *Latest Malayalam Movies* or *Malayalam Dubbed Movies*.
3. **Select or Enter Year:** Tap an existing year button or type any 4-digit year as a message.
4. **Enter Movie Title:** Type the name (e.g., `Manjummel Boys`).
5. **Send or Forward Media Files:**
   - Poster (photo or document).
   - Video files (e.g., 480p, 720p, 1080p).
   - Media albums or documents.
   - The bot replies with an interactive counter: `✅ Received message #1 (Photo)!`.
6. Click **✅ Finish Upload** to commit the movie and media references to MongoDB.

---

## 15. Configuring Sub 2 (Public vs Private Request)

1. Click **📢 Add Sub (Sub 2)** in the Admin Dashboard.
2. Click **➕ Setup Sub 2 Channel**.
3. **Step 1:** Send the numeric Channel ID (e.g., `-1001987654321`). Make sure the bot is an Administrator in this channel.
4. **Step 2:** Choose the Channel Type:
   - **🌐 Public Channel:** Verified via `getChatMember`.
   - **🔒 Private Channel (Join Request):** Auto-generates a join request link with `creates_join_request=True`.
5. **Step 3:** Confirm invite link.

---

## 16. Force Subscribe Behaviour & Business Rules

1. **Sub 1 (Permanent):** Verified via `getChatMember` on `SUB1_CHANNEL_ID`.
2. **Sub 2 (Dynamic):**
   - If Public: Verified via `getChatMember`.
   - If Private: Verified by checking MongoDB for a recorded `chat_join_request`.
3. **Business Rule:** Receiving and recording the user's Join Request update is sufficient to satisfy Sub 2. Users gain access immediately without waiting for administrator approval.
4. **TRY AGAIN Button:** Performs fresh verification and delivers files immediately upon success.

---

## 17. Advanced Broadcast Engine (100k–300k Users)

### Workflow
1. Click **📨 Advanced Broadcast** in the Admin Dashboard.
2. The bot enters **Broadcast Collection Mode**.
3. Send or forward one or multiple messages (text, photos, videos, albums, voice, stickers).
4. Review the collected message counter.
5. Buttons:
   - **➕ Add More Messages:** Continue appending messages.
   - **👁 Preview Broadcast:** Delivers exact copies of all messages to you in chat.
   - **🚀 SEND THIS MESSAGE:** Prompts confirmation with total active recipients.
6. Click **Confirm**:
   - The worker streams users from MongoDB in chunks of `BROADCAST_BATCH_SIZE=500`.
   - Dispatches under `BROADCAST_CONCURRENCY=5` workers.
   - Updates live progress in the Telegram message periodically.
   - Handles `TelegramRetryAfter` flood controls and exponential backoffs.
   - Flags blocked users as `is_blocked = True`.
7. **Crash / Restart Recovery:** If Koyeb or the server restarts during a broadcast, the bot automatically checks MongoDB on startup and resumes unfinished deliveries without duplicate deliveries!

---

## 18. Admin Management Section

1. Click **👥 Admin Management** in the Admin Dashboard.
2. **➕ Add Admin:** Send the numeric Telegram User ID of the new admin. Access is granted instantly in MongoDB.
3. **➖ Remove Admin:** Select from the list of removable secondary admins. The Primary Owner account is protected and the last admin cannot be removed.
4. **📋 View All Admins:** Displays all active admins, their roles, and added timestamps.

---

## 19. GitHub Upload Instructions

```bash
# 1. Initialize Git repository
git init

# 2. Stage all files (Verify that .env is NOT staged!)
git add .

# 3. Check status to ensure .env is ignored
git status

# 4. Commit initial codebase
git commit -m "Complete Telegram Movie Bot production release with multi-admin and broadcast engine"

# 5. Set default branch to main
git branch -M main

# 6. Add your GitHub remote repository
git remote add origin https://github.com/YOUR_USERNAME/malayalam-movie-bot.git

# 7. Push code to GitHub
git push -u origin main
```

---

## 20. Koyeb Deployment Guide

1. Log in to [koyeb.com](https://www.koyeb.com).
2. Click **Create App** -> Select **GitHub** -> Choose your repository.
3. Service Type: **Worker**.
4. Builder: **Dockerfile**.
5. Add Environment Variables:
   - `BOT_TOKEN`
   - `ADMIN_IDS`
   - `MONGO_URI`
   - `DATABASE_NAME`
   - `SUB1_CHANNEL_ID`
   - `SUB1_INVITE_URL`
   - `LOG_CHANNEL_ID` (optional)
   - `BROADCAST_CONCURRENCY` (5)
   - `BROADCAST_BATCH_SIZE` (500)
6. Click **Deploy**. Check Runtime Logs to confirm MongoDB connection, index creation, admin seeding, and polling startup!

---

## 21. Railway Deployment Guide

The repository includes native Railway configuration via [`railway.json`](file:///c:/Users/harid/OneDrive/Desktop/work/Telegram/railway.json), [`Procfile`](file:///c:/Users/harid/OneDrive/Desktop/work/Telegram/Procfile), and an automated lightweight HTTP health responder in [`bot.py`](file:///c:/Users/harid/OneDrive/Desktop/work/Telegram/bot.py) that automatically binds to Railway's `$PORT` environment variable.

### Step 1: Create a Railway Account & New Project
1. Log in to [railway.com](https://railway.com).
2. Click **+ New Project** -> Select **Deploy from GitHub repo**.
3. Select your repository: `YOUR_USERNAME/malayalam-movie-bot`.

### Step 2: Configure Environment Variables
In the Railway project dashboard, click on your service -> go to the **Variables** tab -> click **New Variable** (or **Raw Editor**) and add:

| Key | Example Value | Description |
|---|---|---|
| `BOT_TOKEN` | `7123456789:ABC...` | From @BotFather |
| `ADMIN_IDS` | `123456789,987654321` | Numeric Telegram IDs of trusted admins |
| `MONGO_URI` | `mongodb+srv://...` | MongoDB Atlas Connection String |
| `DATABASE_NAME` | `malayalam_movie_bot` | MongoDB Database Name |
| `SUB1_CHANNEL_ID` | `-1001234567890` | Fixed Channel ID (begins with -100) |
| `SUB1_INVITE_URL` | `https://t.me/your_main_channel` | Fixed Channel Link |
| `LOG_CHANNEL_ID` | `-1001987654321` | Private Log Channel ID (optional) |
| `BROADCAST_CONCURRENCY` | `5` | Broadcast worker concurrency |
| `BROADCAST_BATCH_SIZE` | `500` | User batch chunk size |

*(Note: `PORT` is automatically assigned and injected by Railway; the bot binds to it for health checks automatically).*

### Step 3: Deploy & Verify
1. Railway automatically reads `railway.json` and builds via `Dockerfile`.
2. Click the **Deployments** tab and view the deployment logs:
   ```
   MongoDB connected successfully to database: malayalam_movie_bot
   Bootstrapped 2 administrator(s) in MongoDB.
   Railway/Cloud HTTP health-check responder active on 0.0.0.0:8080
   Starting long polling with allowed updates: ['message', 'callback_query', 'chat_join_request']
   ```
3. Your bot is now live 24/7 on Railway!

> [!TIP]
> **Coexistence of Koyeb & Railway:** You can host on either Railway or Koyeb using the exact same codebase. However, do **not** run polling instances simultaneously with the same `BOT_TOKEN` on both platforms at once, as Telegram Bot API only allows one active polling process per token.

---

## 22. Automated Testing & Quality Assurance

The test suite covers all components with in-memory mock MongoDB collections:

```bash
pytest
```

### Test Coverage Highlights:
- **User Logging (`test_user_logging.py`):** First-time user alert, duplicate `/start` prevention, failsafe error handling, missing profile details.
- **Admin Management (`test_admin_management.py`):** Bootstrap, dynamic add/remove, owner protection, last admin guardrail.
- **Advanced Broadcast (`test_broadcast.py`):** Multi-message delivery, album group handling, blocked user detection, RetryAfter handling, crash/restart recovery.
- **Force Subscribe (`test_force_sub.py`):** All 6 combinations of Sub 1 and Sub 2 (Public & Private).
- **Movies & Catalogs (`test_movies.py`):** Dynamic year query, media message references, cascading delete.
- **Dynamic Menu (`test_menu.py`):** Label updates, ordering, enabling/disabling, URL updating, defaults restore.

---

## 23. Troubleshooting Guide

- **Bot not responding to `/admin`:** Verify that your Telegram user ID is listed in `ADMIN_IDS` or added via Admin Management.
- **Log channel not receiving messages:** Ensure the bot is an Administrator in the channel with Post Messages permission, and test via `🧪 Test Connection`.
- **Flood limits during broadcast:** The broadcast engine automatically catches `TelegramRetryAfter` and pauses safely. You can adjust `BROADCAST_DELAY_SECONDS` or `BROADCAST_CONCURRENCY` if needed.
- **Two bot instances running:** Ensure only one Koyeb worker, Railway worker, or local process is active per `BOT_TOKEN` to prevent polling conflicts.

---

## 24. Security Guidelines

1. **Never commit `.env`:** Keep tokens and connection URIs out of version control.
2. **Server-Side Enforcement:** Every administrative callback and command is verified through `AdminAuthMiddleware` and `IsAdminFilter`.
3. **Owner Protection:** Secondary administrators cannot remove the primary owner or the last remaining administrator.
4. **Secret Masking:** Application logs filter out bot tokens and database passwords automatically.
5. **Non-Root Container:** The Dockerfile executes the bot under a restricted non-root user (`botuser`).
