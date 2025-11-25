#!/usr/bin/env python3
"""
Скрипт для диагностики проблем с аутентификацией
"""

import os
import sys
import sqlite3

def check_files():
    """Проверяет наличие необходимых файлов"""
    print("🔍 Проверка файлов...")
    
    files = {
        '.secret_key': 'SECRET_KEY для Flask сессий',
        '.encryption_key': 'Ключ шифрования токенов',
        'users.db': 'База данных пользователей'
    }
    
    all_ok = True
    for file, description in files.items():
        if os.path.exists(file):
            size = os.path.getsize(file)
            print(f"  ✅ {file} ({description}) - {size} байт")
        else:
            print(f"  ❌ {file} ({description}) - НЕ НАЙДЕН")
            all_ok = False
    
    return all_ok

def check_database():
    """Проверяет базу данных"""
    print("\n🗄️  Проверка базы данных...")
    
    if not os.path.exists('users.db'):
        print("  ❌ База данных не найдена")
        return False
    
    try:
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        
        # Проверяем структуру таблицы
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        if not cursor.fetchone():
            print("  ❌ Таблица 'users' не существует")
            return False
        
        print("  ✅ Таблица 'users' существует")
        
        # Считаем пользователей
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        print(f"  📊 Пользователей в БД: {count}")
        
        # Показываем последних пользователей (без токенов)
        if count > 0:
            cursor.execute("SELECT username, created_at, last_login FROM users ORDER BY last_login DESC LIMIT 5")
            print("\n  Последние пользователи:")
            for row in cursor.fetchall():
                username, created, last_login = row
                print(f"    - {username or 'Без имени'} (создан: {created}, вход: {last_login})")
        
        conn.close()
        return True
    
    except Exception as e:
        print(f"  ❌ Ошибка при проверке БД: {e}")
        return False

def check_environment():
    """Проверяет переменные окружения"""
    print("\n🌍 Проверка переменных окружения...")
    
    env_vars = ['SECRET_KEY', 'ENCRYPTION_KEY', 'PORT', 'TINKOFF_TOKEN']
    
    for var in env_vars:
        value = os.environ.get(var)
        if value:
            masked = value[:8] + '...' if len(value) > 8 else '***'
            print(f"  ✅ {var} = {masked}")
        else:
            print(f"  ⚠️  {var} не установлен (будет использован из файла или по умолчанию)")

def check_imports():
    """Проверяет импорты"""
    print("\n📦 Проверка зависимостей...")
    
    required = [
        ('flask', 'Flask'),
        ('tinkoff.invest', 'Tinkoff Invest SDK'),
        ('cryptography', 'Cryptography'),
    ]
    
    all_ok = True
    for module, name in required:
        try:
            __import__(module)
            print(f"  ✅ {name}")
        except ImportError:
            print(f"  ❌ {name} не установлен")
            all_ok = False
    
    return all_ok

def test_encryption():
    """Тестирует шифрование"""
    print("\n🔐 Проверка шифрования...")
    
    try:
        from auth import TokenEncryption
        
        encryptor = TokenEncryption()
        test_data = "test_token_12345"
        
        encrypted = encryptor.encrypt(test_data)
        decrypted = encryptor.decrypt(encrypted)
        
        if decrypted == test_data:
            print("  ✅ Шифрование работает корректно")
            return True
        else:
            print("  ❌ Ошибка шифрования: данные не совпадают")
            return False
    
    except Exception as e:
        print(f"  ❌ Ошибка при тестировании шифрования: {e}")
        return False

def main():
    print("=" * 60)
    print("  Диагностика Tinkoff Investment Rebalancer")
    print("=" * 60)
    print()
    
    results = []
    
    results.append(("Файлы", check_files()))
    results.append(("База данных", check_database()))
    results.append(("Зависимости", check_imports()))
    results.append(("Шифрование", test_encryption()))
    
    check_environment()
    
    print("\n" + "=" * 60)
    print("  Результаты диагностики:")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results:
        status = "✅" if passed else "❌"
        print(f"  {status} {name}")
        if not passed:
            all_passed = False
    
    print()
    
    if all_passed:
        print("✅ Все проверки пройдены успешно!")
        print("\nЕсли проблема сохраняется:")
        print("  1. Перезапустите приложение")
        print("  2. Очистите cookies в браузере")
        print("  3. Попробуйте войти заново")
    else:
        print("❌ Обнаружены проблемы!")
        print("\nРешения:")
        print("  1. Установите зависимости: pip install -r requirements.txt")
        print("  2. Проверьте права доступа к файлам: chmod 600 .secret_key .encryption_key users.db")
        print("  3. Пересоздайте базу данных: rm users.db && python app.py")
    
    print()
    return 0 if all_passed else 1

if __name__ == '__main__':
    sys.exit(main())

