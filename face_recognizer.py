import numpy as np
import face_recognition
import face_recognition_models
from db import IDatabase

class FaceRecognizer:
    def __init__(self, database: IDatabase, threshold=0.6):
        """
        инициализация класса FaceRecognizer с заданной базой данных и порогом расстояния
        """
        self.database = database
        self.threshold = threshold

    def recognize_and_update(self, image_path):
        """
        распознает лицо на изображении и обновляет базу данных
        """
        embedding = self._extract_embedding_from_image(image_path)
        if embedding is None:
            result = {
                "статус": "ошибка",
                "сообщение": "Не удалось извлечь эмбеддинг из изображения."
            }
        else:
            result = self._recognize_and_update_from_embedding(embedding)
        return self._format_result(result)

    def _extract_embedding_from_image(self, image_path):
        """
        извлекает эмбеддинг лица из изображения
        """
        image = face_recognition.load_image_file(image_path)
        face_encodings = face_recognition.face_encodings(image)
        if len(face_encodings) != 1:
            return None
        return face_encodings[0]

    def _recognize_and_update_from_embedding(self, embedding):
        """
        распознает лицо по эмбеддингу и обновляет базу данных
        """
        all_embeddings = self.database.get_all_embeddings()
        matched_person_ids = set()

        for person_id, embeddings in all_embeddings.items():
            for stored_embedding in embeddings:
                distance = self._calculate_distance(embedding, stored_embedding)
                if distance < self.threshold:
                    matched_person_ids.add(person_id)

        if len(matched_person_ids) == 0:
            new_person_id = self.database.add_person_with_embedding(embedding)
            return {
                "статус": "добавлен",
                "сообщение": f"Новый человек добавлен с ID {new_person_id}.",
                "ID человека": new_person_id,
                "количество появлений": 1,
            }
        elif len(matched_person_ids) == 1:
            matched_person_id = matched_person_ids.pop()
            self.database.add_embedding(matched_person_id, embedding)
            self.database.increment_appearance(matched_person_id)
            appearance_count = self.database.get_appearance_count(matched_person_id)
            return {
                "статус": "обновлён",
                "сообщение": f"Эмбеддинг добавлен для человека с ID {matched_person_id}.",
                "ID человека": matched_person_id,
                "количество появлений": appearance_count,
            }
        else:
            return {
                "статус": "неоднозначно",
                "сообщение": "Не удалось точно определить.",
            }

    def _calculate_distance(self, embedding1, embedding2):
        """
        вычисляет евклидово расстояние между двумя эмбеддингами
        """
        return np.linalg.norm(np.array(embedding1) - np.array(embedding2))

    def _format_result(self, result):
        """
        форматирует результат в строку для вывода
        """
        formatted_result = "\n".join(f"{key}: {value}" for key, value in result.items())
        return formatted_result