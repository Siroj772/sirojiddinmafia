from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from flask import Flask, request

from telegram.ext import Updater, CommandHandler, CallbackContext
from collections import Counter
from fpdf import FPDF
import random
import os

# Bot tokeni
TOKEN = "7525665590:AAEZhghUoF8y1jNPMkigogBGBE05l3orxPo"
SUPER_ADMIN_ID = 6058698891  # Adminning ID
password = "Sirojiddin1221"  # Admin parol

# O'yinchilar, rollar va o'yin holati
app = Flask(__name__)
players = []
roles = {}
player_stats = {}
bonus_balance = {}
admin_list = {}
game_stats = {"games_played": 0, "wins": 0}
game_active = False
role_names = ["Mafiya", "Komissar", "Kartani", "Aholi", "Doktor", "Don", "Qotil", "Kezuvchi", "Ubitsa", "Sotqin", "Omadli"]
role_assignments = {}

updater = Updater(TOKEN, use_context=True)
dispatcher = updater.dispatcher

# Admin parolni tekshirish
def check_password(update, context):
    if update.message.text.lower() == f"/adminpassword {password}":
        user_id = update.message.from_user.id
        bonus_balance[user_id] = bonus_balance.get(user_id, 0) + 10000000
        context.bot.send_message(user_id, "🎉 Sizga 10,000,000 tanga va 10,000,000 almas berildi!")
    else:
        update.message.reply_text("Parol noto'g'ri!")

# Admin tayinlash
def assign_admin(update, context):
    if update.message.from_user.id == SUPER_ADMIN_ID:
        if context.args:
            user_id = int(context.args[0])
            admin_list[user_id] = "admin"
            context.bot.send_message(user_id, "Siz endi admin bo'ldingiz!")
            update.message.reply_text(f"Admin tayinlandi: {user_id}")
        else:
            update.message.reply_text("Admin tayinlash uchun foydalanuvchi ID si kerak.")

# Adminlikdan olish
def remove_admin(update, context):
    if update.message.from_user.id == SUPER_ADMIN_ID:
        if context.args:
            user_id = int(context.args[0])
            if user_id in admin_list:
                del admin_list[user_id]
                context.bot.send_message(user_id, "Siz adminlikdan olinib, odatdagi foydalanuvchiga aylantirildingiz.")
                update.message.reply_text(f"Adminlikdan olinadi: {user_id}")
            else:
                update.message.reply_text("Foydalanuvchi admin emas.")
        else:
            update.message.reply_text("Adminlikdan olish uchun foydalanuvchi ID si kerak.")

# Bonus berish
def give_bonus(update, context):
    if context.args:
        user_id = int(context.args[0])
        bonus = int(context.args[1])
        bonus_balance[user_id] = bonus_balance.get(user_id, 0) + bonus
        context.bot.send_message(user_id, f"🎉 Sizga {bonus} tanga sovrin berildi!")
        update.message.reply_text(f"{user_id} ga {bonus} tanga berildi.")
    else:
        update.message.reply_text("Bonus berish uchun foydalanuvchi ID si va bonus miqdori kerak.")
def send_announce_roles(context):
    all_roles = []
    for pid in roles:
        all_roles += roles[pid]
    counts = Counter(all_roles)

    emoji_map = {
        "advokat": "👨‍💼", "gazabkor": "🧟", "aholi": "👨", "komissar": "🕵",
        "doktor": "👨‍⚕️", "don": "🤵🏻", "daydi": "🧙‍♂", "ubitsa": "🕴️",
        "mafia": "🤵🏼", "qotil": "🔪", "sotqin": "🤓", "afsungar": "🧞‍♂️","o`g`ri":"🦹🏼‍♂️"
    }

    text = "🎭 <b>O‘yindagi rollar:</b>\n"
    for role, count in counts.items():
        emoji = emoji_map.get(role, "🎭")
        suffix = f" - {count}" if count > 1 else ""
        text += f"{emoji} {role.capitalize()}{suffix}\n"
    text += f"\nJami o‘yinchilar: {len(players)}"
# O'yin boshlash
def start_game(update, context):
    global game_started, day_night_counter
    game_started = True
    day_night_counter = 1

    assign_roles()
    send_announce_roles(context)
    context.bot.send_message(chat_id=group_chat_id,
                             text="🌚 🌃 *Tun*\nKo‘chaga faqat jasur va qo‘rqmas odamlar chiqishdi...",
                             parse_mode="Markdown")
    Thread(target=game_loop, args=(context,)).start()


# O'yin to'xtatish
def stop_game(update, context):
    user = update.effective_user
    member = bot.get_chat_member(update.effective_chat.id, user.id)
    if member.status not in ["administrator", "creator"]:
        return
    global game_started, players, roles, lynch_votes
    game_started = False
    players.clear()
    roles.clear()
    lynch_votes.clear()
    update.message.reply_text("🛑 O‘yin to‘xtatildi.")

