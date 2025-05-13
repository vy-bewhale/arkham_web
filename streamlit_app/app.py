# Streamlit application entry point 
import streamlit as st
st.set_page_config(layout="wide", page_title="Arkham Client Explorer")
import pandas as pd
import os
import time # Добавляем импорт time
from dotenv import load_dotenv
import arkham_service # Модуль с логикой Arkham
import telegram_service # НОВЫЙ импорт для Telegram
from typing import List, Dict, Any, Tuple, Optional, Set # Нужен typing для подсказок типов
from streamlit_local_storage import LocalStorage
import json

WHITELIST_KEYS = [
    'lookback_cache_input', 'min_usd_cache_input', 'limit_cache_input',
    'min_usd_query_input', 'lookback_query_input', 'token_symbols_multiselect',
    'from_address_names_multiselect', 'to_address_names_multiselect',
    'limit_query_input',
    'auto_refresh_enabled', 'auto_refresh_interval',
    'cache_initialized_flag', 'known_tokens', 'known_addresses',
    'detailed_token_info', 'detailed_address_info',
    'api_key_loaded', 'error_message', 'api_params_debug',
    'initialized',
    # Новые ключи для Telegram
    'telegram_chat_id',
    'telegram_alerts_enabled',
    'alert_history',
    'telegram_bot_token' # Новый ключ для токена
]

localS = LocalStorage()

APP_MAX_ALERT_ATTEMPTS = 5

def _get_rotation_priority_key(item_data: Dict[str, Any]):
    status = item_data.get('status')
    attempt = item_data.get('attempt', 0)
    
    if status in ["error", "pending"]:
        if attempt >= APP_MAX_ALERT_ATTEMPTS:
            priority_group = 0
        else:
            priority_group = 1
        time_value = item_data.get('last_attempt_time', 0)
    elif status == "success":
        priority_group = 2
        time_value = item_data.get('sent_time', 0)
    else:
        priority_group = 1
        time_value = item_data.get('last_attempt_time', 0)
    return (priority_group, time_value)

def initialize_session_state():
    if 'initialized' not in st.session_state:
        dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env') 
        load_dotenv(dotenv_path=dotenv_path)
        api_key = os.getenv("ARKHAM_API_KEY")
        st.session_state.api_key = api_key
        st.session_state.api_key_loaded = bool(api_key)
        st.session_state.arkham_monitor = None
        st.session_state.error_message = None
        st.session_state.cache_initialized_flag = False
        st.session_state.known_tokens = []
        st.session_state.known_addresses = []
        st.session_state.transactions_df = pd.DataFrame() 
        st.session_state.detailed_token_info = {}
        st.session_state.detailed_address_info = {}
        st.session_state.lookback_cache_input = '7d'
        st.session_state.min_usd_cache_input = 10000.0 
        st.session_state.limit_cache_input = 1000
        st.session_state.min_usd_query_input = 1000000.0 
        st.session_state.lookback_query_input = '7d'
        st.session_state.token_symbols_multiselect = []
        st.session_state.from_address_names_multiselect = []
        st.session_state.to_address_names_multiselect = []
        st.session_state.limit_query_input = 50
        st.session_state.auto_refresh_enabled = False
        st.session_state.auto_refresh_interval = 60
        st.session_state.telegram_chat_id = ''
        st.session_state.telegram_alerts_enabled = False
        st.session_state.alert_history = {}
        st.session_state.telegram_bot_token = ''
        st.session_state.initialized = True

    api_key_present = st.session_state.get('api_key') or os.getenv("ARKHAM_API_KEY")

    if ('arkham_monitor' not in st.session_state or st.session_state.get('arkham_monitor') is None) and api_key_present:
        current_api_key = st.session_state.get('api_key') or os.getenv("ARKHAM_API_KEY")
        try:
            st.session_state.arkham_monitor = arkham_service.create_monitor(current_api_key)
            if st.session_state.arkham_monitor is not None:
                st.session_state.api_key_loaded = True
            else:
                st.session_state.api_key_loaded = False
                st.session_state.error_message = "Не удалось инициализировать Arkham Monitor (create_monitor вернул None)."
        except Exception as e:
            st.session_state.arkham_monitor = None
            st.session_state.api_key_loaded = False
            st.session_state.error_message = f"Ошибка при создании ArkhamMonitor: {e}"
    elif not api_key_present:
        st.session_state.arkham_monitor = None
        st.session_state.api_key_loaded = False
        if not st.session_state.get('error_message'):
             st.session_state.error_message = "ARKHAM_API_KEY не найден."
             

