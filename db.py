import numpy as np
import hashlib
import time
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    Float,
    ForeignKey,
    BIGINT,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from abc import ABC, abstractmethod

Base = declarative_base()

EXPECTED_DIMENSION = 128  # Размерность эмбеддингов

class IDatabase(ABC):
    """
    Интерфейс для работы с базой данных.
    """

    @abstractmethod
    def add_person_with_embedding(self, embedding):
        pass

    @abstractmethod
    def add_embedding(self, person_id, embedding):
        pass

    @abstractmethod
    def get_all_embeddings(self):
        pass

    @abstractmethod
    def get_embeddings(self, person_id):
        pass

    @abstractmethod
    def increment_appearance(self, person_id):
        pass

    @abstractmethod
    def get_appearance_count(self, person_id):
        pass

    @abstractmethod
    def clear_database(self):
        pass

class CacheManager:
    """
    Класс для управления кэшированием.
    """

    def __init__(self, cache_lifetime=60):
        self.cache = None
        self.cache_timestamp = None
        self.cache_lifetime = cache_lifetime

    def is_cache_valid(self):
        """
        Проверяет, является ли кэш актуальным.
        """
        return self.cache and (time.time() - self.cache_timestamp <= self.cache_lifetime)

    def get_cache(self, force_refresh=False):
        """
        Возвращает текущий кэш, если он актуален.
        :param force_refresh: Принудительное обновление кэша.
        """
        if force_refresh or not self.is_cache_valid():
            return None
        return self.cache

    def refresh_cache(self, data):
        """
        Обновляет кэш с новыми данными.
        :param data: данные для сохранения в кэш.
        """
        self.cache = data
        self.cache_timestamp = time.time()