# O'yinchilarni ro'yxatga olish
def add_player(update, context):
    if game_active and update.message.from_user.id not in players:
        players.append(update.message.from_user.id)
        update.message.reply_text("Siz o'yinga qo'shildingiz!")
    else:
        update.message.reply_text("O'yin boshlanmagan yoki siz allaqachon o'yinda ishtirok etyapsiz.")

# O'yinchilar ro'yxatini ko'rsatish
def game_status(update, context):
    if players:
        player_names = [f"{bot.get_chat(player_id).first_name}" for player_id in players]
        update.message.reply_text(f"O'yindagi o'yinchilar: {', '.join(player_names)}")
    else:
        update.message.reply_text("Hozirda o'yinda hech kim yo'q.")

# Rollarni tayinlash
def assign_roles(update, context):
    if update.message.from_user.id == SUPER_ADMIN_ID:
        random.shuffle(role_names)
        for i, player_id in enumerate(players):
            if i < len(role_names):
                roles[player_id] = role_names[i]
                context.bot.send_message(player_id, f"Sizga {role_names[i]} roli tayinlandi!")
        update.message.reply_text("Rollar tasodifiy tayinlandi.")

# O'yin statistikasini yaratish va yuborish
def generate_game_stats_pdf():
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="O'yin Statistikalari: Eng Ko'p O'ynaganlar, Eng Boylar va Eng Ko'p Yutganlar", ln=True, align="C")
    pdf.ln(10)
    pdf.cell(200, 10, txt="Eng Ko'p O'ynaganlar:", ln=True)
    for player_id, stats in sorted(player_stats.items(), key=lambda item: item[1]['games'], reverse=True):
        player_name = bot.get_chat(player_id).first_name
        pdf.cell(200, 10, txt=f"{player_name}: {stats['games']} o'yinlar", ln=True)
    pdf.ln(10)
    pdf.cell(200, 10, txt="Eng Boylar (Tangalar):", ln=True)
    for player_id, balance in sorted(bonus_balance.items(), key=lambda item: item[1], reverse=True):
        player_name = bot.get_chat(player_id).first_name
        pdf.cell(200, 10, txt=f"{player_name}: {balance} tanga", ln=True)
    pdf.ln(10)
    pdf.cell(200, 10, txt="Eng Ko'p Yutganlar:", ln=True)
    for player_id, stats in sorted(player_stats.items(), key=lambda item: item[1]['wins'], reverse=True):
        player_name = bot.get_chat(player_id).first_name
        pdf.cell(200, 10, txt=f"{player_name}: {stats['wins']} yutish", ln=True)
    file_path = "/mnt/data/game_stats.pdf"
    pdf.output(file_path)
    return file_path

# O'yin statistikasini yuborish
def send_game_stats(update, context):
    if update.message.from_user.id == SUPER_ADMIN_ID:
        file_path = generate_game_stats_pdf()
        context.bot.send_document(chat_id=SUPER_ADMIN_ID, document=open(file_path, 'rb'))
    else:
        update.message.reply_text("Sizda bu komanda uchun ruxsat yo'q.")
def send_komissar_actions(context):
    for kom_id in [pid for pid, rlist in roles.items() if "komissar" in rlist]:
        buttons = [
            [InlineKeyboardButton("🔍 Tekshirish", callback_data="kom_check")],
            [InlineKeyboardButton("🔫 O‘ldirish", callback_data="kom_kill")]
        ]
        bot.send_message(chat_id=kom_id, text="🕵 Komissar, nima qilmoqchisiz?", reply_markup=InlineKeyboardMarkup(buttons))

def komissar_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id

    if query.data.startswith("kom_"):
        action = query.data.split("_")[1]
        buttons = []
        for pid in players:
            if pid != user_id:
                try:
                    u = bot.get_chat(pid)
                    buttons.append([InlineKeyboardButton(u.first_name, callback_data=f"komfinal_{action}_{pid}")])
                except: continue
        query.message.reply_text(f"👤 Kimni {action} qilmoqchisiz?", reply_markup=InlineKeyboardMarkup(buttons))

    elif query.data.startswith("komfinal_"):
        _, action, pid = query.data.split("_")
        pid = int(pid)
        user = bot.get_chat(pid)
        if action == "check":
            role_names = ', '.join(roles.get(pid, ["aniqlanmadi"]))
            context.bot.send_message(chat_id=group_chat_id, text=f"🔎 Komissar {user.first_name} ni tekshirdi. Roli: {role_names}")
        elif action == "kill":
            context.bot.send_message(chat_id=group_chat_id, text=f"☠️ Komissar tomonidan {user.first_name} o‘ldirildi!")
        query.answer("✅ Amal bajarildi.")
