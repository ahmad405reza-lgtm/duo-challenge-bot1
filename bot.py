import os
import telebot
from telebot import types
import sqlite3
import random
import time
import json
from datetime import datetime
import logging

# تنظیمات لاگینگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# توکن ربات - مستقیماً قرار داده شده
BOT_TOKEN = "8381414632:AAGFI2Qe-Wjc6SED-JDeNmgY6cBaYdGeBYw"

# بررسی توکن
if not BOT_TOKEN or len(BOT_TOKEN) < 20:
    logger.error("❌ توکن نامعتبر است!")
    exit(1)

logger.info(f"✅ توکن با موفقیت تنظیم شد (طول: {len(BOT_TOKEN)} کاراکتر)")

# ایجاد ربات
try:
    bot = telebot.TeleBot(BOT_TOKEN)
    logger.info("✅ ربات با موفقیت ایجاد شد")
except Exception as e:
    logger.error(f"❌ خطا در ایجاد ربات: {e}")
    exit(1)

# مسیر دیتابیس
DB_PATH = 'duo_challenge.db'

# ایجاد اتصال به دیتابیس
conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30)
cursor = conn.cursor()

def init_database():
    try:
        # جدول کاربران
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            score INTEGER DEFAULT 0,
            games_played INTEGER DEFAULT 0,
            wins INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # جدول بازی‌های فعال
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS active_games (
            game_id INTEGER PRIMARY KEY AUTOINCREMENT,
            player1_id INTEGER,
            player2_id INTEGER,
            game_type TEXT,
            status TEXT DEFAULT 'waiting',
            game_data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # جدول دعوت‌ها
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS invitations (
            invitation_id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_user_id INTEGER,
            to_user_id INTEGER,
            game_type TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        conn.commit()
        logger.info("✅ دیتابیس با موفقیت راه اندازی شد")
    except Exception as e:
        logger.error(f"❌ خطا در راه اندازی دیتابیس: {e}")

init_database()

# تابع ثبت کاربر
def register_user(user_id, username, first_name, last_name):
    try:
        cursor.execute('''
        INSERT OR IGNORE INTO users (user_id, username, first_name, last_name)
        VALUES (?, ?, ?, ?)
        ''', (user_id, username, first_name, last_name))
        conn.commit()
        logger.info(f"✅ کاربر ثبت شد: {user_id}")
    except Exception as e:
        logger.error(f"❌ خطا در ثبت کاربر: {e}")

# منوی اصلی
def main_menu():
    keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn_play = types.KeyboardButton('🎮 شروع بازی')
    btn_leaderboard = types.KeyboardButton('🏆 لیدربورد')
    btn_profile = types.KeyboardButton('👤 پروفایل')
    btn_help = types.KeyboardButton('❓ راهنما')
    keyboard.add(btn_play, btn_leaderboard, btn_profile, btn_help)
    return keyboard

# منوی انتخاب بازی
def game_selection_menu():
    keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn_math = types.KeyboardButton('🧮 چالش ریاضی')
    btn_word = types.KeyboardButton('🔤 چالش کلمات')
    btn_memory = types.KeyboardButton('🧠 چالش حافظه')
    btn_trivia = types.KeyboardButton('📚 چالش اطلاعات عمومی')
    btn_back = types.KeyboardButton('🔙 بازگشت')
    keyboard.add(btn_math, btn_word, btn_memory, btn_trivia, btn_back)
    return keyboard

# هندلر start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    try:
        user_id = message.from_user.id
        username = message.from_user.username or "ندارد"
        first_name = message.from_user.first_name or "کاربر"
        last_name = message.from_user.last_name or ""
        
        # ثبت کاربر
        register_user(user_id, username, first_name, last_name)
        
        # بررسی پارامترهای دعوت
        if len(message.text.split()) > 1:
            params = message.text.split()[1]
            if params.startswith('invite_'):
                handle_invitation(params, user_id, message.chat.id)
                return
        
        welcome_text = f"""
🤖 به ربات Duo Challenge خوش آمدید!

👤 کاربر: {first_name}
✅ ربات با موفقیت اجرا شد!

🎮 برای شروع بازی از منوی زیر استفاده کنید:
        """
        
        bot.send_message(message.chat.id, welcome_text, reply_markup=main_menu())
        
    except Exception as e:
        logger.error(f"❌ خطا در start: {e}")
        bot.send_message(message.chat.id, "⚠️ خطایی رخ داده است. لطفا دوباره تلاش کنید.")

# مدیریت دعوت‌ها
def handle_invitation(params, to_user_id, chat_id):
    try:
        if params.startswith('invite_'):
            parts = params.split('_')
            if len(parts) >= 4:
                from_user_id = int(parts[1])
                game_type = parts[2]
                game_name = parts[3].replace('_', ' ')
                
                # ثبت دعوت
                cursor.execute('''
                INSERT INTO invitations (from_user_id, to_user_id, game_type, status)
                VALUES (?, ?, ?, ?)
                ''', (from_user_id, to_user_id, game_type, 'accepted'))
                conn.commit()
                
                # ایجاد بازی
                cursor.execute('''
                INSERT INTO active_games (player1_id, player2_id, game_type, status)
                VALUES (?, ?, ?, ?)
                ''', (from_user_id, to_user_id, game_type, 'active'))
                conn.commit()
                
                game_id = cursor.lastrowid
                
                # اطلاع به دعوت کننده
                try:
                    from_name = get_user_name(from_user_id)
                    to_name = get_user_name(to_user_id)
                    bot.send_message(from_user_id, f"✅ {to_name} دعوت شما برای بازی {game_name} را پذیرفت! 🎮")
                except Exception as e:
                    logger.error(f"خطا در اطلاع به دعوت کننده: {e}")
                
                # اطلاع به دعوت شده
                bot.send_message(chat_id, f"✅ شما دعوت {from_name} برای بازی {game_name} را پذیرفتید! 🎮")
                
                # شروع بازی
                if game_type == 'math':
                    start_math_game(game_id, from_user_id, to_user_id)
                else:
                    bot.send_message(chat_id, f"🎯 بازی #{game_id} شروع شد! نوع بازی: {game_name}")
                    
    except Exception as e:
        logger.error(f"❌ خطا در handle_invitation: {e}")

# دریافت نام کاربر
def get_user_name(user_id):
    try:
        cursor.execute('SELECT first_name, username FROM users WHERE user_id = ?', (user_id,))
        user_data = cursor.fetchone()
        if user_data:
            first_name, username = user_data
            return f"{first_name} (@{username})" if username else first_name
        return "کاربر"
    except Exception as e:
        logger.error(f"❌ خطا در get_user_name: {e}")
        return "کاربر"

# هندلر پیام‌های متنی
@bot.message_handler(func=lambda message: True)
def handle_messages(message):
    try:
        chat_id = message.chat.id
        text = message.text
        user_id = message.from_user.id

        if text == '🎮 شروع بازی':
            bot.send_message(chat_id, "🎯 لطفا نوع بازی را انتخاب کنید:", reply_markup=game_selection_menu())
        
        elif text == '🏆 لیدربورد':
            show_leaderboard(chat_id)
        
        elif text == '👤 پروفایل':
            show_profile(chat_id, user_id)
        
        elif text == '❓ راهنما':
            show_help(chat_id)
        
        elif text == '🔙 بازگشت':
            bot.send_message(chat_id, "منوی اصلی:", reply_markup=main_menu())
        
        elif text in ['🧮 چالش ریاضی', '🔤 چالش کلمات', '🧠 چالش حافظه', '📚 چالش اطلاعات عمومی']:
            game_type, game_name = get_game_type(text)
            invite_friend(chat_id, user_id, game_type, game_name)
            
    except Exception as e:
        logger.error(f"❌ خطا در handle_messages: {e}")

# دریافت نوع بازی
def get_game_type(text):
    if text == '🧮 چالش ریاضی':
        return 'math', 'چالش ریاضی'
    elif text == '🔤 چالش کلمات':
        return 'word', 'چالش کلمات'
    elif text == '🧠 چالش حافظه':
        return 'memory', 'چالش حافظه'
    elif text == '📚 چالش اطلاعات عمومی':
        return 'trivia', 'چالش اطلاعات عمومی'
    return 'math', 'چالش ریاضی'

# دعوت دوست
def invite_friend(chat_id, user_id, game_type, game_name):
    try:
        bot_username = (bot.get_me()).username
        encoded_game_name = game_name.replace(' ', '_')
        invite_url = f"https://t.me/{bot_username}?start=invite_{user_id}_{game_type}_{encoded_game_name}"
        
        # ایجاد کیبورد برای دعوت
        keyboard = types.InlineKeyboardMarkup()
        btn_invite = types.InlineKeyboardButton("📩 اشتراک گذاری لینک دعوت", url=f"https://t.me/share/url?url={invite_url}&text=به من در چالش {game_name} ملحق شو!")
        keyboard.add(btn_invite)
        
        message_text = f"""
🔗 برای دعوت دوست به بازی {game_name}:

{invite_url}

یا از دکمه زیر برای اشتراک‌گذاری استفاده کنید:
        """
        
        bot.send_message(chat_id, message_text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"❌ خطا در invite_friend: {e}")
        bot.send_message(chat_id, "⚠️ خطایی در ایجاد لینک دعوت رخ داده است.")

# نمایش پروفایل
def show_profile(chat_id, user_id):
    try:
        cursor.execute('SELECT username, score, games_played, wins FROM users WHERE user_id = ?', (user_id,))
        user_data = cursor.fetchone()
        
        if user_data:
            username, score, games_played, wins = user_data
            win_rate = (wins / games_played * 100) if games_played > 0 else 0
            
            profile_text = f"""
👤 پروفایل کاربری:

🆔 نام کاربری: @{username if username else 'ندارد'}
🏆 امتیاز: {score}
🎮 تعداد بازی‌ها: {games_played}
✅ پیروزی‌ها: {wins}
📊 درصد پیروزی: {win_rate:.1f}%
            """
            
            bot.send_message(chat_id, profile_text)
        else:
            bot.send_message(chat_id, "❌ کاربر یافت نشد!")
            
    except Exception as e:
        logger.error(f"❌ خطا در show_profile: {e}")
        bot.send_message(chat_id, "⚠️ خطایی در نمایش پروفایل رخ داده است.")

# نمایش لیدربورد
def show_leaderboard(chat_id):
    try:
        cursor.execute('''
        SELECT username, score 
        FROM users 
        ORDER BY score DESC 
        LIMIT 10
        ''')
        
        top_players = cursor.fetchall()
        
        if not top_players:
            bot.send_message(chat_id, "🏆 هنوز هیچ بازیکنی در جدول رده‌بندی وجود ندارد!")
            return
        
        leaderboard_text = "🏆 10 بازیکن برتر:\n\n"
        
        for i, (username, score) in enumerate(top_players, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            leaderboard_text += f"{medal} @{username if username else 'ناشناس'} - {score} امتیاز\n"
        
        bot.send_message(chat_id, leaderboard_text)
        
    except Exception as e:
        logger.error(f"❌ خطا در show_leaderboard: {e}")
        bot.send_message(chat_id, "⚠️ خطایی در نمایش لیدربورد رخ داده است.")

# نمایش راهنما
def show_help(chat_id):
    try:
        help_text = """
❓ راهنمای ربات Duo Challenge:

🎮 انواع بازی‌ها:
• 🧮 چالش ریاضی: مسابقه حل مسائل ریاضی
• 🔤 چالش کلمات: مسابقه ساخت کلمات
• 🧠 چالش حافظه: آزمایش حافظه
• 📚 چالش اطلاعات عمومی: سوالات عمومی

👥 روش بازی:
1. نوع بازی را انتخاب کنید
2. لینک دعوت را برای دوست بفرستید
3. پس از پذیرش، بازی شروع می‌شود

🏆 امتیازات شما در جدول رده‌بندی ثبت می‌شود.
        """
        
        bot.send_message(chat_id, help_text)
        
    except Exception as e:
        logger.error(f"❌ خطا در show_help: {e}")

# شروع بازی ریاضی
def start_math_game(game_id, player1_id, player2_id):
    try:
        # تولید سوال ریاضی
        operations = ['+', '-', '*']
        op = random.choice(operations)
        
        if op == '+':
            a, b = random.randint(10, 50), random.randint(10, 50)
            answer = a + b
        elif op == '-':
            a, b = random.randint(50, 100), random.randint(10, 49)
            answer = a - b
        else:  # *
            a, b = random.randint(2, 12), random.randint(2, 12)
            answer = a * b
        
        question = f"🧮 سوال ریاضی:\n\n{a} {op} {b} = ?"
        
        # ذخیره پاسخ صحیح
        cursor.execute('''
        UPDATE active_games 
        SET game_data = ?, status = 'question'
        WHERE game_id = ?
        ''', (json.dumps({'answer': answer, 'question': question}), game_id))
        conn.commit()
        
        # ارسال سوال به بازیکنان
        bot.send_message(player1_id, f"{question}\n\n⏰ 30 ثانیه وقت دارید!")
        bot.send_message(player2_id, f"{question}\n\n⏰ 30 ثانیه وقت دارید!")
        
        logger.info(f"بازی ریاضی شروع شد: {a} {op} {b} = {answer}")
        
    except Exception as e:
        logger.error(f"❌ خطا در start_math_game: {e}")

# شروع پولینگ
def start_polling():
    logger.info("=" * 50)
    logger.info("🚀 DUO CHALLENGE BOT STARTING...")
    logger.info("🤖 Bot Token: " + BOT_TOKEN[:10] + "..." + BOT_TOKEN[-10:])
    logger.info("=" * 50)
    
    while True:
        try:
            logger.info("🔄 شروع پولینگ...")
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except Exception as e:
            logger.error(f"❌ خطا در پولینگ: {e}")
            logger.info("⏳ تلاش مجدد در 15 ثانیه...")
            time.sleep(15)

if __name__ == '__main__':
    start_polling()
