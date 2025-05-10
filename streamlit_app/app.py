# Streamlit application entry point 
import streamlit as st
st.set_page_config(layout="wide", page_title="Arkham Client Explorer")
import pandas as pd
import os
import time # Добавляем импорт time
from dotenv import load_dotenv
import arkham_service # Модуль с логикой Arkham
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
    'initialized'
]

localS = LocalStorage()

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
        st.session_state.initialized = True
    if ('arkham_monitor' not in st.session_state or st.session_state.arkham_monitor is None) and \
       (st.session_state.get('api_key') or os.getenv("ARKHAM_API_KEY")):
        api_key = st.session_state.get('api_key') or os.getenv("ARKHAM_API_KEY")
        try:
            st.session_state.arkham_monitor = arkham_service.create_monitor(api_key)
        except Exception as e:
            st.session_state.arkham_monitor = None
        if st.session_state.arkham_monitor is None:
            st.session_state.api_key_loaded = False
            st.session_state.error_message = "Не удалось инициализировать Arkham Monitor. Проверьте API ключ или настройки сети."

def load_app_settings():
    if "app_state_loaded" not in st.session_state:
        try:
            raw_state = localS.getItem("app_state")
            if raw_state:
                state_dict = json.loads(raw_state)
                if state_dict.get("state_version") == 1:
                    for k in WHITELIST_KEYS:
                        if k in state_dict:
                            st.session_state[k] = state_dict[k]
            st.session_state.app_state_loaded = True
        except Exception as e:
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
        localS.setItem("app_state", json.dumps(state_to_save, ensure_ascii=False))
    except Exception:
        pass

def load_arkham_cache(arkham_monitor):
    if "arkham_cache_loaded" not in st.session_state and arkham_monitor is not None:
        try:
            raw_cache = localS.getItem("arkham_cache")
            if raw_cache:
                cache_dict = json.loads(raw_cache)
                arkham_monitor.load_full_cache_state(cache_dict)
            st.session_state.arkham_cache_loaded = True
        except Exception as e:
            st.session_state.arkham_cache_loaded = True

def save_arkham_cache(arkham_monitor):
    if arkham_monitor is not None:
        try:
            cache_to_save = arkham_monitor.get_full_cache_state()
            localS.setItem("arkham_cache", json.dumps(cache_to_save, ensure_ascii=False))
        except Exception:
            pass

def handle_populate_cache_button():
    """Обработчик для кнопки обновления кеша Arkham."""
    if st.session_state.arkham_monitor:
        # Получаем значения из session_state, куда их записали виджеты по ключам
        lookback = st.session_state.lookback_cache_input
        min_usd = st.session_state.min_usd_cache_input
        limit = st.session_state.limit_cache_input
        
        with st.spinner("Обновление кеша данных Arkham..."):
            tokens, addresses, error = arkham_service.populate_arkham_cache(
                st.session_state.arkham_monitor, lookback, min_usd, limit
            )
        
        if error:
            st.session_state.error_message = error
            # Очищаем списки, если была ошибка, чтобы не показывать старые данные
            st.session_state.known_tokens = []
            st.session_state.known_addresses = []
            st.session_state.cache_initialized_flag = False
            st.session_state.detailed_token_info = {} # Возвращаем
            st.session_state.detailed_address_info = {} # Возвращаем
        else:
            st.session_state.known_tokens = tokens # Возвращаем
            st.session_state.known_addresses = addresses # Возвращаем
            st.session_state.cache_initialized_flag = True
            st.session_state.error_message = None # Очищаем предыдущие ошибки
            st.success(f"Кеш успешно обновлен. Загружено {len(tokens)} токенов и {len(addresses)} адресов.") # Возвращаем исходное сообщение

            # Получаем детализированную информацию
            token_details, token_err = arkham_service.get_detailed_token_info(st.session_state.arkham_monitor)
            if token_err:
                st.warning(f"Не удалось получить детали по токенам: {token_err}")
                st.session_state.detailed_token_info = {} # Возвращаем
            else:
                st.session_state.detailed_token_info = token_details if token_details is not None else {} # Возвращаем
            
            address_details, addr_err = arkham_service.get_detailed_address_info(st.session_state.arkham_monitor)
            if addr_err:
                st.warning(f"Не удалось получить детали по адресам: {addr_err}")
                st.session_state.detailed_address_info = {} # Возвращаем
            else:
                st.session_state.detailed_address_info = address_details if address_details is not None else {} # Возвращаем
            # Сохраняем кеш Arkham только после успешного обновления
            save_arkham_cache(st.session_state.arkham_monitor)
        # st.rerun() # Убираем rerun
    else:
        st.session_state.error_message = "Arkham Monitor не инициализирован. Невозможно обновить кеш."
        # st.rerun() # Убираем rerun