def send_mafia_targets(context):
    mafia_ids = [pid for pid, rlist in roles.items() if "mafia" in rlist or "don" in rlist]
    for mafia_id in mafia_ids:
        buttons = []
        for pid in players:
            if pid != mafia_id:
                try:
                    user = bot.get_chat(pid)
                    buttons.append([InlineKeyboardButton(user.first_name, callback_data=f"kill_{pid}")])
                except: continue
        if buttons:
            bot.send_message(chat_id=mafia_id, text="🎯 Kimni o‘ldirasiz? (Mafia)", reply_markup=InlineKeyboardMarkup(buttons))

def mafia_kill_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    if query.data.startswith("kill_"):
        pid = int(query.data.split("_")[1])
        user = bot.get_chat(pid)

        # Faqat mafiya a’zolariga xabar yuborish
        mafia_ids = [p for p, r in roles.items() if "mafia" in r or "don" in r]
        for mid in mafia_ids:
            try:
                context.bot.send_message(chat_id=mid, text=f"☠️ Mafia {user.first_name} ni o‘ldirdi!")
            except:
                continue

        query.answer("✅ Tanlandi.")

def send_ubitsa_targets(context):
    for uid in [pid for pid, rlist in roles.items() if "ubitsa" in rlist]:
        buttons = []
        for pid in players:
            if pid != uid:
                try:
                    user = bot.get_chat(pid)
                    buttons.append([InlineKeyboardButton(user.first_name, callback_data=f"ubitsa_{pid}")])
                except: continue
        if buttons:
            bot.send_message(chat_id=uid, text="🔪 Kimni o‘ldirasiz? (Ubitsa)", reply_markup=InlineKeyboardMarkup(buttons))

def ubitsa_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    if query.data.startswith("ubitsa_"):
        pid = int(query.data.split("_")[1])
        user = bot.get_chat(pid)
        context.bot.send_message(chat_id=group_chat_id, text=f"🩸 Ubitsa {user.first_name} ni o‘ldirdi!")
        query.answer("✅ Amal bajarildi.")
def send_doctor_targets(context):
    for pid in players:
        if "doktor" in roles.get(pid, []):
            buttons = []
            for uid in players:
                try:
                    user = bot.get_chat(uid)
                    buttons.append([InlineKeyboardButton(user.first_name, callback_data=f"heal_{uid}")])
                except: continue
            bot.send_message(chat_id=pid, text="🩺 Kimni davolaysiz?", reply_markup=InlineKeyboardMarkup(buttons))
    if attacker:
        bot.send_message(chat_id=healer_id, text=f"🔔 Siz {healed_user.first_name} ni davoladingiz. Unga {attacker} tashrif buyurgan edi.")
    else:
        bot.send_message(chat_id=healer_id, text=f"🔔 Siz {healed_user.first_name} ni davoladingiz. Unga hech kim kelmadi.")

    query.answer("✅ Davolandi.")
    attack_targets.pop(healed_id, None)

def doctor_heal_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    if query.data.startswith("heal_"):
        healed_id = int(query.data.split("_")[1])
        user = bot.get_chat(healed_id)
        context.bot.send_message(chat_id=group_chat_id, text=f"🩺 Doktor {user.first_name} ni davoladi!")
        query.answer("✅ Davolandi.")
def send_advokat_targets(context):
    for pid in players:
        if "advokat" in roles.get(pid, []):
            buttons = []
            for uid in players:
                try:
                    user = bot.get_chat(uid)
                    buttons.append([InlineKeyboardButton(user.first_name, callback_data=f"advok_{uid}")])
                except: continue
            bot.send_message(chat_id=pid, text="👨‍💼 Kimni himoya qilasiz?", reply_markup=InlineKeyboardMarkup(buttons))

def advokat_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    if query.data.startswith("advok_"):
        target_id = int(query.data.split("_")[1])
        user = bot.get_chat(target_id)
        context.bot.send_message(chat_id=group_chat_id, text=f"👨‍💼 Advokat {user.first_name} ni himoya qildi!")
        query.answer("✅ Himoya qilingan.")
def send_daydi_targets(context):
    for pid in players:
        if "daydi" in roles.get(pid, []):
            buttons = []
            for uid in players:
                try:
                    user = bot.get_chat(uid)
                    buttons.append([InlineKeyboardButton(user.first_name, callback_data=f"daydi_{uid}")])
                except: continue
            bot.send_message(chat_id=pid, text="🧙‍♂ Kimga borasiz? (guvoh bo‘lish)", reply_markup=InlineKeyboardMarkup(buttons))

def daydi_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    if query.data.startswith("daydi_"):
        target_id = int(query.data.split("_")[1])
        user = bot.get_chat(target_id)
        context.bot.send_message(chat_id=group_chat_id, text=f"🧙‍♂ Daydi {user.first_name} ga bordi, guvoh bo‘ldi!")
        query.answer("✅ Bordingiz.")