def load_app_settings():
    if "app_state_loaded" not in st.session_state:
        try:
            raw_state = localS.getItem("app_state") # Убран key
            if raw_state:
                state_dict = json.loads(raw_state)
                if state_dict.get("state_version") == 1:
                    for k in WHITELIST_KEYS:
                        if k in state_dict:
                            if k == 'alert_history':
                                try:
                                    loaded_history = state_dict[k]
                                    if isinstance(loaded_history, dict):
                                        st.session_state[k] = loaded_history
                                    else:
                                        print(f"Warning: Loaded alert_history is not a dict, resetting.")
                                        st.session_state[k] = {}
                                except json.JSONDecodeError:
                                    print(f"Warning: Could not decode alert_history from localStorage, resetting.")
                                    st.session_state[k] = {}
                            else:
                                st.session_state[k] = state_dict[k]
            st.session_state.app_state_loaded = True
        except Exception as e:
            print(f"Error loading app settings from localStorage: {e}")
            st.session_state.app_state_loaded = True

def save_app_settings():
    try:
        state_to_save = {k: st.session_state.get(k) for k in WHITELIST_KEYS if k in st.session_state}
        for k in ['detailed_token_info', 'detailed_address_info']:
            if k in state_to_save and isinstance(state_to_save[k], dict):
                for subk, v in state_to_save[k].items():
                    if isinstance(v, set):
                        state_to_save[k][subk] = list(v)
        state_to_save["state_version"] = 1
        if 'alert_history' in state_to_save and not isinstance(state_to_save['alert_history'], dict):
            print("Warning: alert_history is not a dict during save, saving empty dict instead.")
            state_to_save['alert_history'] = {}
        localS.setItem("app_state", json.dumps(state_to_save, ensure_ascii=False), key="app_settings_storage")
    except Exception as e:
        print(f"Error saving app settings to localStorage: {e}")
        pass

def load_arkham_cache(arkham_monitor):
    should_attempt_load = ("arkham_cache_loaded" not in st.session_state or not st.session_state.get("arkham_cache_loaded", False)) and arkham_monitor is not None
    if not should_attempt_load:
        return
    if 'arkham_cache_loaded' in st.session_state:
        del st.session_state['arkham_cache_loaded']
    try:
        raw_cache = localS.getItem("arkham_alert_cache") # Убран key
        if raw_cache:
            cache_dict = json.loads(raw_cache)
            arkham_monitor.load_full_cache_state(cache_dict)
            st.session_state.known_tokens = arkham_monitor.get_known_token_symbols()
            st.session_state.known_addresses = arkham_monitor.get_known_address_names()
            token_cache_data = cache_dict.get('token_cache', {})
            address_cache_data = cache_dict.get('address_cache', {})
            st.session_state.detailed_token_info = token_cache_data.get('symbol_to_ids', {})
            st.session_state.detailed_address_info = address_cache_data.get('name_to_ids', {})
            if st.session_state.detailed_token_info is None: st.session_state.detailed_token_info = {}
            if st.session_state.detailed_address_info is None: st.session_state.detailed_address_info = {}
            if st.session_state.known_tokens or st.session_state.known_addresses:
                st.session_state.cache_initialized_flag = True
            else:
                st.session_state.cache_initialized_flag = False
            st.session_state.arkham_cache_loaded = True
        else:
            st.session_state.cache_initialized_flag = False
            st.session_state.arkham_cache_loaded = False
    except Exception as e: 
        print(f"Error loading arkham cache from localStorage: {e}")
        st.session_state.cache_initialized_flag = False
        st.session_state.arkham_cache_loaded = False