def handle_auto_refresh_toggle():
    """Обработчик для переключателя автообновления (просто переключает флаг)."""
    # Логика запуска/остановки потока удалена
    # Состояние auto_refresh_enabled меняется автоматически виджетом st.toggle
    pass # Теперь эта функция может быть пустой или ее можно убрать, если on_change не нужен 
         # Оставим пока pass для ясности, что on_change был, но логика изменилась.
         # Или можно убрать on_change из st.toggle ниже.

def _fetch_and_update_table():
    """Получает транзакции и обновляет session_state."""
    if not st.session_state.arkham_monitor:
        st.session_state.error_message = "Arkham Monitor не инициализирован. Невозможно выполнить запрос."
        st.session_state.transactions_df = pd.DataFrame() # Очищаем старые результаты
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

        if st.session_state.arkham_monitor:
            updated_tokens = st.session_state.arkham_monitor.get_known_token_symbols()
            updated_addresses = st.session_state.arkham_monitor.get_known_address_names()

            if set(st.session_state.get('known_tokens', [])) != set(updated_tokens):
                st.session_state.known_tokens = updated_tokens
            
            if set(st.session_state.get('known_addresses', [])) != set(updated_addresses):
                st.session_state.known_addresses = updated_addresses

            token_details, token_err = arkham_service.get_detailed_token_info(st.session_state.arkham_monitor)
            if token_err:
                st.warning(f"Не удалось обновить детали по токенам после поиска: {token_err}")
            else:
                st.session_state.detailed_token_info = token_details if token_details is not None else {}
            
            address_details, addr_err = arkham_service.get_detailed_address_info(st.session_state.arkham_monitor)
            if addr_err:
                st.warning(f"Не удалось обновить детали по адресам после поиска: {addr_err}")
            else:
                st.session_state.detailed_address_info = address_details if address_details is not None else {}
            
            save_arkham_cache(st.session_state.arkham_monitor)
            # Устанавливаем флаг, что кеш был инициализирован/обновлен, если он не был установлен
            if not st.session_state.cache_initialized_flag and (updated_tokens or updated_addresses):
                 st.session_state.cache_initialized_flag = True


        if st.session_state.transactions_df.empty:
            st.info("Транзакции по заданным фильтрам не найдены.")
        else:
            pass

def handle_fetch_transactions_button():
    """Обработчик для кнопки "Найти Транзакции"."""
    _fetch_and_update_table() # Просто вызываем общую функцию
    # st.rerun() # Убираем rerun

def render_sidebar():
    """Отрисовывает боковую панель."""

    with st.sidebar.expander("Настройки API и Кеша", expanded=False):
        st.selectbox(
            "Период для кеша", 
            ['24h', '7d', '30d'], 
            key='lookback_cache_input', 
            help="Период для первоначальной загрузки данных в кеш (адреса, токены)."
        )
        # Value убран
        st.number_input(
            "Мин. USD для кеша", 
            min_value=0.0,
            step=1000.0, 
            key='min_usd_cache_input',
            format="%.0f",
            help="Минимальная сумма транзакции в USD для наполнения кеша."
        )
        # Value убран
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
        # Изменяем пропорции колонок на [2, 1]
        cols = st.columns([2, 1])
        # Value убран
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
        # Все фильтры и кнопка поиска теперь внутри этого экспандера
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
        # Value убран
        st.number_input(
            "Лимит транзакций в результате", 
            min_value=1, 
            max_value=1000, 
            step=10, 
            key='limit_query_input', 
            help="Максимальное кол-во транзакций в итоговом результате."
        )
        st.button("Найти Транзакции", on_click=handle_fetch_transactions_button, key="fetch_transactions_btn")

    with st.sidebar.expander("Автоматическое Обновление"):
        st.toggle(
            "Включить", 
            key='auto_refresh_enabled', 
            # on_change=handle_auto_refresh_toggle, # Убираем on_change, т.к. логика теперь в main
            help="Автоматически обновлять таблицу транзакций. ВНИМАНИЕ: Приложение будет неактивно во время ожидания интервала."
        )
        st.number_input(
            "Интервал обновления (сек)", 
            min_value=10, 
            step=10, 
            key='auto_refresh_interval', 
            help="Как часто обновлять таблицу (минимум 10 секунд).",
            # disabled=st.session_state.get('auto_refresh_running', False) # Убираем disabled, т.к. нет auto_refresh_running
        )