def send_kezuvchi_targets(context):
    for pid in players:
        if "kezuvchi" in roles.get(pid, []):
            buttons = []
            for uid in players:
                try:
                    user = bot.get_chat(uid)
                    buttons.append([InlineKeyboardButton(user.first_name, callback_data=f"kez_{uid}")])
                except: continue
            bot.send_message(chat_id=pid, text="💃 Kim bilan birga bo‘lasiz?", reply_markup=InlineKeyboardMarkup(buttons))

def kezuvchi_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    if query.data.startswith("kez_"):
        target_id = int(query.data.split("_")[1])
        user = bot.get_chat(target_id)
        context.bot.send_message(chat_id=group_chat_id, text=f"💃 Kezuvchi {user.first_name} bilan kechani o‘tkazdi!")
        query.answer("✅ Tanlandi.")
def send_lynch_buttons(context):
    for voter_id in players:
        buttons = []
        for target_id in players:
            if target_id != voter_id:
                try:
                    user = bot.get_chat(target_id)
                    buttons.append([InlineKeyboardButton(user.first_name, callback_data=f"lynch_{voter_id}_{target_id}")])
                except: continue
        try:
            bot.send_message(chat_id=voter_id, text="🗳 Kimni osamiz?", reply_markup=InlineKeyboardMarkup(buttons))
        except: continue
def lynch_vote_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data.split("_")
    voter = int(data[1])
    target = int(data[2])

    lynch_votes[voter] = target
    target_user = bot.get_chat(target)
    query.answer("✅ Ovoz berildi.")
    query.message.reply_text(f"🗳 Siz {target_user.first_name} ni osish uchun tanladingiz.")
def resolve_lynch_votes(context):
    if not lynch_votes:
        context.bot.send_message(chat_id=group_chat_id, text="⚖️ Hech kimga ovoz berilmadi.")
        return

    vote_count = Counter(lynch_votes.values())
    most_voted = vote_count.most_common(1)[0][0]
    voted_user = bot.get_chat(most_voted)
    context.bot.send_message(chat_id=group_chat_id, text=f"☠️ {voted_user.first_name} eng ko‘p ovoz oldi va osildi!")
def show_alive_players_and_roles():
    alive_names = []
    for i, pid in enumerate(players, 1):
        try:
            user = bot.get_chat(pid)
            alive_names.append(f"{i}. {user.first_name}")
        except:
            alive_names.append(f"{i}. ID: {pid}")

    bot.send_message(chat_id=group_chat_id, text="📋 Tirik o‘yinchilar:\n" + "\n".join(alive_names))
    send_announce_roles(bot)
# === Webhook va Flask app ===
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    print("Webhook kelib tushdi:", data)
    return "OK", 200


if __name__ == "__main__":
    app.run(debug=True)

@app.route("/")
def home():
    return "Mafia Bot Ishlamoqda ✅"

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

# Handlerlar qo'shish
dispatcher.add_handler(CommandHandler("adminpassword", check_password))  # Admin parolni tekshirish
dispatcher.add_handler(CommandHandler("assignadmin", assign_admin))  # Admin tayinlash
dispatcher.add_handler(CommandHandler("removeadmin", remove_admin))  # Adminlikdan olish
dispatcher.add_handler(CommandHandler("give", give_bonus))  # Bonus berish (hamma ishlatishi mumkin)
dispatcher.add_handler(CommandHandler("start", start_game))  # O'yinni boshlash
dispatcher.add_handler(CommandHandler("stop", stop_game))  # O'yinni to'xtatish
dispatcher.add_handler(CommandHandler("addplayer", add_player))  # O'yinchilarni qo'shish
dispatcher.add_handler(CommandHandler("status", game_status))  # O'yin holatini ko'rsatish
dispatcher.add_handler(CommandHandler("assignroles", assign_roles))  # Rollarni tayinlash
dispatcher.add_handler(CommandHandler("sendstats", send_game_stats))  # O'yin statistikasi yuborish

dispatcher.add_handler(CallbackQueryHandler(button_handler, pattern="^(join_game|start_game_btn)$"))
dispatcher.add_handler(CallbackQueryHandler(mafia_kill_callback, pattern="^kill_"))
dispatcher.add_handler(CallbackQueryHandler(doctor_heal_callback, pattern="^heal_"))
dispatcher.add_handler(CallbackQueryHandler(komissar_callback, pattern="^kom_"))
dispatcher.add_handler(CallbackQueryHandler(komissar_callback, pattern="^komfinal_"))
dispatcher.add_handler(CallbackQueryHandler(claim_callback, pattern="^claim_"))
dispatcher.add_handler(CallbackQueryHandler(lynch_vote_callback, pattern="^lynch_"))
updater.start_polling()
updater.idle()
