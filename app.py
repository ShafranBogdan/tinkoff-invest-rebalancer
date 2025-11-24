from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import os
import secrets
from tinkoff_service import TinkoffInvestService, RebalanceCalculator
from auth import UserDatabase, generate_session_id

app = Flask(__name__)

# Секретный ключ для сессий
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))

# Инициализация базы данных
db = UserDatabase()


def get_user_token():
    """Получает токен текущего пользователя из базы данных"""
    if 'user_id' not in session:
        return None
    return db.get_token(session['user_id'])


@app.route('/')
def index():
    """Главная страница"""
    # Проверяем, есть ли у пользователя токен
    if 'user_id' not in session or not db.user_exists(session['user_id']):
        return redirect(url_for('login'))
    
    token = get_user_token()
    if not token:
        return redirect(url_for('login'))
    
    return render_template('index.html')


@app.route('/login', methods=['GET'])
def login():
    """Страница входа"""
    return render_template('login.html')


@app.route('/api/auth/login', methods=['POST'])
def api_login():
    """API для входа пользователя"""
    try:
        data = request.json
        token = data.get('token', '').strip()
        username = data.get('username', 'Пользователь').strip()
        
        if not token:
            return jsonify({'error': 'Токен не указан'}), 400
        
        # Проверяем валидность токена, пытаясь получить счета
        try:
            service = TinkoffInvestService(token)
            accounts = service.get_accounts()
            
            # Токен валидный, сохраняем пользователя
            if 'user_id' not in session:
                session['user_id'] = generate_session_id()
            
            db.create_or_update_user(session['user_id'], token, username)
            session['username'] = username
            
            return jsonify({
                'success': True,
                'username': username,
                'accounts_count': len(accounts)
            })
        except Exception as e:
            return jsonify({'error': f'Неверный токен: {str(e)}'}), 400
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/auth/logout', methods=['POST'])
def api_logout():
    """API для выхода пользователя"""
    try:
        if 'user_id' in session:
            # Опционально: можно удалить пользователя из БД или просто очистить сессию
            # db.delete_user(session['user_id'])
            session.clear()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/auth/delete', methods=['POST'])
def api_delete_account():
    """API для удаления токена пользователя"""
    try:
        if 'user_id' in session:
            db.delete_user(session['user_id'])
            session.clear()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/settings')
def settings():
    """Страница настроек"""
    if 'user_id' not in session or not db.user_exists(session['user_id']):
        return redirect(url_for('login'))
    
    return render_template('settings.html', username=session.get('username', 'Пользователь'))


@app.route('/api/accounts', methods=['GET'])
def get_accounts():
    """API для получения списка счетов"""
    try:
        token = get_user_token()
        if not token:
            return jsonify({'error': 'Не авторизован'}), 401
        
        service = TinkoffInvestService(token)
        accounts = service.get_accounts()
        return jsonify({'accounts': accounts})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/portfolio/<account_id>', methods=['GET'])
def get_portfolio(account_id):
    """API для получения портфеля по счету"""
    try:
        token = get_user_token()
        if not token:
            return jsonify({'error': 'Не авторизован'}), 401
        
        service = TinkoffInvestService(token)
        portfolio = service.get_portfolio(account_id)
        return jsonify(portfolio)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/rebalance', methods=['POST'])
def calculate_rebalance():
    """API для расчета ребалансировки"""
    try:
        token = get_user_token()
        if not token:
            return jsonify({'error': 'Не авторизован'}), 401
        
        data = request.json
        positions = data.get('positions', [])
        target_weights = data.get('target_weights', {})
        mode = data.get('mode', 'buy_only')
        
        result = RebalanceCalculator.calculate_rebalance(positions, target_weights, mode)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    # Порт можно настроить через переменную окружения PORT
    # По умолчанию 5001 (5000 часто занят AirPlay на macOS)
    port = int(os.environ.get('PORT', 5001))
    print(f"\n🚀 Приложение запускается на http://localhost:{port}")
    print(f"   Откройте этот адрес в браузере\n")
    app.run(debug=True, host='0.0.0.0', port=port)
