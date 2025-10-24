import telebot
import sqlite3
from config import BOT_TOKEN

bot=telebot.TeleBot(BOT_TOKEN)

conn = sqlite3.connect("data/memes.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS memes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    img_id TEXT NOT NULL,
    text TEXT NOT NULL
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS user_state (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    current_img TEXT NOT NULL
)
""")
conn.commit()
conn.close()

def get_current_state(user_id):
  conn = sqlite3.connect("data/memes.db")
  cursor = conn.cursor()
  cursor.execute("SELECT current_img FROM user_state WHERE user_id=?", (user_id,))
  rows = cursor.fetchall()
  conn.close()

  if not rows:
     return
  else:
     return rows[0][0]
  
def reset_state(user_id):
  conn = sqlite3.connect("data/memes.db")
  cursor = conn.cursor()
  cursor.execute("DELETE FROM user_state WHERE user_id=?", (user_id,))
  conn.commit()
  conn.close()

def set_state(user_id, img):
  conn = sqlite3.connect("data/memes.db")
  cursor = conn.cursor()
  cursor.execute("INSERT INTO user_state (user_id, current_img) VALUES (?, ?)", (user_id, img))
  conn.commit()
  conn.close()

@bot.message_handler(commands=['start'])
def start_message(message):
  bot.send_message(message.chat.id,
                   "Привет!"
                   "\nПрисылай сначала картинку, потом текст на ней" 
                   "\nКаждую отдельную строку на картинке записывай в новой строке" 
                   "\nМежду отдельными блоками текста пропускай пустую строку"
                   "\n"
                   "\nПосмотреть то, что есть в датасете сейчас, можно по команде /view_all"
                   "\nПосмотреть на свой последний отправленный мем можно по команде /view_my_last"
                   "\nУдалить свой последний отправленный мем можно по команде /delete_my_last" \
                   "\nЕсли ошибся - удали и отправь заново"
                   "\n"
                   "\nЕсли случайно отправил не ту картинку, введи команду /reset и начинай заново")


@bot.message_handler(commands=['view_all'])
def view_all_message(message):
  conn = sqlite3.connect("data/memes.db")
  cursor = conn.cursor()
  cursor.execute("SELECT img_id, text FROM memes")
  rows = cursor.fetchall()
  if not rows:
      bot.send_message(message.chat.id, "Пока ничего нет")
  else:
    for r in rows:
        bot.send_photo(message.chat.id, r[0], caption=r[1])
  conn.close()
  
@bot.message_handler(commands=['view_my_last'])
def view_last_message(message):
  user_id = message.from_user.id

  conn = sqlite3.connect("data/memes.db")
  cursor = conn.cursor()
  cursor.execute("SELECT img_id, text FROM memes WHERE user_id=? ORDER BY id DESC LIMIT 1", (user_id,))
  rows = cursor.fetchall()
  if not rows:
      bot.send_message(message.chat.id, "Пока ничего нет")
  else:
    for r in rows:
        bot.send_photo(message.chat.id, r[0], caption=r[1])
  conn.close()

@bot.message_handler(commands=['delete_my_last'])
def delete_last_message(message):
  user_id = message.from_user.id

  conn = sqlite3.connect("data/memes.db")
  cursor = conn.cursor()
  cursor.execute("SELECT id FROM memes WHERE user_id=? ORDER BY id DESC LIMIT 1", (user_id,))
  rows = cursor.fetchall()

  if not rows:
      bot.send_message(message.chat.id, "Пока ничего нет")

  else:
    for r in rows:
        cursor.execute("DELETE FROM memes WHERE id=?", (r[0],))
        conn.commit()
        bot.send_message(message.chat.id, "Успех")
  conn.close()
  
  
@bot.message_handler(commands=['reset'])
def reset_current_img(message):
  user_id = message.from_user.id

  if get_current_state(user_id) is not None:
    reset_state(user_id)
    bot.send_message(message.chat.id,
                   "Готово, давай начнем заново")
  else:
    bot.send_message(message.chat.id,
                   "У тебя и так ничего не отправлено, давай начинать")
  
@bot.message_handler(content_types='text')
def text_message(message):
    user_id = message.from_user.id

    if get_current_state(user_id) is not None:
      conn = sqlite3.connect("data/memes.db")
      cursor = conn.cursor()
      cursor.execute("INSERT INTO memes (user_id, img_id, text) VALUES (?, ?, ?)", (user_id, get_current_state(user_id), message.text))
      conn.commit()
      conn.close()
      reset_state(user_id)
      bot.send_message(message.chat.id,
                  "Успех, давай ещё")
    else:
       bot.send_message(message.chat.id,
                   "Сначала пришли картинку!")
       
       
@bot.message_handler(content_types='photo')
def img_message(message):
    user_id = message.from_user.id
    file_id = message.photo[-1].file_id

    if get_current_state(user_id) is not None:
      bot.send_message(message.chat.id,
                "Сначала подпиши уже присланную картинку")
    else:
      set_state(user_id, file_id)
      bot.send_message(message.chat.id,
                  "Успех, теперь давай текст")
      

bot.infinity_polling()
