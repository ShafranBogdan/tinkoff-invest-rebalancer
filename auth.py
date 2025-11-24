import os
import sqlite3
import hashlib
from cryptography.fernet import Fernet
from typing import Optional
import secrets


class TokenEncryption:
    """Класс для шифрования и дешифрования токенов"""
    
    def __init__(self):
        # Получаем ключ шифрования из переменной окружения или генерируем новый
        encryption_key = os.environ.get('ENCRYPTION_KEY')
        
        if not encryption_key:
            # Генерируем новый ключ и сохраняем в файл
            key_file = os.path.join(os.path.dirname(__file__), '.encryption_key')
            if os.path.exists(key_file):
                with open(key_file, 'rb') as f:
                    encryption_key = f.read().decode()
            else:
                encryption_key = Fernet.generate_key().decode()
                with open(key_file, 'w') as f:
                    f.write(encryption_key)
                print("⚠️  Создан новый ключ шифрования в файле .encryption_key")
                print("   Сохраните этот файл в безопасном месте!")
        
        self.cipher = Fernet(encryption_key.encode() if isinstance(encryption_key, str) else encryption_key)
    
    def encrypt(self, token: str) -> str:
        """Шифрует токен"""
        return self.cipher.encrypt(token.encode()).decode()
    
    def decrypt(self, encrypted_token: str) -> str:
        """Дешифрует токен"""
        return self.cipher.decrypt(encrypted_token.encode()).decode()


class UserDatabase:
    """Класс для работы с базой данных пользователей"""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.join(os.path.dirname(__file__), 'users.db')
        
        self.db_path = db_path
        self.encryption = TokenEncryption()
        self._init_db()
    
    def _init_db(self):
        """Инициализация базы данных"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT UNIQUE NOT NULL,
                username TEXT,
                encrypted_token TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def create_or_update_user(self, session_id: str, token: str, username: str = None) -> bool:
        """Создает нового пользователя или обновляет существующего"""
        try:
            encrypted_token = self.encryption.encrypt(token)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Проверяем, существует ли пользователь
            cursor.execute('SELECT id FROM users WHERE session_id = ?', (session_id,))
            existing = cursor.fetchone()
            
            if existing:
                # Обновляем существующего пользователя
                cursor.execute('''
                    UPDATE users 
                    SET encrypted_token = ?, username = ?, last_login = CURRENT_TIMESTAMP
                    WHERE session_id = ?
                ''', (encrypted_token, username, session_id))
            else:
                # Создаем нового пользователя
                cursor.execute('''
                    INSERT INTO users (session_id, encrypted_token, username)
                    VALUES (?, ?, ?)
                ''', (session_id, encrypted_token, username))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Ошибка при создании/обновлении пользователя: {e}")
            return False
    
    def get_token(self, session_id: str) -> Optional[str]:
        """Получает расшифрованный токен пользователя"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT encrypted_token FROM users WHERE session_id = ?
            ''', (session_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                encrypted_token = result[0]
                return self.encryption.decrypt(encrypted_token)
            
            return None
        except Exception as e:
            print(f"Ошибка при получении токена: {e}")
            return None
    
    def delete_user(self, session_id: str) -> bool:
        """Удаляет пользователя"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM users WHERE session_id = ?', (session_id,))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Ошибка при удалении пользователя: {e}")
            return False
    
    def user_exists(self, session_id: str) -> bool:
        """Проверяет существование пользователя"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT id FROM users WHERE session_id = ?', (session_id,))
            result = cursor.fetchone()
            
            conn.close()
            return result is not None
        except Exception as e:
            print(f"Ошибка при проверке пользователя: {e}")
            return False


def generate_session_id() -> str:
    """Генерирует уникальный идентификатор сессии"""
    return secrets.token_urlsafe(32)