def render_main_content():
    """Отрисовывает основное содержимое страницы."""
    # st.title("Arkham Client Explorer") # Удаляем заголовок

    # Отображение ошибок из session_state, если они не были обработаны кнопками
    if st.session_state.get('error_message'):
        st.error(st.session_state.error_message)
        st.session_state.error_message = None # Сбрасываем после отображения

    # Общая информация и статус
    if st.session_state.get('api_key_loaded') and st.session_state.get('arkham_monitor'):
        if not st.session_state.get('cache_initialized_flag'):
            st.info("Данные для кеша (имена адресов, символы токенов) еще не загружены. Используйте кнопку в сайдбаре для загрузки.")
    else:
        # Ошибка уже должна была быть показана в main() и приложение остановлено, но на всякий случай
        st.error("Приложение не может функционировать без API ключа или инициализации монитора.")
        return # Не рендерим дальше, если нет монитора
        
    # Отображение Транзакций
    transactions_df = st.session_state.get('transactions_df', pd.DataFrame())
    if not transactions_df.empty:
        with st.expander("Найденные транзакции", expanded=True):
            st.dataframe(
                transactions_df, 
                use_container_width=True,
                height=600,  # Увеличиваем высоту таблицы
                column_config={
                    "Откуда": st.column_config.TextColumn(width="medium"),
                    "Куда": st.column_config.TextColumn(width="medium")
                }
            )
    # Сообщение "не найдено" выводится в handle_fetch_transactions_button через st.info, 
    # здесь дополнительно можно не дублировать, если только не хотим специфичное отображение.

    # Информация о Кеше
    with st.expander("Информация о кеше (адреса и токены)", expanded=False):
        known_tokens_list = st.session_state.get('known_tokens', [])
        known_addresses_list = st.session_state.get('known_addresses', [])
        cache_initialized = st.session_state.get('cache_initialized_flag', False)

        tab1, tab2, tab3 = st.tabs(["Сводка", "Известные Адреса", "Известные Токены"])

        with tab1: # Сводка
            if not cache_initialized:
                st.info("Кеш еще не инициализирован. Пожалуйста, загрузите его, используя опцию в сайдбаре.")
            else:
                detailed_addresses_count = len(st.session_state.get('detailed_address_info', {}))
                detailed_tokens_count = len(st.session_state.get('detailed_token_info', {}))
                st.write(f"Уникальных имен/адресов в кеше: {len(known_addresses_list)} (детализировано: {detailed_addresses_count})")
                st.write(f"Уникальных символов токенов в кеше: {len(known_tokens_list)} (детализировано: {detailed_tokens_count})")
                if not known_addresses_list and not known_tokens_list:
                    st.write("Кеш был инициализирован, но не содержит данных (0 адресов, 0 токенов).")

        with tab2: # Известные Адреса
            if not cache_initialized:
                st.info("Кеш не инициализирован. Данные об адресах отсутствуют.")
            elif not known_addresses_list:
                st.info("Список известных адресов пуст. Загрузите или обновите кеш из сайдбара.")
            else:
                # Готовим данные для DataFrame
                data_for_addresses_df = []
                detailed_address_info = st.session_state.get('detailed_address_info', {})
                for name in known_addresses_list: # known_addresses_list уже отсортирован из кеша
                    count = detailed_address_info.get(name, 0) # Получаем количество ID
                    data_for_addresses_df.append({"Адрес/Имя": name, "Кол-во связанных ID": count})
                
                df_addresses = pd.DataFrame(data_for_addresses_df)
                st.dataframe(df_addresses, use_container_width=True, height=300)
        
        with tab3: # Известные Токены
            if not cache_initialized:
                st.info("Кеш не инициализирован. Данные о токенах отсутствуют.")
            elif not known_tokens_list:
                st.info("Список известных токенов пуст. Загрузите или обновите кеш из сайдбара.")
            else:
                # Готовим данные для DataFrame
                data_for_tokens_df = []
                detailed_token_info = st.session_state.get('detailed_token_info', {})
                for symbol in known_tokens_list: # known_tokens_list уже отсортирован из кеша
                    ids_set = detailed_token_info.get(symbol, set())
                    ids_str = ", ".join(sorted(list(ids_set))) # Отображаем ID через запятую, отсортировав
                    count_ids = len(ids_set)
                    # Можно выбрать, что отображать: сами ID или их количество, или и то и другое
                    data_for_tokens_df.append({"Символ Токена": symbol, "ID Токенов": ids_str, "Кол-во ID": count_ids})
                
                df_tokens = pd.DataFrame(data_for_tokens_df)
                # Конфигурируем колонки, чтобы ID были видны, если они длинные
                st.dataframe(
                    df_tokens, 
                    use_container_width=True, 
                    height=300,
                    column_config={
                        "ID Токенов": st.column_config.TextColumn(width="large")
                    }
                )

def main():
    load_app_settings()
    initialize_session_state()
    if st.session_state.get('arkham_monitor') is not None:
        load_arkham_cache(st.session_state.arkham_monitor)
    if st.session_state.get('error_message') and not st.session_state.get('arkham_monitor'):
        st.error(st.session_state.error_message)
        st.session_state.error_message = None
        st.stop()
    elif not st.session_state.get('api_key_loaded', False):
        current_error = st.session_state.get('error_message', "Критическая ошибка: ARKHAM_API_KEY не найден или недействителен. Проверьте .env файл.")
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
    # load_custom_css("assets/style.css") # Убираем отсюда, если он был здесь ранее глобально
    main() 