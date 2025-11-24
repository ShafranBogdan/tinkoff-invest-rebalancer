#!/bin/bash

echo "🚀 Запуск приложения для ребалансировки портфеля Tinkoff Invest"
echo ""

# Проверка Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 не найден. Установите Python 3.9-3.13."
    exit 1
fi

# Проверка версии Python
PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "✅ Python найден: $(python3 --version)"

# Предупреждение о Python 3.14+
MAJOR=$(python3 -c 'import sys; print(sys.version_info.major)')
MINOR=$(python3 -c 'import sys; print(sys.version_info.minor)')

if [ "$MAJOR" -eq 3 ] && [ "$MINOR" -ge 14 ]; then
    echo ""
    echo "⚠️  ВНИМАНИЕ: Вы используете Python 3.14+, который пока не поддерживается библиотекой tinkoff-investments."
    echo "   Рекомендуется использовать Python 3.11, 3.12 или 3.13."
    echo ""
    read -p "Продолжить все равно? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Проверка виртуального окружения
if [ ! -d "venv" ]; then
    echo "📦 Создание виртуального окружения..."
    python3 -m venv venv
fi

# Активация виртуального окружения
echo "🔧 Активация виртуального окружения..."
source venv/bin/activate

# Установка зависимостей
echo "📥 Установка зависимостей..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

# Проверка токена
if [ ! -f "token.txt" ] && [ -z "$TINKOFF_TOKEN" ]; then
    echo ""
    echo "⚠️  ВНИМАНИЕ: Токен не найден!"
    echo ""
    echo "Создайте файл token.txt с вашим токеном или установите переменную окружения TINKOFF_TOKEN"
    echo ""
    echo "Пример:"
    echo "  echo 'ваш_токен' > token.txt"
    echo "или"
    echo "  export TINKOFF_TOKEN='ваш_токен'"
    echo ""
    read -p "Продолжить запуск? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo ""
echo "✨ Запуск Flask приложения..."
echo "🌐 Приложение будет доступно по адресу: http://localhost:5001"
echo "   (Порт 5001 используется по умолчанию, т.к. 5000 часто занят AirPlay на macOS)"
echo ""
echo "💡 Чтобы использовать другой порт, установите переменную PORT:"
echo "   export PORT=8080 && python3 app.py"
echo ""
echo "Нажмите Ctrl+C для остановки"
echo ""

python3 app.py