def save_arkham_cache(arkham_monitor):
    if arkham_monitor is not None:
        try:
            cache_to_save = arkham_monitor.get_full_cache_state()
            localS.setItem("arkham_alert_cache", json.dumps(cache_to_save, ensure_ascii=False), key="arkham_cache_storage")
        except Exception as e: 
            print(f"Error saving arkham cache to localStorage: {e}")
            pass

def save_alert_history(history: Dict[str, Dict[str, Any]]):
    limit_q_input = st.session_state.get('limit_query_input', 50) 
    max_history_size = 2 * limit_q_input
    history_copy_for_saving = history.copy()
    if len(history_copy_for_saving) > max_history_size:
        sorted_keys_for_removal = sorted(
            history_copy_for_saving.keys(),
            key=lambda k: _get_rotation_priority_key(history_copy_for_saving[k])
        )
        num_to_remove = len(history_copy_for_saving) - max_history_size
        hashes_to_remove = sorted_keys_for_removal[:num_to_remove]
        for h_key in hashes_to_remove:
            if h_key in history_copy_for_saving:
                 del history_copy_for_saving[h_key]
    try:
        st.session_state.alert_history = history_copy_for_saving 
        save_app_settings() # Это вызовет localS.setItem с key="app_settings_storage"
    except Exception as e:
        print(f"Error in save_alert_history when calling save_app_settings: {e}")
        pass

def handle_populate_cache_button():
    if st.session_state.arkham_monitor:
        lookback = st.session_state.lookback_cache_input
        min_usd = st.session_state.min_usd_cache_input
        limit = st.session_state.limit_cache_input
        with st.spinner("Обновление кеша данных Arkham..."):
            tokens, addresses, error = arkham_service.populate_arkham_cache(
                st.session_state.arkham_monitor, lookback, min_usd, limit
            )
        if error:
            st.session_state.error_message = error
            st.session_state.known_tokens = []
            st.session_state.known_addresses = []
            st.session_state.cache_initialized_flag = False
            st.session_state.detailed_token_info = {}
            st.session_state.detailed_address_info = {}
        else:
            st.session_state.known_tokens = tokens
            st.session_state.known_addresses = addresses
            st.session_state.cache_initialized_flag = True
            st.session_state.error_message = None
            st.success(f"Кеш успешно обновлен. Загружено {len(tokens)} токенов и {len(addresses)} адресов.")
            if st.session_state.arkham_monitor:
                try:
                    full_cache_state = st.session_state.arkham_monitor.get_full_cache_state()
                    st.session_state.detailed_token_info = full_cache_state.get('token_cache', {}).get('symbol_to_ids', {})
                    st.session_state.detailed_address_info = full_cache_state.get('address_cache', {}).get('name_to_ids', {})
                    if st.session_state.detailed_token_info is None: 
                        st.session_state.detailed_token_info = {}
                    if st.session_state.detailed_address_info is None: 
                        st.session_state.detailed_address_info = {}
                except Exception as e:
                    st.warning(f"Ошибка при получении полного состояния кеша из монитора: {e}")
                    st.session_state.detailed_token_info = {} 
                    st.session_state.detailed_address_info = {}
            save_arkham_cache(st.session_state.arkham_monitor)
    else:
        st.session_state.error_message = "Arkham Monitor не инициализирован. Невозможно обновить кеш."

def handle_auto_refresh_toggle():
    pass