class Person(Base):
    __tablename__ = 'person'
    id = Column(Integer, primary_key=True)
    appearance_count = Column(Integer, default=0)
    embeddings = relationship(
        "Embedding",
        back_populates="person",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

class Embedding(Base):
    __tablename__ = 'embedding'
    id = Column(Integer, primary_key=True)
    person_id = Column(Integer, ForeignKey('person.id', ondelete="CASCADE"))
    embedding = Column(ARRAY(Float), nullable=False)
    embedding_hash = Column(BIGINT, unique=True, nullable=False)
    person = relationship("Person", back_populates="embeddings")

class FaceDatabase(IDatabase):
    def __init__(self, database_url, cache_manager):
        """
        Инициализация базы данных и системы кэширования.
        :param database_url: URL для подключения к базе данных.
        :param cache_manager: объект CacheManager для управления кэшированием.
        """
        try:
            self.engine = create_engine(database_url)
            self.Session = sessionmaker(bind=self.engine)
            self._initialize_database()
        except Exception as e:
            raise ConnectionError(f"Не удалось подключиться к базе данных: {str(e)}")

        self.cache_manager = cache_manager

    def _initialize_database(self):
        Base.metadata.create_all(self.engine)
    
    def calculate_embedding_hash(self, embedding):
        return hash(tuple(embedding))

    def validate_embedding(self, embedding):
        """
        Проверяет корректность эмбеддинга.
        """
        if not isinstance(embedding, (list, np.ndarray)):
            raise ValueError("Эмбеддинг должен быть списком или массивом.")
        if len(embedding) != EXPECTED_DIMENSION:
            raise ValueError(f"Эмбеддинг должен иметь размерность {EXPECTED_DIMENSION}.")

    def add_person_with_embedding(self, embedding):
        """
        Добавляет нового человека вместе с эмбеддингом.
        """
        self.validate_embedding(embedding)

        try:
            with self.Session() as session:
                embedding_as_list = embedding.tolist() if isinstance(embedding, np.ndarray) else embedding
                embedding_hash = self.calculate_embedding_hash(embedding_as_list)

                # Проверяем уникальность хэша в таблице
                existing_embedding = session.query(Embedding).filter_by(embedding_hash=embedding_hash).first()
                if existing_embedding:
                    raise ValueError("Эмбеддинг с таким значением уже существует в базе данных.")

                # Создаем нового человека
                new_person = Person(appearance_count=1)
                session.add(new_person)
                session.flush()

                # Создаем новый эмбеддинг и связываем его с человеком
                new_embedding = Embedding(
                    person_id=new_person.id,
                    embedding=embedding_as_list,
                    embedding_hash=embedding_hash
                )
                session.add(new_embedding)
                session.commit()

                self.cache_manager.refresh_cache(self.get_all_embeddings_from_db())
                return new_person.id
        except Exception as e:
            raise Exception(f"Ошибка при добавлении нового человека с эмбеддингом: {str(e)}")

    def add_embedding(self, person_id, embedding):
        """
        Добавляет эмбеддинг для существующего человека, если его хэш уникален.
        """
        self.validate_embedding(embedding)

        try:
            with self.Session() as session:
                person = session.query(Person).filter_by(id=person_id).first()
                if not person:
                    raise ValueError(f"Человек с ID {person_id} не найден.")

                embedding_as_list = embedding.tolist() if isinstance(embedding, np.ndarray) else embedding
                embedding_hash = self.calculate_embedding_hash(embedding_as_list)

                existing_embedding = session.query(Embedding).filter_by(embedding_hash=embedding_hash).first()
                if existing_embedding:
                    return  # Дубликат не добавляем

                new_embedding = Embedding(
                    person_id=person.id,
                    embedding=embedding_as_list,
                    embedding_hash=embedding_hash
                )
                session.add(new_embedding)
                session.commit()

                self.cache_manager.refresh_cache(self.get_all_embeddings_from_db())
        except Exception as e:
            raise Exception(f"Ошибка при добавлении эмбеддинга для человека с ID {person_id}: {str(e)}")

    def get_all_embeddings_from_db(self):
        """
        Получает все эмбеддинги из базы данных.
        """
        with self.Session() as session:
            people = session.query(Person).all()
            return {
                person.id: [embedding.embedding for embedding in person.embeddings]
                for person in people
            }

    def get_all_embeddings(self):
        """
        Возвращает все эмбеддинги, используя кэш.
        """
        cached_embeddings = self.cache_manager.get_cache()
        if cached_embeddings is None:
            cached_embeddings = self.get_all_embeddings_from_db()
            self.cache_manager.refresh_cache(cached_embeddings)
        return cached_embeddings

    def get_embeddings(self, person_id):
        """
        Возвращает все эмбеддинги для конкретного человека по его ID.
        """
        cached_embeddings = self.get_all_embeddings()
        if person_id in cached_embeddings:
            return cached_embeddings[person_id]
        else:
            raise ValueError(f"Человек с ID {person_id} не найден.")

    def increment_appearance(self, person_id):
        """
        Увеличивает счётчик появления человека.
        """
        try:
            with self.Session() as session:
                person = session.query(Person).filter_by(id=person_id).first()
                if person:
                    person.appearance_count += 1
                    session.commit()
                    self.cache_manager.refresh_cache(self.get_all_embeddings_from_db())
        except Exception as e:
            raise Exception(f"Ошибка при увеличении счётчика появления человека с ID {person_id}: {str(e)}")

    def get_appearance_count(self, person_id):
        try:
            with self.Session() as session:
                person = session.query(Person).filter_by(id=person_id).first()
                if not person:
                    raise ValueError(f"Человек с ID {person_id} не найден.")
                return person.appearance_count
        except Exception as e:
            raise Exception(f"Ошибка при получении количества появлений человека с ID {person_id}: {str(e)}")

    def clear_database(self):
        try:
            with self.Session() as session:
                session.query(Embedding).delete()
                session.query(Person).delete()
                session.commit()

                self.cache_manager.refresh_cache({})
        except Exception as e:
            raise Exception(f"Ошибка при очистке базы данных: {str(e)}")
