import os
import telebot
from flask import Flask, request
from moviepy.editor import VideoFileClip

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # https://your-app.onrender.com

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

user_data = {}

# ===== START =====
@bot.message_handler(commands=['start'])
def start(msg):
    bot.reply_to(msg, "📥 Video ya video note bhejo.")

# ===== VIDEO =====
@bot.message_handler(content_types=['video'])
def handle_video(msg):
    user_id = msg.chat.id

    file_info = bot.get_file(msg.video.file_id)
    downloaded_file = bot.download_file(file_info.file_path)

    input_path = f"{user_id}_input.mp4"
    output_path = f"{user_id}_output.mp4"

    with open(input_path, 'wb') as f:
        f.write(downloaded_file)

    clip = VideoFileClip(input_path)
    size = min(clip.w, clip.h)

    clip = clip.crop(
        x_center=clip.w/2,
        y_center=clip.h/2,
        width=size,
        height=size
    ).resize((360, 360))

    clip.write_videofile(output_path, codec='libx264')

    user_data[user_id] = {
        "type": "video",
        "path": output_path
    }

    msg2 = bot.send_message(user_id, "✏️ Caption bhejo:")
    bot.register_next_step_handler(msg2, send_final)

# ===== VIDEO NOTE =====
@bot.message_handler(content_types=['video_note'])
def handle_video_note(msg):
    user_id = msg.chat.id

    user_data[user_id] = {
        "type": "video_note",
        "file_id": msg.video_note.file_id
    }

    msg2 = bot.send_message(user_id, "✏️ Caption bhejo:")
    bot.register_next_step_handler(msg2, send_final)

# ===== FINAL =====
def send_final(msg):
    user_id = msg.chat.id
    caption = msg.text

    data = user_data.get(user_id)

    if not data:
        bot.send_message(user_id, "❌ Session expired.")
        return

    if data["type"] == "video":
        with open(data["path"], 'rb') as vid:
            bot.send_video_note(user_id, vid, length=360)

        os.remove(data["path"])
        os.remove(f"{user_id}_input.mp4")

    elif data["type"] == "video_note":
        bot.send_video_note(user_id, data["file_id"])

    bot.send_message(user_id, f"📝 Caption:\n{caption}")

    user_data.pop(user_id, None)

# ===== WEBHOOK ROUTES =====
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    json_str = request.get_data().decode("UTF-8")
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "OK", 200

@app.route("/")
def home():
    return "Bot is running!"

# ===== SET WEBHOOK =====
bot.remove_webhook()
bot.set_webhook(url=f"{WEBHOOK_URL}/{BOT_TOKEN}")

# ===== RUN =====
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
