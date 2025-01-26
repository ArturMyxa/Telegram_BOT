import telebot
import random
from telebot import types
import sqlalchemy
from sqlalchemy.orm import sessionmaker
from db_models import create_tables, Word, User, UserWord
from create_db import get_default_words

# Токен для бота
TOKEN = '8195536784:AAFc53C-fbCAgXM3Vbbonxa9ov-fdyOisUA'

# Инициализация бота и базы данных
bot = telebot.TeleBot(TOKEN)
engine = sqlalchemy.create_engine("postgresql://postgres:5555@localhost:5432/tgbot")
Session = sessionmaker(bind=engine)
create_tables(engine)

print("Бот запущен...")

# Словарь для хранения текущих данных о состоянии пользователя
session_data = {}

def get_session():
    """Управление сессиями через контекстный менеджер"""
    return Session()

def user_list():
    """Получить список всех пользователей"""
    with get_session() as session:
        users = session.query(User).all()
        return [user.cid for user in users]

def add_users(user_id):
    """Добавить нового пользователя и слова по умолчанию"""
    with get_session() as session:
        existing_user = session.query(User).filter_by(cid=user_id).first()
        if not existing_user:
            new_user = User(cid=user_id)
            session.add(new_user)
            session.commit()

            # Получаем ID пользователя
            user_id_db = session.query(User.id).filter(User.cid == user_id).first()[0]

            # Получаем предустановленные слова
            default_words = get_default_words()

            # Добавляем слова в таблицу user_word
            user_words = [UserWord(word=word, translate=translate, id_user=user_id_db) for word, translate in default_words]
            session.add_all(user_words)
            session.commit()

def get_words(user_id):
    """Получить все слова пользователя"""
    with get_session() as session:
        return session.query(UserWord.word, UserWord.translate) \
            .join(User, User.id == UserWord.id_user) \
            .filter(User.cid == user_id).all()

def add_words(cid, word, translate):
    """Добавить слово пользователю"""
    with get_session() as session:
        id_user = session.query(User.id).filter(User.cid == cid).first()
        if id_user:
            session.add(UserWord(word=word, translate=translate, id_user=id_user[0]))
            session.commit()

def delete_words(cid, word):
    """Удалить слово пользователя"""
    with get_session() as session:
        id_user = session.query(User.id).filter(User.cid == cid).first()
        if id_user:
            session.query(UserWord).filter_by(id_user=id_user[0], word=word).delete()
            session.commit()

known_users = user_list()
print(f"Добавлено {len(known_users)} пользователей")

welcome_text = '''Привет 👋
Давай попрактикуемся в английском языке. Тренировки можешь проходить в удобном для себя темпе.
Ты можешь добавлять слова, удалять их и тренироваться, выбирая перевод.
Начнём?'''

class Command:
    ADD_WORD = 'Добавить слово ➕'
    DELETE_WORD = 'Удалить слово 🔙'
    NEXT = 'Дальше ⏭'
    BACK = 'Назад'

def create_markup(buttons):
    """Создать клавиатуру"""
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(*buttons)
    return markup

@bot.message_handler(commands=['start', 'cards'])
def create_cards(message):
    """Создаёт карточки для тренировки"""
    cid = message.chat.id

    if cid not in known_users:
        known_users.append(cid)
        add_users(cid)
        bot.send_message(cid, welcome_text)

    user_words = get_words(cid)

    if len(user_words) < 4:
        buttons = [types.KeyboardButton(Command.ADD_WORD)]
        markup = create_markup(buttons)
        bot.send_message(cid, "Недостаточно слов для тренировки. Добавьте больше слов.", reply_markup=markup)
        return

    random_words = random.sample(user_words, 4)
    target_word = random_words[0]

    direction = random.choice(['en_to_ru', 'ru_to_en'])
    if direction == 'en_to_ru':
        question_text = f"Переведи на русский: '{target_word[0]}'"
        correct_translation = target_word[1]
        options = [word[1] for word in random_words]
    else:
        question_text = f"Переведи на английский: '{target_word[1]}'"
        correct_translation = target_word[0]
        options = [word[0] for word in random_words]

    session_data[cid] = {
        'correct_translation': correct_translation.strip().lower()
    }

    buttons = [types.KeyboardButton(option) for option in options]
    random.shuffle(buttons)
    buttons += [
        types.KeyboardButton(Command.NEXT),
        types.KeyboardButton(Command.ADD_WORD),
        types.KeyboardButton(Command.DELETE_WORD)
    ]
    markup = create_markup(buttons)
    bot.send_message(cid, question_text, reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == Command.NEXT)
