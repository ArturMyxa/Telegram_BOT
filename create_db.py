from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db_models import create_tables, Word


def get_default_words():
    """Возвращает список предустановленных слов"""
    return [
        ('Duck', 'Утка'),
        ('Rooster', 'Петух'),
        ('Cow', 'Корова'),
        ('Horse', 'Лошадь'),
        ('Goat', 'Коза'),
        ('Black', 'Черный'),
        ('Blue', 'Синий'),
        ('White', 'Белый'),
        ('Gray', 'Серый'),
        ('Yellow', 'Желтый'),
        ('apple', 'яблоко'),
        ('book', 'книга'),
        ('cat', 'кот'),
        ('dog', 'собака'),
    ]

def create_db(engine):
    """Создает таблицы и добавляет предустановленные слова"""
    words = get_default_words()
    create_tables(engine)

    # Создаем сессию
    Session = sessionmaker(bind=engine)
    with Session() as session:
        for word, translate in words:
            if not session.query(Word).filter_by(word=word).first():
                session.add(Word(word=word, translate=translate))
        session.commit()

# Инициализация подключения к базе данных
engine = create_engine("postgresql://postgres:5555@localhost:5432/tgbot")

# Создаем таблицы и добавляем предустановленные слова
create_db(engine)
