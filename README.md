
```markdown
# 🤖 Discord Bot & Flask Web Dashboard

A feature-rich, modular Discord bot paired with a modern Flask-based web dashboard. This project allows server administrators to manage bot settings, leveling systems, economy features, and moderation tools directly from a web interface using Discord OAuth2 authentication.

---

## 🚀 Features

* **Modular Discord Bot (`discord.py`):**
  * 🛡️ **Moderation (`moderation.py`):** Kick, ban, mute, and automated safety controls.
  * 📈 **Leveling System (`leveling.py`):** XP tracking, rank cards with custom visual generation (`card_generator.py`), and rewards.
  * 🎉 **Welcome System (`welcome.py`):** Customized greeting messages and welcome cards.
  * 🎵 **Music Player (`music.py` & `music_card.py`):** Audio streaming capabilities and music cards for voice channels.
  * 🛠️ **Utility (`utility.py`):** General commands like ping, server info, etc.

* **Flask Web Dashboard (`web/`):**
  * 🔐 **Discord OAuth2 Login (`auth.py`):** Secure authentication via user credentials.
  * 🎛️ **Guild Management:** Real-time permission checking to manage only the servers where you are an administrator.
  * 🖥️ **Dynamic Pages:** Includes Home (`index.html`), Features (`features.html`), Commands (`commands.html`), Tutorials (`tutorials.html`), Server Selection (`dashboard.html`), and Server Customization (`manage.html`).

---

## 📂 Project Structure

```text
discord-bot-project/
│
├── bot/                      # Discord bot core logic
│   ├── cogs/                 # Bot features and commands (Modules)
│   │   ├── moderation.py     # Kick, ban, mute commands
│   │   ├── leveling.py       # XP, rank, and card system
│   │   ├── welcome.py        # Welcome message and card
│   │   ├── music.py          # Music player (Optional)
│   │   └── utility.py        # General commands (ping, serverinfo, etc.)
│   ├── utils/                # Helper functions (Image Generator)
│   │   ├── card_generator.py # Rank/Welcome card creation using Pillow
│   │   └── music_card.py     # Music card creation helper
│   ├── config.py             # Configuration and token management
│   └── main.py               # Main bot execution file
│
├── database/                 # Database connections and schemas
│   ├── db.py                 # Connection setup
│   └── models.py             # Database tables or collections
│
├── web/                      # Website and Dashboard (Flask)
│   ├── static/               # CSS, JavaScript, and image assets (e.g., style.css)
│   ├── templates/            # HTML pages (Jinja2)
│   │   ├── commands.html     # Commands list page
│   │   ├── dashboard.html    # Server selection and dashboard overview
│   │   ├── features.html     # Features showcase page
│   │   ├── index.html        # Home page (Bot invite option)
│   │   ├── manage.html       # Specific server customization page
│   │   └── tutorials.html    # Tutorial guides page
│   ├── auth.py               # Discord OAuth2 login handler
│   └── app.py                # Web server execution file
│
├── .env                      # Secret tokens and configurations (Ignored in Git)
├── .gitignore                # Specifies intentionally untracked files to ignore
├── README.md                 # Project documentation and setup guide
└── requirements.txt          # Python dependencies (discord.py, Pillow, Flask, etc.)

```

---

## 🛠️ Prerequisites & Installation

1. **Clone the Repository:**
```bash
git clone [https://github.com/sujaanz/discord-bot-project.git](https://github.com/sujaanz/discord-bot-project.git)
cd discord-bot-project

```


2. **Install Dependencies:**
Make sure you have Python installed, then run:
```bash
pip install -r requirements.txt

```


3. **Configure Environment Variables:**
Create a `.env` file in the root directory and add your credentials securely:
```env
DISCORD_TOKEN=your_bot_token_here
CLIENT_ID=your_client_id_here
CLIENT_SECRET=your_client_secret_here
SECRET_KEY=your_flask_session_key_here

```



---

## 🚀 Running the Project

* **Run the Flask Web Dashboard:**
```bash
python web/app.py

```


* **Run the Discord Bot:**
```bash
python bot/main.py

```



---

## 👨‍💻 Author

* **Sk Sujaan Mondal**
* GitHub: [sujaanz](https://github.com/sujaanz)

```