def handle_next(message):
    """Обрабатывает нажатие кнопки 'Далее'"""
    create_cards(message)

@bot.message_handler(func=lambda message: message.text == Command.ADD_WORD)
def add_word_handler(message):
    """Инициирует процесс добавления нового слова"""
    cid = message.chat.id
    bot.send_message(cid, "Введите слово на английском:")
    session_data[cid] = {"state": "awaiting_english_word"}

@bot.message_handler(func=lambda message: session_data.get(message.chat.id, {}).get("state") == "awaiting_english_word")
def get_english_word(message):
    """Получает английское слово и запрашивает перевод"""
    cid = message.chat.id
    session_data[cid]["english_word"] = message.text.strip()
    session_data[cid]["state"] = "awaiting_russian_translation"
    bot.send_message(cid, "Введите перевод этого слова на русском:")

@bot.message_handler(func=lambda message: session_data.get(message.chat.id, {}).get("state") == "awaiting_russian_translation")
def get_russian_translation(message):
    """Сохраняет перевод слова в базу данных"""
    cid = message.chat.id
    russian_word = message.text.strip()
    english_word = session_data[cid].get("english_word")

    if english_word and russian_word:
        add_words(cid, english_word, russian_word)
        bot.send_message(cid, f"Слово '{english_word}' -> '{russian_word}' добавлено!")
    else:
        bot.send_message(cid, "Ошибка при добавлении слова. Попробуйте ещё раз.")

    session_data.pop(cid, None)
    create_cards(message)

@bot.message_handler(func=lambda message: message.text == Command.DELETE_WORD)
def delete_word_handler(message):
    """Инициирует процесс удаления слова"""
    cid = message.chat.id
    user_words = get_words(cid)

    if not user_words:
        bot.send_message(cid, "У вас пока нет слов для удаления.")
        return

    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    buttons = [types.KeyboardButton(word[0]) for word in user_words]
    buttons.append(types.KeyboardButton(Command.BACK))
    markup.add(*buttons)
    bot.send_message(cid, "Выберите слово для удаления или нажмите 'Назад':", reply_markup=markup)
    session_data[cid] = {"state": "awaiting_word_deletion"}

@bot.message_handler(func=lambda message: session_data.get(message.chat.id, {}).get("state") == "awaiting_word_deletion")
def handle_word_deletion(message):
    """Удаляет выбранное пользователем слово или возвращает назад"""
    cid = message.chat.id
    word_to_delete = message.text.strip()

    if word_to_delete == Command.BACK:
        bot.send_message(cid, "Возвращаемся назад.")
        session_data.pop(cid, None)
        create_cards(message)
        return

    delete_words(cid, word_to_delete)
    bot.send_message(cid, f"Слово '{word_to_delete}' удалено.")
    session_data.pop(cid, None)
    create_cards(message)

@bot.message_handler(func=lambda message: True, content_types=['text'])
def handle_translation_check(message):
    """Проверяет ответ пользователя"""
    cid = message.chat.id
    user_choice = message.text.strip().lower()

    data = session_data.get(cid)
    if not data:
        bot.send_message(cid, "Ошибка: данные текущего слова не найдены.")
        create_cards(message)
        return

    correct_translation = data['correct_translation']

    if user_choice == correct_translation:
        bot.send_message(cid, "✅ Правильно!")
    else:
        bot.send_message(cid, f"❌ Неправильно! Правильный ответ: '{correct_translation.capitalize()}'.")

    create_cards(message)

bot.infinity_polling(skip_pending=True)