def _process_telegram_alerts(transactions_df: pd.DataFrame):
    if not st.session_state.get('telegram_alerts_enabled', False):
        return
    bot_token = st.session_state.get('telegram_bot_token', '')
    chat_id = st.session_state.get('telegram_chat_id', '')
    if not bot_token or not chat_id:
        return
    session_history = st.session_state.get('alert_history', {})
    history_updated = False
    current_time = time.time()
    if 'TxID' not in transactions_df.columns or transactions_df.empty:
        return
    transactions_df_to_process = transactions_df.iloc[::-1]
    current_cycle_alert_history = session_history.copy()
    for index, row in transactions_df_to_process.iterrows():
        tx_hash = row.get('TxID')
        if not tx_hash or pd.isna(tx_hash) or tx_hash == 'N/A':
            continue
        tx_hash_str = str(tx_hash)
        alert_info = current_cycle_alert_history.get(tx_hash_str) 
        should_send = False
        current_attempt = 0
        if alert_info is None:
            should_send = True
            current_attempt = 1
        elif alert_info.get('status') in ["pending", "error"]:
            last_attempt_time = alert_info.get('last_attempt_time', 0)
            attempts_done = alert_info.get('attempt', 0) 
            if attempts_done < APP_MAX_ALERT_ATTEMPTS and (current_time - last_attempt_time >= 60):
                should_send = True
                current_attempt = attempts_done + 1
        if should_send:
            message_html = telegram_service.format_telegram_message(row)
            if message_html:
                success = telegram_service.send_telegram_alert(bot_token, chat_id, message_html)
                new_status = "success" if success else ("error" if current_attempt >= APP_MAX_ALERT_ATTEMPTS else "pending")
                sent_time_val = current_time if success else (alert_info.get('sent_time') if alert_info and 'sent_time' in alert_info else None) 
                current_cycle_alert_history[tx_hash_str] = {
                    'status': new_status,
                    'attempt': current_attempt,
                    'last_attempt_time': current_time,
                    'sent_time': sent_time_val,
                    'original_timestamp_from_data': row.get('time')
                }
                history_updated = True
                time.sleep(0.1)
    if history_updated:
        save_alert_history(current_cycle_alert_history)

def _fetch_and_update_table():
    if not st.session_state.arkham_monitor:
        st.session_state.error_message = "Arkham Monitor не инициализирован. Невозможно выполнить запрос."
        st.session_state.transactions_df = pd.DataFrame()
        st.toast("Ошибка: Монитор Arkham не инициализирован.", icon="🚨")
        return
    if not st.session_state.cache_initialized_flag:
        st.warning("Внимание: Кеш адресов и токенов не был инициализирован или обновлен. Фильтрация по именам и токенам может быть неэффективной.")
    filter_params = {
        'min_usd': st.session_state.min_usd_query_input,
        'lookback': st.session_state.lookback_query_input,
        'token_symbols': st.session_state.token_symbols_multiselect,
        'from_address_names': st.session_state.from_address_names_multiselect,
        'to_address_names': st.session_state.to_address_names_multiselect
    }
    query_limit = st.session_state.limit_query_input
    with st.spinner("Запрос транзакций..."):
        df, error, api_params_debug = arkham_service.fetch_transactions(
            st.session_state.arkham_monitor, filter_params, query_limit
        )
    st.session_state.api_params_debug = api_params_debug 
    if error:
        st.session_state.error_message = error
        st.session_state.transactions_df = pd.DataFrame() 
        st.toast(f"Ошибка при получении транзакций: {error}", icon="🚨")
    else:
        st.session_state.transactions_df = df if df is not None else pd.DataFrame()
        st.session_state.error_message = None 
        if not st.session_state.transactions_df.empty:
            try:
                _process_telegram_alerts(st.session_state.transactions_df)
            except Exception as e:
                st.error(f"Ошибка при обработке Telegram алертов: {e}")
                print(f"Error processing Telegram alerts: {e}")
        if st.session_state.arkham_monitor:
            updated_tokens = st.session_state.arkham_monitor.get_known_token_symbols()
            updated_addresses = st.session_state.arkham_monitor.get_known_address_names()
            if set(st.session_state.get('known_tokens', [])) != set(updated_tokens):
                st.session_state.known_tokens = updated_tokens
            if set(st.session_state.get('known_addresses', [])) != set(updated_addresses):
                st.session_state.known_addresses = updated_addresses
            if st.session_state.arkham_monitor:
                try:
                    full_cache_state = st.session_state.arkham_monitor.get_full_cache_state()
                    st.session_state.detailed_token_info = full_cache_state.get('token_cache', {}).get('symbol_to_ids', {})
                    st.session_state.detailed_address_info = full_cache_state.get('address_cache', {}).get('name_to_ids', {})
                    if st.session_state.detailed_token_info is None: 
                        st.session_state.detailed_token_info = {}
                    if st.session_state.detailed_address_info is None: 
                        st.session_state.detailed_address_info = {}
                except Exception as e:
                    st.warning(f"Ошибка при получении полного состояния кеша из монитора после поиска: {e}")
                    st.session_state.detailed_token_info = {} 
                    st.session_state.detailed_address_info = {}
            save_arkham_cache(st.session_state.arkham_monitor)
            if not st.session_state.cache_initialized_flag and (updated_tokens or updated_addresses):
                 st.session_state.cache_initialized_flag = True
        if st.session_state.transactions_df.empty:
            st.info("Транзакции по заданным фильтрам не найдены.")

