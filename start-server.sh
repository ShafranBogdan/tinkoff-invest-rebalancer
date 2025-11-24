#!/bin/bash

# Скрипт для быстрого запуска сервера в production режиме

echo "🚀 Запуск Tinkoff Rebalancer на сервере..."
echo ""

# Проверка что мы в правильной директории
if [ ! -f "app.py" ]; then
    echo "❌ Ошибка: запустите скрипт из директории приложения"
    exit 1
fi

# Получаем имя пользователя и путь
CURRENT_USER=$(whoami)
CURRENT_DIR=$(pwd)

echo "📁 Директория: $CURRENT_DIR"
echo "👤 Пользователь: $CURRENT_USER"
echo ""

# Устанавливаем gunicorn если нет
if [ ! -f "venv/bin/gunicorn" ]; then
    echo "📦 Установка Gunicorn..."
    source venv/bin/activate
    pip install gunicorn
fi

# Создаем systemd сервис
echo "⚙️  Создание systemd сервиса..."

sudo tee /etc/systemd/system/tinkoff-rebalancer.service > /dev/null <<EOF
[Unit]
Description=Tinkoff Investment Rebalancer
After=network.target

[Service]
Type=simple
User=$CURRENT_USER
WorkingDirectory=$CURRENT_DIR
Environment="PATH=$CURRENT_DIR/venv/bin"
Environment="PORT=5001"

ExecStart=$CURRENT_DIR/venv/bin/gunicorn \\
    --workers 2 \\
    --bind 0.0.0.0:5001 \\
    --timeout 120 \\
    --access-logfile $CURRENT_DIR/access.log \\
    --error-logfile $CURRENT_DIR/error.log \\
    app:app

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Перезагружаем systemd
echo "🔄 Перезагрузка systemd..."
sudo systemctl daemon-reload

# Запускаем сервис
echo "▶️  Запуск сервиса..."
sudo systemctl start tinkoff-rebalancer

# Включаем автозапуск
echo "✅ Включение автозапуска..."
sudo systemctl enable tinkoff-rebalancer

# Ждем немного
sleep 2

# Проверяем статус
echo ""
echo "📊 Статус сервиса:"
sudo systemctl status tinkoff-rebalancer --no-pager

echo ""
echo "=========================================="
echo "✅ Сервер запущен!"
echo "=========================================="
echo ""
echo "🌐 Приложение доступно:"
echo "   http://$(hostname -I | awk '{print $1}'):5001"
echo ""
echo "📝 Полезные команды:"
echo "   sudo systemctl status tinkoff-rebalancer    # Статус"
echo "   sudo systemctl restart tinkoff-rebalancer   # Перезапуск"
echo "   sudo systemctl stop tinkoff-rebalancer      # Остановка"
echo "   sudo journalctl -u tinkoff-rebalancer -f    # Логи в реальном времени"
echo "   tail -f $CURRENT_DIR/error.log              # Логи ошибок"
echo ""
echo "💡 Вы можете безопасно выйти из SSH - сервер продолжит работать!"
echo ""

