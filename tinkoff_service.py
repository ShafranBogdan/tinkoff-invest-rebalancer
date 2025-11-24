import os
from decimal import Decimal
from typing import List, Dict, Optional
from tinkoff.invest import Client, InstrumentIdType
from tinkoff.invest.schemas import MoneyValue, Quotation


def quotation_to_decimal(quotation: Quotation) -> Decimal:
    """Преобразование Quotation в Decimal"""
    return Decimal(quotation.units) + Decimal(quotation.nano) / Decimal(1_000_000_000)


def money_value_to_decimal(money: MoneyValue) -> Decimal:
    """Преобразование MoneyValue в Decimal"""
    return Decimal(money.units) + Decimal(money.nano) / Decimal(1_000_000_000)


def get_token() -> str:
    """Получение токена из переменной окружения или файла token.txt"""
    # Сначала пробуем получить из переменной окружения
    token = os.environ.get('TINKOFF_TOKEN')
    
    if token:
        return token
    
    # Если нет в переменной окружения, читаем из файла
    token_file = os.path.join(os.path.dirname(__file__), 'token.txt')
    if os.path.exists(token_file):
        with open(token_file, 'r') as f:
            token = f.read().strip()
            return token
    
    raise ValueError("Токен не найден! Укажите TINKOFF_TOKEN в переменной окружения или создайте файл token.txt")


class TinkoffInvestService:
    """Сервис для работы с Tinkoff Invest API"""
    
    def __init__(self, token: str):
        self.token = token
    
    def get_accounts(self) -> List[Dict]:
        """Получить список счетов"""
        with Client(self.token) as client:
            accounts = client.users.get_accounts()
            return [
                {
                    'id': acc.id,
                    'name': acc.name,
                    'type': acc.type,
                    'status': acc.status
                }
                for acc in accounts.accounts
            ]
    
    def get_portfolio(self, account_id: str) -> Dict:
        """Получить портфель по счету"""
        with Client(self.token) as client:
            portfolio = client.operations.get_portfolio(account_id=account_id)
            
            positions = []
            for position in portfolio.positions:
                # Получаем информацию об инструменте
                instrument = None
                try:
                    if position.figi:
                        instrument = client.instruments.get_instrument_by(
                            id_type=InstrumentIdType.INSTRUMENT_ID_TYPE_FIGI,
                            id=position.figi
                        ).instrument
                except:
                    pass
                
                # Расчет текущей стоимости позиции
                quantity = quotation_to_decimal(position.quantity)
                current_price = money_value_to_decimal(position.current_price) if position.current_price else Decimal(0)
                current_value = quantity * current_price
                
                positions.append({
                    'figi': position.figi,
                    'name': instrument.name if instrument else position.figi,
                    'ticker': instrument.ticker if instrument else '',
                    'type': instrument.instrument_type if instrument else '',
                    'quantity': float(quantity),
                    'current_price': float(current_price),
                    'current_value': float(current_value),
                    'currency': position.current_price.currency if position.current_price else 'RUB'
                })
            
            total_value = money_value_to_decimal(portfolio.total_amount_portfolio)
            
            return {
                'positions': positions,
                'total_value': float(total_value),
                'currency': portfolio.total_amount_portfolio.currency
            }


class RebalanceCalculator:
    """Калькулятор ребалансировки портфеля"""
    
    @staticmethod
    def calculate_rebalance(positions: List[Dict], target_weights: Dict[str, float], mode: str = 'buy_only') -> Dict:
        """
        Расчет ребалансировки портфеля
        
        Args:
            positions: Список позиций с текущими значениями
            target_weights: Целевые доли для каждого актива (figi -> вес в процентах)
            mode: Режим ребалансировки ('buy_only' или 'buy_and_sell')
        
        Returns:
            Dict с информацией о необходимых операциях
        """
        # Проверка что сумма весов = 100%
        total_weight = sum(target_weights.values())
        if abs(total_weight - 100) > 0.01:
            return {'error': f'Сумма долей должна быть 100%, а не {total_weight}%'}
        
        # Фильтруем только выбранные позиции
        selected_positions = {
            pos['figi']: pos 
            for pos in positions 
            if pos['figi'] in target_weights
        }
        
        # Текущая общая стоимость выбранных активов
        current_total = sum(pos['current_value'] for pos in selected_positions.values())
        
        if current_total == 0:
            return {'error': 'Общая стоимость выбранных активов равна 0'}
        
        # Расчет текущих и целевых долей
        current_weights = {
            figi: (pos['current_value'] / current_total * 100) if current_total > 0 else 0
            for figi, pos in selected_positions.items()
        }
        
        # Расчет целевых стоимостей
        operations = []
        
        if mode == 'buy_only':
            # Режим только покупки: не продаем, только докупаем
            # Находим актив с наибольшим отклонением (который должен быть меньше целевого)
            max_scale_factor = 0
            
            for figi, pos in selected_positions.items():
                current_value = pos['current_value']
                target_weight = target_weights[figi] / 100
                
                if target_weight > 0:
                    # Какой должна быть общая сумма, чтобы текущая стоимость составляла целевую долю
                    required_total = current_value / target_weight
                    scale_factor = required_total / current_total
                    max_scale_factor = max(max_scale_factor, scale_factor)
            
            # Новая общая сумма портфеля
            new_total = current_total * max_scale_factor
            additional_investment = new_total - current_total
            
            for figi, pos in selected_positions.items():
                target_value = new_total * (target_weights[figi] / 100)
                current_value = pos['current_value']
                diff_value = target_value - current_value
                
                if abs(diff_value) > 0.01:  # Игнорируем очень маленькие различия
                    diff_quantity = diff_value / pos['current_price'] if pos['current_price'] > 0 else 0
                    
                    operations.append({
                        'figi': figi,
                        'name': pos['name'],
                        'ticker': pos['ticker'],
                        'action': 'buy' if diff_value > 0 else 'skip',
                        'quantity': abs(diff_quantity),
                        'value': abs(diff_value),
                        'current_value': current_value,
                        'target_value': target_value,
                        'current_weight': current_weights[figi],
                        'target_weight': target_weights[figi],
                        'price': pos['current_price']
                    })
            
            return {
                'operations': operations,
                'current_total': current_total,
                'new_total': new_total,
                'additional_investment': additional_investment,
                'mode': mode
            }
        
        else:  # buy_and_sell
            # Режим с продажей: можем и покупать, и продавать
            for figi, pos in selected_positions.items():
                target_value = current_total * (target_weights[figi] / 100)
                current_value = pos['current_value']
                diff_value = target_value - current_value
                
                if abs(diff_value) > 0.01:  # Игнорируем очень маленькие различия
                    diff_quantity = diff_value / pos['current_price'] if pos['current_price'] > 0 else 0
                    
                    operations.append({
                        'figi': figi,
                        'name': pos['name'],
                        'ticker': pos['ticker'],
                        'action': 'buy' if diff_value > 0 else 'sell',
                        'quantity': abs(diff_quantity),
                        'value': abs(diff_value),
                        'current_value': current_value,
                        'target_value': target_value,
                        'current_weight': current_weights[figi],
                        'target_weight': target_weights[figi],
                        'price': pos['current_price']
                    })
            
            return {
                'operations': operations,
                'current_total': current_total,
                'new_total': current_total,
                'additional_investment': 0,
                'mode': mode
            }

