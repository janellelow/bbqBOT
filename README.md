# BBQ RSVP + Payment Bot — Full Setup Guide

No coding or terminal needed for any of this — everything below is clicking buttons on websites.

**What you'll end up with:**
- A Telegram bot your guests message to RSVP and send payment screenshots.
- A private webpage (like `https://your-bbq.up.railway.app`) you open in any browser to see who's paid.

---

## Part 1 — Create your Telegram bot (5 min)

1. Open Telegram (phone or desktop app).
2. In the search bar, type **BotFather** and open the chat with the account that has a blue checkmark (it's the official one, username `@BotFather`).
3. Tap **Start**.
4. Send the message: `/newbot`
5. It asks for a **name** — this is the display name guests see, e.g. `Janelle's BBQ Bot`. Type it and send.
6. It asks for a **username** — must be unique and end in `bot`, e.g. `janelle_bbq_2026_bot`. Type it and send. If it says taken, try again with small changes.
7. BotFather replies with a message containing a long **token**, like:
   `7123456789:AAHxyz-examplestring...`
   **Copy this whole token and save it somewhere** (e.g. a note on your phone). This is the key to your bot — don't share it publicly.
8. Note down your bot's username too (e.g. `janelle_bbq_2026_bot`) — guests will message `t.me/janelle_bbq_2026_bot` to reach it.

---

## Part 2 — Get the bot's code onto GitHub (10 min)

GitHub is just free file storage that Railway (next part) will read from. You don't need to know how to code.

1. Go to **github.com** and sign up for a free account if you don't have one (top right → Sign up).
2. Once logged in, click the **+** icon (top right) → **New repository**.
3. Name it `bbq-bot`. Leave it **Private**. Click **Create repository**.
4. On the new (empty) repo page, click **uploading an existing file** (a blue link in the middle of the page).
5. Unzip the `bbq-bot.zip` file I sent you on your computer first (double-click it, or right-click → Extract).
6. Open the unzipped `bbq-bot` folder. Select **all the files inside it** (app.py, bot.py, db.py, ocr.py, web.py, requirements.txt, Dockerfile, README.md) — select all and drag them into the GitHub upload box in your browser. (Drag the files themselves, not the outer folder.)
7. Scroll down, click the green **Commit changes** button.

Your code is now on GitHub. You won't need to touch this again unless you want to change something later.

---

## Part 3 — Deploy it on Railway so it's live 24/7 (10 min)

Railway is a hosting service with a free tier — this keeps your bot running even when your computer is off.

1. Go to **railway.app** → **Login** → choose **Login with GitHub** (easiest, links the two automatically).
2. Click **New Project** → **Deploy from GitHub repo**.
3. Find and select the `bbq-bot` repo you just created. (If it's not listed, click "Configure GitHub App" and give Railway access to that repo.)
4. Railway starts building automatically — let it run, this takes 2-3 minutes the first time.
5. Once it's deployed, click on the service box (it'll be named something like `bbq-bot`).
6. Go to the **Variables** tab. Add these one at a time (click **New Variable** for each):

   | Variable name | Value |
   |---|---|
   | `BOT_TOKEN` | the long token from Part 1, step 7 |
   | `ADMIN_IDS` | leave blank for now — you'll add this in Part 4 |
   | `EVENT_NAME` | e.g. `Saturday's BBQ` |
   | `DASHBOARD_PASSWORD` | make up a simple password, e.g. `bbq2026` — you'll use this to open the dashboard |

7. After adding variables, Railway will automatically redeploy. Wait for the status to show a green **"Success"** / checkmark.
8. Go to the **Settings** tab of the service → find **Networking** → click **Generate Domain**. Railway gives you a public link like `bbq-bot-production-xxxx.up.railway.app`. **Save this link** — this is your dashboard.

---

## Part 4 — Get your Telegram ID so /status commands work for you

1. On Telegram, open a chat with **your own bot** (search its username from Part 1, step 8).
2. Tap **Start**, then send: `/whoami`
3. It replies with your numeric Telegram ID, e.g. `842913556`.
4. Go back to Railway → your service → **Variables** → edit `ADMIN_IDS` → paste that number in. (If more than one person should be an admin, separate IDs with commas: `842913556,719234000`.)
5. Railway redeploys automatically — give it a minute.

---

## Part 5 — Try it out

1. Open your dashboard link from Part 3, step 8 in a browser. Enter the `DASHBOARD_PASSWORD` you set. You should see an empty table — that's correct, nobody has RSVP'd yet.
2. On Telegram, message your bot, send `/start`, tap "I'm coming", then send any photo as a test "screenshot."
3. Refresh the dashboard page (or wait up to 15 seconds — it auto-refreshes) — you should see yourself show up as coming, with the photo thumbnail.
4. Share your bot's link (`t.me/your_bot_username`) with your guests. As people RSVP and send screenshots, they'll appear on the dashboard automatically.

---

## Using it on the day

- Send guests your bot link: `t.me/your_bot_username`
- They tap **Start** → confirm attendance → send their payment screenshot whenever they pay.
- You open your dashboard link anytime to see: who's coming, who's paid, and a thumbnail of each screenshot.
- If the automatic OCR amount-reading gets something wrong (it sometimes will — different payment apps format screenshots differently), message your bot `/markpaid @theirhandle` or `/markunpaid @theirhandle` to fix it by hand.

## Good to know

- **The automatic amount-reading is a convenience, not proof of payment.** It reads text off the image; it can't confirm money actually moved or catch an edited screenshot. Glance at the thumbnails on the dashboard for anything marked "⚠️ review."
- **Guests without a Telegram @username** show up by their display name instead — fine for a small group, but worth keeping an eye out if two guests share a name.
- Keep your `DASHBOARD_PASSWORD` and `BOT_TOKEN` private — anyone with the token can control your bot, and anyone with the password can see guests' payment screenshots.
- Railway's free tier is enough for an event like this; if you ever see a "trial expired" notice, you'd need to add a card on Railway (it won't start charging without you upgrading).
