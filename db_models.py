import sqlalchemy as sq
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = 'user'
    id = sq.Column(sq.Integer, primary_key=True)
    cid = sq.Column(sq.BigInteger, unique=True, nullable=False)

    # Связь с таблицей UserWord
    user_words = relationship("UserWord", back_populates="user", lazy="select", overlaps="words")

class UserWord(Base):
    __tablename__ = 'user_word'
    id = sq.Column(sq.Integer, primary_key=True)
    word = sq.Column(sq.String(length=40), nullable=False)
    translate = sq.Column(sq.String(length=40), nullable=False)
    id_user = sq.Column(sq.Integer, sq.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)

    # Связь с User
    user = relationship("User", back_populates="user_words", lazy="joined", overlaps="words")





class Word(Base):
    __tablename__ = 'word'
    id = sq.Column(sq.Integer, primary_key=True)
    word = sq.Column(sq.String(length=40), unique=True)
    translate = sq.Column(sq.String(length=40), unique=True)


def create_tables(engine):
    """Создать таблицы"""
    Base.metadata.drop_all(engine)  # Удаляем старые таблицы для теста
    Base.metadata.create_all(engine)  # Создаем новые таблицы