def handle_fetch_transactions_button():
    _fetch_and_update_table()

def render_sidebar():
    with st.sidebar.expander("Настройки API и Кеша", expanded=False):
        st.selectbox(
            "Период для кеша", 
            ['24h', '7d', '30d'], 
            key='lookback_cache_input', 
            help="Период для первоначальной загрузки данных в кеш (адреса, токены)."
        )
        st.number_input(
            "Мин. USD для кеша", 
            min_value=0.0,
            step=1000.0, 
            key='min_usd_cache_input',
            format="%.0f",
            help="Минимальная сумма транзакции в USD для наполнения кеша."
        )
        st.number_input(
            "Лимит для кеша", 
            min_value=1,
            max_value=5000, 
            step=100, 
            key='limit_cache_input',
            help="Максимальное количество транзакций для запроса при наполнении кеша."
        )
        st.button("Загрузить/Обновить кеш", on_click=handle_populate_cache_button, key="populate_cache_btn")
    
    with st.sidebar.expander("Фильтры Транзакций", expanded=True):
        cols = st.columns([2, 1])
        cols[0].number_input(
            "Мин. сумма USD", 
            min_value=0.0, 
            step=10000.0, 
            key='min_usd_query_input', 
            format="%.0f",
            help="Минимальная сумма транзакции в USD для основного запроса."
        )
        cols[1].selectbox(
            "Период", 
            ['1h', '6h', '12h', '24h', '3d', '7d', '30d'], 
            key='lookback_query_input', 
            help="Временной период для основного запроса транзакций."
        )
        st.multiselect(
            "Фильтр по токенам", 
            options=st.session_state.get('known_tokens', []),
            key='token_symbols_multiselect',
            help="Выберите символы токенов. Список обновляется после загрузки/обновления кеша."
        )
        st.multiselect(
            "Фильтр по отправителю", 
            options=st.session_state.get('known_addresses', []),
            key='from_address_names_multiselect',
            help="Выберите имена/адреса отправителей. Список обновляется после загрузки/обновления кеша."
        )
        st.multiselect(
            "Фильтр по получателю", 
            options=st.session_state.get('known_addresses', []),
            key='to_address_names_multiselect',
            help="Выберите имена/адреса получателей. Список обновляется после загрузки/обновления кеша."
        )
        st.number_input(
            "Лимит транзакций в результате", 
            min_value=1, 
            max_value=1000, 
            step=10, 
            key='limit_query_input', 
            help="Максимальное кол-во транзакций в итоговом результате."
        )
        st.button("Найти Транзакции", on_click=handle_fetch_transactions_button, key="fetch_transactions_btn")

    with st.sidebar.expander("Настройки алертов Telegram"):
        current_bot_token = st.session_state.get('telegram_bot_token', '')
        current_chat_id = st.session_state.get('telegram_chat_id', '')
        st.text_input(
            "Telegram Bot Token",
            key='telegram_bot_token',
            type="password",
            help="Токен вашего Telegram бота. Его можно получить у @BotFather."
        )
        st.text_input(
            "Telegram Chat ID",
            key='telegram_chat_id',
            help="ID чата или группы в Telegram для отправки алертов.",
        )
        alerts_can_be_enabled = bool(current_bot_token) and bool(current_chat_id)
        st.toggle(
            "Включить алерты Telegram",
            key='telegram_alerts_enabled',
            help="Отправлять уведомления о новых транзакциях в Telegram.",
            disabled=not alerts_can_be_enabled
        )

    with st.sidebar.expander("Автоматическое Обновление"):
        st.toggle(
            "Включить", 
            key='auto_refresh_enabled', 
            help="Автоматически обновлять таблицу транзакций. ВНИМАНИЕ: Приложение будет неактивно во время ожидания интервала."
        )
        st.number_input(
            "Интервал обновления (сек)", 
            min_value=10, 
            step=10, 
            key='auto_refresh_interval', 
            help="Как часто обновлять таблицу (минимум 10 секунд).",
        )

