# Service layer for Arkham Client interactions 
import pandas as pd
from arkham.arkham_monitor import ArkhamMonitor # Убедиться, что путь импорта соответствует структуре arkham_client
import requests # Для обработки возможных исключений RequestException
from typing import Tuple, List, Dict, Optional, Any, Set # Добавил Any для DataFrame в Python < 3.9 и Set

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

def get_detailed_token_info(monitor: ArkhamMonitor) -> Tuple[Optional[Dict[str, Set[str]]], Optional[str]]:
    """
    Получает детализированную информацию о токенах (символ -> множество ID).
    Возвращает (token_details_map, error_message_or_none).
    """
    if not monitor:
        return None, "Экземпляр ArkhamMonitor не инициализирован."
    try:
        token_map = monitor.get_token_symbol_map()
        # Дополнительно отфильтруем, чтобы ключи соответствовали get_known_token_symbols()
        # Это важно, если get_token_symbol_map может содержать больше символов, чем get_known_token_symbols
        known_symbols = monitor.get_known_token_symbols()
        filtered_token_map = {sym: ids for sym, ids in token_map.items() if sym in known_symbols}
        return filtered_token_map, None
    except Exception as e:
        error_msg = f"Непредвиденная ошибка при получении детальной информации о токенах: {e}"
        print(error_msg)
        return None, error_msg

def get_detailed_address_info(monitor: ArkhamMonitor) -> Tuple[Optional[Dict[str, int]], Optional[str]]:
    """
    Получает детализированную информацию об адресах (имя -> количество связанных ID).
    Возвращает (address_details_map, error_message_or_none).
    """
    if not monitor:
        return None, "Экземпляр ArkhamMonitor не инициализирован."
    try:
        known_names = monitor.get_known_address_names()
        address_info_map = {}
        if hasattr(monitor, 'address_cache') and monitor.address_cache is not None:
            for name in known_names:
                # Предполагаем, что monitor.address_cache.get_identifiers_by_name(name) существует и возвращает set
                try:
                    associated_ids = monitor.address_cache.get_identifiers_by_name(name)
                    address_info_map[name] = len(associated_ids)
                except AttributeError: # Если у address_cache нет такого метода
                    address_info_map[name] = 0 # Или другое значение по умолчанию
                    print(f"Warning: monitor.address_cache.get_identifiers_by_name отсутствует.")
                except Exception as e_inner:
                    print(f"Error getting ID count for address {name}: {e_inner}")
                    address_info_map[name] = 0 # Ошибка при получении, ставим 0
        else:
            # Если нет address_cache, заполняем нулями или другим индикатором
            for name in known_names:
                address_info_map[name] = 0 
            print("Warning: monitor.address_cache отсутствует. Детальная информация по адресам не будет полной.")
            
        return address_info_map, None
    except Exception as e:
        error_msg = f"Непредвиденная ошибка при получении детальной информации об адресах: {e}"
        print(error_msg)
        return None, error_msg

def fetch_transactions(monitor: ArkhamMonitor, filter_params: Dict[str, Any], query_limit: int) -> Tuple[Optional[pd.DataFrame], Optional[str], Optional[Dict[str, Any]]]:
    """
    Получает транзакции на основе заданных фильтров.
    Возвращает (transactions_df, error_message_or_none, api_params_for_debug).
    filter_params может содержать: min_usd, lookback, token_symbols, from_address_names, to_address_names
    """
    api_params_for_debug = None # Инициализируем
    if not monitor:
        return None, "Экземпляр ArkhamMonitor не инициализирован.", api_params_for_debug
    try:
        active_filters = {k: v for k, v in filter_params.items() if v is not None}
        
        monitor.set_filters(
            min_usd=active_filters.get('min_usd'),
            lookback=active_filters.get('lookback'),
            token_symbols=active_filters.get('token_symbols'),
            from_address_names=active_filters.get('from_address_names'),
            to_address_names=active_filters.get('to_address_names')
        )
        # Получаем сформированные параметры API для отладки
        if hasattr(monitor, 'filter') and monitor.filter is not None:
             api_params_for_debug = monitor.filter.get_api_params(limit=query_limit)
             
        transactions_df = monitor.get_transactions(limit=query_limit)
        return transactions_df, None, api_params_for_debug
    except requests.exceptions.RequestException as e:
        error_msg = f"Сетевая ошибка при запросе транзакций Arkham: {e}"
        print(error_msg)
        return None, error_msg, api_params_for_debug
    except Exception as e:
        error_msg = f"Непредвиденная ошибка при запросе транзакций Arkham: {e}"
        print(error_msg)
        return None, error_msg, api_params_for_debug 