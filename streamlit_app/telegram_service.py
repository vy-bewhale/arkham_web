import os
import requests
import html
import time
import re # Добавляем импорт re для регулярных выражений
from typing import Optional, Dict, Any
import pandas as pd
# from dotenv import load_dotenv # Больше не нужно

# УДАЛЕНО: Загрузка переменных окружения на уровне модуля

# УДАЛЕНО: Функция get_telegram_token()

def _escape_html(text: Optional[str]) -> str:
    """Безопасно экранирует HTML-строку."""
    if text is None:
        return ""
    # Убираем потенциальные пробелы по краям перед экранированием
    return html.escape(str(text).strip())

def format_telegram_message(transaction_row: pd.Series) -> Optional[str]:
    """Форматирует данные транзакции в HTML-сообщение для Telegram."""
    try:
        # Извлечение данных
        time_str_raw = transaction_row.get("Время", "N/A")
        network_str_raw = transaction_row.get("Сеть", "N/A")
        from_str_raw = transaction_row.get("Откуда", "N/A")
        to_str_raw = transaction_row.get("Куда", "N/A")
        token_symbol_raw = transaction_row.get("Символ", "N/A")
        usd_amount_raw = transaction_row.get("USD", None) # Получаем как есть, м.б. None или не число
        tx_id_raw = transaction_row.get("TxID", None)

        # Экранирование основных строк
        time_str = _escape_html(time_str_raw)
        network_str = _escape_html(network_str_raw)
        token_symbol_str = _escape_html(token_symbol_raw)
        
        # ---- Определение иконки ----
        message_icon = "🌐" # Иконка по умолчанию
        token_symbol_lower = str(token_symbol_raw).lower() if token_symbol_raw else ""
        if 'usd' in token_symbol_lower:
            message_icon = "💲"
        elif 'eth' in token_symbol_lower:
            message_icon = "💎"
        elif 'btc' in token_symbol_lower or 'bitcoin' in token_symbol_lower:
            message_icon = "💰"
        # ---- Конец определения иконки ----
        
        # Проверка и экранирование TxID
        tx_id_str = None
        if tx_id_raw and not pd.isna(tx_id_raw) and str(tx_id_raw).strip() != 'N/A':
             tx_id_str = _escape_html(str(tx_id_raw)) # Экранируем TxID тоже на всякий случай

        if not tx_id_str:
            print("Warning: Valid TxID is missing, cannot format Telegram message.")
            return None

        # Форматирование USD: просто экранируем исходную строку
        usd_amount_formatted = "N/A"
        if usd_amount_raw is not None and not pd.isna(usd_amount_raw):
            usd_amount_formatted = _escape_html(str(usd_amount_raw))
        
        # Форматирование Откуда/Куда с выделением CEX/DEX
        def highlight_cex_dex(text_raw):
            if not isinstance(text_raw, str):
                return _escape_html(text_raw) # Просто экранируем, если не строка
            
            escaped_text = _escape_html(text_raw)
            
            # Замена CEX/DEX на <b>CEX</b>/<b>DEX</b> без учета регистра, но с границами слова
            # Используем функцию для замены, чтобы сохранить регистр слова CEX/DEX если нужно,
            # но проще сделать их заглавными в теге <b>
            def replace_match(match):
                 word = match.group(0)
                 # return f'<b>{word}</b>' # Сохраняет регистр
                 return f'<b>{word.upper()}</b>' # Делает заглавными
                 
            highlighted_text = re.sub(r'\b(cex|dex)\b', replace_match, escaped_text, flags=re.IGNORECASE)
            return highlighted_text

        from_str_formatted = highlight_cex_dex(from_str_raw)
        to_str_formatted = highlight_cex_dex(to_str_raw)
            
        # Формирование HTML-сообщения
        message_html = (
            f"{message_icon} <b>{usd_amount_formatted}</b> <b>{token_symbol_str}</b> ({network_str})\n"
            f"<b>From:</b> {from_str_formatted}\n"
            f"<b>To:</b> {to_str_formatted}\n"
            f"<i>{time_str}</i>\n"
            f"🔗 <a href=\"https://platform.arkhamintelligence.com/explorer/tx/{tx_id_str}\">View on Arkham</a>"
        )
        # Убираем пустые строки в начале/конце, если они случайно образовались
        return message_html.strip() 
        
    except Exception as e:
        print(f"Error formatting telegram message: {e}")
        # Добавим вывод самой строки для отладки
        print(f"Row data causing error: {transaction_row.to_dict()}")
        return None

def send_telegram_alert(bot_token: str, chat_id: str, message_html: str) -> bool:
    """Отправляет HTML-сообщение в Telegram и возвращает статус успеха."""
    api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': message_html,
        'parse_mode': 'HTML',
        'disable_web_page_preview': True
    }
    try:
        response = requests.post(api_url, data=payload, timeout=10) # Таймаут 10 секунд
        response.raise_for_status() # Проверка на HTTP ошибки (4xx, 5xx)
        response_data = response.json()
        if response_data.get('ok'):
            return True
        else:
            print(f"Telegram API error: {response_data.get('description')}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"Network error sending Telegram alert: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error sending Telegram alert: {e}")
        return False

# УДАЛЕНО: Пример использования, так как get_telegram_token() удалена
# if __name__ == '__main__':
# ... 