def render_main_content():
    if st.session_state.get('error_message'):
        st.error(st.session_state.error_message)
        st.session_state.error_message = None
    if st.session_state.get('api_key_loaded') and st.session_state.get('arkham_monitor'):
        if not st.session_state.get('cache_initialized_flag'):
            st.info("Данные для кеша (имена адресов, символы токенов) еще не загружены. Используйте кнопку в сайдбаре для загрузки.")
    else:
        st.error("Приложение не может функционировать без API ключа или инициализации монитора.")
        return
    transactions_df_original = st.session_state.get('transactions_df', pd.DataFrame())
    if not transactions_df_original.empty:
        transactions_df_with_status = transactions_df_original.copy()
        alert_history_for_status = st.session_state.get('alert_history', {})
        alerts_enabled = st.session_state.get('telegram_alerts_enabled', False)
        def get_status_icon(tx_id, history, enabled):
            if not tx_id or pd.isna(tx_id) or tx_id == 'N/A':
                return "(нет TxID)"
            if not enabled:
                 return "➖"
            tx_id_str = str(tx_id)
            info = history.get(tx_id_str)
            if info:
                status = info.get('status')
                attempt = info.get('attempt', 0)
                if status == "success":
                    return "✅"
                elif status == "failed":
                    return "⏳" if attempt < APP_MAX_ALERT_ATTEMPTS else "❌"
                elif status == "pending":
                    return "⏳"
                elif status == "error":
                    return "⏳" if attempt < APP_MAX_ALERT_ATTEMPTS else "❌"
                else:
                    return "❓"
            else:
                return ""
        alert_column_name = "Alert" 
        if 'TxID' in transactions_df_with_status.columns:
            transactions_df_with_status[alert_column_name] = transactions_df_with_status['TxID'].apply(
                lambda txid: get_status_icon(txid, alert_history_for_status, alerts_enabled)
            )
        else:
            transactions_df_with_status[alert_column_name] = "(нет TxID)"
        with st.expander("Найденные транзакции", expanded=True):
            cols_in_df = transactions_df_with_status.columns.tolist()
            ordered_cols = []
            if alert_column_name in cols_in_df:
                ordered_cols.append(alert_column_name)
            for col in cols_in_df:
                if col != alert_column_name:
                    ordered_cols.append(col)
            df_display = transactions_df_with_status[ordered_cols]
            st.dataframe(
                df_display, 
                use_container_width=True,
                height=600,
                column_config={
                    "Откуда": st.column_config.TextColumn(width="medium"),
                    "Куда": st.column_config.TextColumn(width="medium"),
                }
            )
    else:
        if st.session_state.get('initialized'):
             st.info("Транзакции по заданным фильтрам не найдены или еще не были запрошены.")

    with st.expander("Информация о кеше (адреса и токены)", expanded=False):
        known_tokens_list = st.session_state.get('known_tokens', [])
        known_addresses_list = st.session_state.get('known_addresses', [])
        cache_initialized = st.session_state.get('cache_initialized_flag', False)
        tab1, tab2, tab3 = st.tabs(["Сводка", "Известные Адреса", "Известные Токены"])
        with tab1:
            if not cache_initialized:
                st.info("Кеш еще не инициализирован. Пожалуйста, загрузите его, используя опцию в сайдбаре.")
            else:
                detailed_address_info = st.session_state.get('detailed_address_info', {})
                total_detailed_addresses_ids = sum(len(ids) for ids in detailed_address_info.values() if isinstance(ids, list))
                detailed_token_info = st.session_state.get('detailed_token_info', {})
                total_detailed_tokens_ids = sum(len(ids) for ids in detailed_token_info.values() if isinstance(ids, list))
                st.write(f"Уникальных имен/адресов в кеше: {len(known_addresses_list)} (связанных ID: {total_detailed_addresses_ids})")
                st.write(f"Уникальных символов токенов в кеше: {len(known_tokens_list)} (связанных ID: {total_detailed_tokens_ids})")
                if not known_addresses_list and not known_tokens_list:
                    st.write("Кеш был инициализирован, но не содержит данных (0 адресов, 0 токенов).")
                ls_size_mb = get_localstorage_size()
                if ls_size_mb >= 0:
                    st.write(f"Размер сохраненных данных в localStorage: {ls_size_mb:.2f} МБ")
                else:
                    st.write("Не удалось определить размер данных в localStorage.")
        with tab2:
            if not cache_initialized:
                st.info("Кеш не инициализирован. Данные об адресах отсутствуют.")
            elif not known_addresses_list:
                st.info("Список известных адресов пуст. Загрузите или обновите кеш из сайдбара.")
            else:
                data_for_addresses_df = []
                detailed_address_info_tab = st.session_state.get('detailed_address_info', {})
                for name in known_addresses_list:
                    ids_list = detailed_address_info_tab.get(name, [])
                    count = len(ids_list) if isinstance(ids_list, list) else 0
                    data_for_addresses_df.append({"Адрес/Имя": name, "Кол-во связанных ID": count})
                df_addresses = pd.DataFrame(data_for_addresses_df)
                st.dataframe(df_addresses, use_container_width=True, height=300)
        with tab3:
            if not cache_initialized:
                st.info("Кеш не инициализирован. Данные о токенах отсутствуют.")
            elif not known_tokens_list:
                st.info("Список известных токенов пуст. Загрузите или обновите кеш из сайдбара.")
            else:
                data_for_tokens_df = []
                detailed_token_info_tab = st.session_state.get('detailed_token_info', {})
                for symbol in known_tokens_list:
                    ids_list = detailed_token_info_tab.get(symbol, [])
                    count_ids = len(ids_list) if isinstance(ids_list, list) else 0
                    data_for_tokens_df.append({"Символ Токена": symbol, "Кол-во связанных ID": count_ids})
                df_tokens = pd.DataFrame(data_for_tokens_df)
                st.dataframe(
                    df_tokens, 
                    use_container_width=True, 
                    height=300,
                    column_config={}
                )

