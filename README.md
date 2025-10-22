## 🪙 Online Pricer Bot

**A Telegram bot for real-time crypto and currency price monitoring, alerts, and broadcasting — with advanced group, channel, and admin capabilities.**

---

## 📌 Overview

Online Pricer Bot allows users to:

- Track live prices of cryptocurrencies, currencies, and gold
- Set price alerts
- Use the bot in groups as a price calculator and announcer
- Connect their own Telegram channels for automated posting
- Upgrade to VIP for enhanced features
- Administer and monitor usage with rich statistics and control
- Supports Both Persian & English languages; And a middle stage: Persian with English symbols; Which user selects at bot start up.

---

## 💡 Features

### 👥 For Users

- 🔎 **Smart Price Search**:
  - Search tokens or currencies by **symbol**, **Persian name**, or **English name**
  - Works in both **private chat** and **groups**

- 🛠️ **Customizable Watchlists**:
  - Add specific coins, currencies, or gold types to monitor
  - Use `/get` or the inline calculator keyboard to get your selected prices

- 📢 **Group Integration**:
  - Use the bot in groups as a **price announcer** or **price calculator**
  - Each group can have a separate custom token list
  - Group usage requires VIP status

- 📡 **Channel Integration**:
  - Users can link their own Telegram **channels** to schedule price updates
  - Each user configures their own update interval and token list
  - Channel activation requires VIP

- 🚨 **Price Alerts**:
  - Set alerts for specific tokens/currencies to notify you when they reach a desired price

- 🌟 **VIP Upgrade**:
  - Allows longer watchlists
  - Enables group and channel integrations
  - Required for advanced features

---

### 🛡️ For Admins

- 📈 **Statistics Dashboard**:
  - Daily, weekly, monthly, and yearly statistics on: [God Admin only]
    - User messages
    - New users
    - VIP upgrades
    - Group and channel activation

- 🔧 **User Management**:
  - Upgrade users to **staff admins** [God Admin only]
  - View all VIP users [God Admin only]
  - Manually upgrade users to VIP.

- 📬 **Broadcast Tools**: [God Admin only]
  - Send **ads or announcements** to all users
  - Auto-delete Ads/Announcements too.
  - Broadcasts can include text, images, audio, etc.

- 🧾 **VIP Plan Management**: [God Admin only]
  - Update the list of available VIP plans shown to users

---

## ⚙️ Setup

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/pya-h/online_pricer_bot.git
   cd online_pricer_bot

2. **Install Dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

3. **Create `.env` File**:

   ```env
    BOT_TOKEN=
    BOT_USERNAME=
    NAVASAN_API_KEY=
    ABAN_TETHER_TOKEN=
    COINMARKETCAP_API_KEY=
    CHANNEL_ID=
    CHANNEL_USERNAME=
    CHANNEL_URL=
    SECOND_CHANNEL_ID=
    SECOND_CHANNEL_USERNAME=
    SECOND_CHANNEL_URL=
    ADMIN_USERNAME=
    ADMIN_PASSWORD=
    HARDCODE_ADMIN_USERNAME=
    HARDCODE_ADMIN_CHATID=
    DATABASE_HOST=
    DATABASE_USERNAME=
    DATABASE_PASSWORD=
    DATABASE_NAME=
    HOST_URL=
    BOT_TAG=
    BOT_PORT=
    RUN_METHOD=
    MAIN_CHANNEL_DEFAULT_INTERVAL=
   ```

---

## 💬 Commands

> Some commands have been **shortened or revised** from earlier versions.

### 🔓 General User Commands

| Command           | Description                                         |
| ----------------- | --------------------------------------------------- |
| `/start`          | Start the bot                                       |
| `/view`           | Get current prices based on user list               |
| `/view_list`      | Config user's view prices tokens list               |
| `/calculator`     | Enter calculator mode                               |
| `/calculator_list`| Config user's calculator tokens list                |
| `/alert`          | Set a new price alert                               |
| `/alert_list`     | View user's ongoing price alerts                    |
| `/channels`       | Open channel's panel                                |
| `/groups`         | Open group's panel                                  |
| `/lang`           | Switch bot language between Persian & English       |
| `/vip`            | Show available VIP plans                            |
| `/my_plan`        | Show user's current plan                            |
| `/settings`       | Open settings panel                                 |

### 🧙 Admin Commands

After login, these commands are available:

| Command                | Description                                  |
| ---------------------- | -------------------------------------------- |
| `/stats`               | Show daily/weekly/monthly/yearly usage stats |
| `/add_admin`           | Promote a user to staff Admin level (God)    |
| `/rem_admin`           | Downgrade a staff Admin to Normal level (God)|
| `/post`                | Broadcast a message to all users (God)       |
| `/newplans`            | Update the VIP plan list (God)               |
| `/up`                  | Promote a user to VIP                        |
| `/down`                | Downgrade a user to free plan                |
| `/api_keys`            | Show the list of free API keys bot is using  |
| `/add_api {key}`       | Add new free CoinMarketCap API key.          |
| `/rem_api {key}`       | Remove a free CoinMarketCap API key.         |

---

## 📌 Notes
* Admin API key manager is for looping between free CoinMarketCap API keys, in order to prevent limitation. 
* Persian language support is embedded but user can also use English or Persian with English symbols.
* Inline keyboards are used for intuitive navigation
* User state and settings are persisted for individual experience
* Some features (group usage, channel linking, longer lists) require VIP status
* There are other features that do not have /command input, but are easily accessed with ReplyMarkup keyboard.
* Bot have force Channel membership support; Only allowing usage after user follows certain channels. 
---

## 📎 Example Use Cases

* Use in a **crypto Telegram group** to fetch and announce price of ETH in Tomans
* Connect a **personal channel** to post BTC and USD prices every 15 minutes
* Set an alert to notify when **USDT price drops below 50,000 Tomans**
* Admins can **send promotional messages** to all users with auto-deletion