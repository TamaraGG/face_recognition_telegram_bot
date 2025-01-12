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

Base = declarative_base()

EXPECTED_DIMENSION = 128  # Размерность эмбеддингов


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


class FaceDatabase:
    def __init__(self, database_url, cache_lifetime=60):
        """
        Инициализация базы данных и системы кэширования.
        :param database_url: URL для подключения к базе данных.
        :param cache_lifetime: время жизни кэша в секундах.
        """
        try:
            self.engine = create_engine(database_url)
            self.Session = sessionmaker(bind=self.engine)
            self._initialize_database()
        except Exception as e:
            raise ConnectionError(f"Не удалось подключиться к базе данных: {str(e)}")

        # Кэш
        self.cache = None
        self.cache_timestamp = None
        self.cache_lifetime = cache_lifetime

    def _initialize_database(self):
        Base.metadata.create_all(self.engine)

    def _refresh_cache(self, force_refresh=False):
        """
        Обновляет кэш с данными о всех людях и их эмбеддингах.
        """
        if force_refresh or not self.cache or (time.time() - self.cache_timestamp > self.cache_lifetime):
            try:
                with self.Session() as session:
                    people = session.query(Person).all()
                    self.cache = {
                        person.id: [embedding.embedding for embedding in person.embeddings]
                        for person in people
                    }
                    self.cache_timestamp = time.time()
            except Exception as e:
                raise Exception(f"Ошибка при обновлении кэша: {str(e)}")

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

                self._refresh_cache(force_refresh=True)  # Обновляем кэш после изменений
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

                if person.embeddings.count() >= 5:
                    self._remove_similar_embeddings(person, embedding, session)

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

                self._refresh_cache(force_refresh=True)  # Обновляем кэш после изменений
        except Exception as e:
            raise Exception(f"Ошибка при добавлении эмбеддинга для человека с ID {person_id}: {str(e)}")

    def get_all_embeddings(self):
        """
        Возвращает все эмбеддинги из базы данных, используя кэш.
        """
        self._refresh_cache()
        return self.cache

    def get_embeddings(self, person_id):
        """
        Возвращает все эмбеддинги для конкретного человека по его ID.
        """
        self._refresh_cache()

        if person_id in self.cache:
            return self.cache[person_id]
        else:
            with self.Session() as session:
                person = session.query(Person).filter_by(id=person_id).first()
                if not person:
                    raise ValueError(f"Человек с ID {person_id} не найден.")
                embeddings = [embedding.embedding for embedding in person.embeddings]
                self.cache[person_id] = embeddings
                return embeddings

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
                    self._refresh_cache(force_refresh=True)
        except Exception as e:
            raise Exception(f"Ошибка при увеличении счётчика появления человека с ID {person_id}: {str(e)}")

    def _remove_similar_embeddings(self, person, new_embedding, session):
        """
        Удаляет наиболее похожий эмбеддинг из базы.
        """
        embeddings = session.query(Embedding).filter_by(person_id=person.id).all()
        if not embeddings:
            raise ValueError(f"Нет эмбеддингов для человека с ID {person.id}")

        distances = [
            np.linalg.norm(np.array(e.embedding) - np.array(new_embedding))
            for e in embeddings
        ]
        min_distance_index = np.argmin(distances)
        session.delete(embeddings[min_distance_index])
        session.commit()

    def calculate_embedding_hash(self, embedding):
        """
        Вычисляет хэш для заданного эмбеддинга.
        """
        return hash(tuple(embedding))
    
    def get_appearance_count(self, person_id):
        """
        Возвращает количество появлений человека по его ID.
        :param person_id: ID человека.
        :return: Количество появлений (appearance_count).
        """
        try:
            with self.Session() as session:
                person = session.query(Person).filter_by(id=person_id).first()
                if not person:
                    raise ValueError(f"Человек с ID {person_id} не найден.")
                return person.appearance_count
        except Exception as e:
            raise Exception(f"Ошибка при получении количества появлений человека с ID {person_id}: {str(e)}")

