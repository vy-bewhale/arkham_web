# Service layer for Arkham Client interactions 
import pandas as pd
from arkham.arkham_monitor import ArkhamMonitor # Убедиться, что путь импорта соответствует структуре arkham_client
import requests # Для обработки возможных исключений RequestException
from typing import Tuple, List, Dict, Optional, Any # Добавил Any для DataFrame в Python < 3.9

def create_monitor(api_key: str) -> Optional[ArkhamMonitor]:
    """Создает и возвращает экземпляр ArkhamMonitor."""
    if not api_key:
        return None
    try:
        monitor = ArkhamMonitor(api_key=api_key)
        return monitor
    except Exception as e: # Широкий перехват на случай ошибок инициализации
        print(f"Error creating ArkhamMonitor: {e}") # Логирование для отладки
        return None

def populate_arkham_cache(monitor: ArkhamMonitor, lookback: str, min_usd: float, limit: int) -> Tuple[List[str], List[str], Optional[str]]:
    """
    Наполняет внутренний кеш ArkhamMonitor (адреса, токены) и возвращает эти списки.
    Возвращает (known_tokens, known_addresses, error_message_or_none).
    """
    if not monitor:
        return [], [], "Экземпляр ArkhamMonitor не инициализирован."
    try:
        monitor.set_filters(min_usd=min_usd, lookback=lookback)
        # initial_df = monitor.get_transactions(limit=limit) # Сам DataFrame здесь не используется напрямую
        monitor.get_transactions(limit=limit) # Вызов для побочного эффекта наполнения кеша
        
        known_tokens = monitor.get_known_token_symbols()
        known_addresses = monitor.get_known_address_names()
        return known_tokens, known_addresses, None
    except requests.exceptions.RequestException as e:
        error_msg = f"Сетевая ошибка при обновлении кеша Arkham: {e}"
        print(error_msg)
        return [], [], error_msg
    except Exception as e:
        error_msg = f"Непредвиденная ошибка при обновлении кеша Arkham: {e}"
        print(error_msg)
        return [], [], error_msg

def fetch_transactions(monitor: ArkhamMonitor, filter_params: Dict[str, Any], query_limit: int) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    Получает транзакции на основе заданных фильтров.
    Возвращает (transactions_df, error_message_or_none).
    filter_params может содержать: min_usd, lookback, token_symbols, from_address_names, to_address_names
    """
    if not monitor:
        return None, "Экземпляр ArkhamMonitor не инициализирован."
    try:
        # Формируем аргументы для set_filters, исключая None и пустые списки, если это необходимо для библиотеки
        # Однако, оригинальная библиотека arkham_client должна сама корректно обрабатывать None/пустые списки.
        # Поэтому передаем как есть, если библиотека это поддерживает.
        active_filters = {k: v for k, v in filter_params.items() if v is not None}
        # Если token_symbols, from_address_names, to_address_names пустые списки, 
        # и библиотека их не должна принимать как "без фильтра", их нужно убрать или передать None.
        # Предполагаем, что библиотека корректно обработает пустые списки как "не применять этот фильтр".
        
        monitor.set_filters(
            min_usd=active_filters.get('min_usd'),
            lookback=active_filters.get('lookback'),
            token_symbols=active_filters.get('token_symbols'),
            from_address_names=active_filters.get('from_address_names'),
            to_address_names=active_filters.get('to_address_names')
        )
        transactions_df = monitor.get_transactions(limit=query_limit)
        return transactions_df, None
    except requests.exceptions.RequestException as e:
        error_msg = f"Сетевая ошибка при запросе транзакций Arkham: {e}"
        print(error_msg)
        return None, error_msg
    except Exception as e:
        error_msg = f"Непредвиденная ошибка при запросе транзакций Arkham: {e}"
        print(error_msg)
        return None, error_msg 