#!/bin/bash

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=========================================="
echo "  Tinkoff Rebalancer - Quick Deploy"
echo "=========================================="
echo ""

# Проверка прав root
if [ "$EUID" -eq 0 ]; then 
    echo -e "${RED}Не запускайте этот скрипт от root!${NC}"
    exit 1
fi

# Определение ОС
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
else
    echo -e "${RED}Не удалось определить ОС${NC}"
    exit 1
fi

echo -e "${GREEN}Обнаружена ОС: $OS${NC}"
echo ""

# Функция установки пакетов
install_packages() {
    echo -e "${YELLOW}Установка необходимых пакетов...${NC}"
    
    if [ "$OS" = "ubuntu" ] || [ "$OS" = "debian" ]; then
        sudo apt update
        sudo apt install -y python3 python3-pip python3-venv nginx
    elif [ "$OS" = "centos" ] || [ "$OS" = "rhel" ] || [ "$OS" = "fedora" ]; then
        sudo yum update -y
        sudo yum install -y python3 python3-pip nginx
    else
        echo -e "${RED}Неподдерживаемая ОС${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✓ Пакеты установлены${NC}"
}

# Функция настройки виртуального окружения
setup_venv() {
    echo ""
    echo -e "${YELLOW}Настройка виртуального окружения...${NC}"
    
    if [ -d "venv" ]; then
        echo "Виртуальное окружение уже существует, пропускаем..."
    else
        python3 -m venv venv
    fi
    
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    pip install gunicorn
    
    echo -e "${GREEN}✓ Виртуальное окружение настроено${NC}"
}

# Функция создания systemd сервиса
create_service() {
    echo ""
    echo -e "${YELLOW}Создание systemd сервиса...${NC}"
    
    CURRENT_USER=$(whoami)
    CURRENT_DIR=$(pwd)
    
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
    
    sudo systemctl daemon-reload
    sudo systemctl enable tinkoff-rebalancer
    
    echo -e "${GREEN}✓ Systemd сервис создан${NC}"
}

# Функция настройки Nginx
setup_nginx() {
    echo ""
    read -p "Настроить Nginx reverse proxy? (y/N): " setup_nginx_choice
    
    if [ "$setup_nginx_choice" = "y" ] || [ "$setup_nginx_choice" = "Y" ]; then
        echo -e "${YELLOW}Настройка Nginx...${NC}"
        
        read -p "Введите ваш домен или IP адрес: " server_name
        
        sudo tee /etc/nginx/sites-available/tinkoff-rebalancer > /dev/null <<EOF
server {
    listen 80;
    server_name $server_name;

    access_log /var/log/nginx/tinkoff-rebalancer-access.log;
    error_log /var/log/nginx/tinkoff-rebalancer-error.log;

    client_max_body_size 10M;

    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
EOF
        
        if [ -d "/etc/nginx/sites-enabled" ]; then
            sudo ln -sf /etc/nginx/sites-available/tinkoff-rebalancer /etc/nginx/sites-enabled/
        fi
        
        sudo nginx -t && sudo systemctl restart nginx
        
        echo -e "${GREEN}✓ Nginx настроен${NC}"
        echo -e "${GREEN}Приложение доступно по адресу: http://$server_name${NC}"
    fi
}

# Функция настройки firewall
setup_firewall() {
    echo ""
    read -p "Настроить firewall? (y/N): " setup_fw_choice
    
    if [ "$setup_fw_choice" = "y" ] || [ "$setup_fw_choice" = "Y" ]; then
        echo -e "${YELLOW}Настройка firewall...${NC}"
        
        if command -v ufw &> /dev/null; then
            sudo ufw allow 80/tcp
            sudo ufw allow 443/tcp
            sudo ufw allow 5001/tcp
            echo -e "${GREEN}✓ UFW настроен${NC}"
        elif command -v firewall-cmd &> /dev/null; then
            sudo firewall-cmd --permanent --add-service=http
            sudo firewall-cmd --permanent --add-service=https
            sudo firewall-cmd --permanent --add-port=5001/tcp
            sudo firewall-cmd --reload
            echo -e "${GREEN}✓ FirewallD настроен${NC}"
        else
            echo -e "${YELLOW}Firewall не найден, пропускаем...${NC}"
        fi
    fi
}

# Главная функция
main() {
    # Проверка, что мы в правильной директории
    if [ ! -f "app.py" ] || [ ! -f "requirements.txt" ]; then
        echo -e "${RED}Ошибка: Запустите скрипт из директории приложения!${NC}"
        exit 1
    fi
    
    # Установка пакетов
    read -p "Установить системные пакеты? (y/N): " install_choice
    if [ "$install_choice" = "y" ] || [ "$install_choice" = "Y" ]; then
        install_packages
    fi
    
    # Настройка виртуального окружения
    setup_venv
    
    # Создание сервиса
    read -p "Создать systemd сервис? (y/N): " service_choice
    if [ "$service_choice" = "y" ] || [ "$service_choice" = "Y" ]; then
        create_service
    fi
    
    # Настройка Nginx
    setup_nginx
    
    # Настройка firewall
    setup_firewall
    
    # Установка прав доступа
    echo ""
    echo -e "${YELLOW}Установка прав доступа...${NC}"
    chmod 600 .encryption_key 2>/dev/null
    chmod 600 users.db 2>/dev/null
    chmod 600 .env 2>/dev/null
    echo -e "${GREEN}✓ Права доступа установлены${NC}"
    
    # Запуск сервиса
    echo ""
    read -p "Запустить сервис сейчас? (y/N): " start_choice
    if [ "$start_choice" = "y" ] || [ "$start_choice" = "Y" ]; then
        sudo systemctl start tinkoff-rebalancer
        sleep 2
        sudo systemctl status tinkoff-rebalancer --no-pager
    fi
    
    echo ""
    echo "=========================================="
    echo -e "${GREEN}Установка завершена!${NC}"
    echo "=========================================="
    echo ""
    echo "Полезные команды:"
    echo "  sudo systemctl status tinkoff-rebalancer    # Статус"
    echo "  sudo systemctl restart tinkoff-rebalancer   # Перезапуск"
    echo "  sudo systemctl stop tinkoff-rebalancer      # Остановка"
    echo "  sudo journalctl -u tinkoff-rebalancer -f    # Логи"
    echo ""
    echo "Приложение доступно по адресу: http://$(hostname -I | awk '{print $1}'):5001"
    echo ""
}

# Запуск
main