def get_localstorage_size():
    try:
        all_data = localS.getAll() # Убран key
        if not all_data:
            return 0.0
        total_size_bytes = sum(len(json.dumps(key, ensure_ascii=False)) + len(json.dumps(value, ensure_ascii=False)) for key, value in all_data.items())
        return total_size_bytes / (1024 * 1024)
    except Exception as e:
        print(f"Error getting localStorage size: {e}")
        return -1

def main():
    load_app_settings()
    initialize_session_state()
    if st.session_state.get('arkham_monitor') is not None:
        load_arkham_cache(st.session_state.arkham_monitor)
    if st.session_state.get('error_message') and not st.session_state.get('arkham_monitor'):
        st.error(st.session_state.error_message)
        st.session_state.error_message = None 
        st.stop()
    elif not st.session_state.get('api_key_loaded', False) and not st.session_state.get('arkham_monitor'):
        current_error = st.session_state.get('error_message', "Критическая ошибка: ARKHAM_API_KEY не найден или недействителен, или монитор не создан.")
        st.error(current_error)
        st.session_state.error_message = None 
        st.stop()

    render_sidebar()
    render_main_content()

    if st.session_state.get('auto_refresh_enabled', False):
        interval = st.session_state.get('auto_refresh_interval', 60)
        placeholder = st.empty() 
        placeholder.info(f"Автообновление таблицы через {interval} сек...")
        time.sleep(interval) 
        placeholder.empty()
        _fetch_and_update_table()
        st.rerun()
    
    save_app_settings()

if __name__ == "__main__":
    main() 