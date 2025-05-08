# Промт 04: Детальный План Разработки Кода для Arkham Client Streamlit App

**Роль:** Ведущий Разработчик

**Дата:** {{YYYY-MM-DD}} <!-- Замени на текущую дату -->

**Контекст:** Пользовательский интерфейс (см. `streamlit_app/docs/UI_Specification.md`) и архитектура приложения (см. `streamlit_app/docs/Architecture_Specification.md` - `app.py` + `arkham_service.py`) определены. Настало время составить детальный пошаговый план написания кода.

**Цель:** Предоставить исчерпывающее руководство для реализации Streamlit-приложения, включая структуру файлов, импорты, сигнатуры ключевых функций, логику управления состоянием, обработку пользовательского ввода, взаимодействие с `arkham_service.py` и обработку ошибок.

**Общая Структура Файлов (согласно `Architecture_Specification.md`):**
```
streamlit_app/
├── app.py                     # Основной файл приложения Streamlit (UI, управление потоком)
├── arkham_service.py          # Модуль для всей логики работы с arkham_client
├── assets/                    # Директория для статических файлов
│   └── style.css              # Пользовательские стили
├── requirements.txt           # Зависимости приложения
└── docs/
    ├── UI_Specification.md
    └── Architecture_Specification.md
```
*Файл `.env` с API-ключом ожидается в корневой директории проекта: `arkham_web/.env`*

---

**I. План для `arkham_service.py`**

**Цель `arkham_service.py`:** Инкапсулировать всю логику взаимодействия с библиотекой `arkham_client`. Функции этого модуля будут вызываться из `app.py`.

**1.1. Импорты:**
```python
import pandas as pd
from arkham.arkham_monitor import ArkhamMonitor # Убедиться, что путь импорта соответствует структуре arkham_client
import requests # Для обработки возможных исключений RequestException
# Другие необходимые импорты, если появятся
```

**1.2. Функция `create_monitor(api_key: str) -> ArkhamMonitor | None`:**
*   **Назначение:** Создает и возвращает экземпляр `ArkhamMonitor`.
*   **Логика:**
    *   Принимает `api_key`.
    *   Если `api_key` предоставлен:
        *   В `try-except` блоке инициализировать `ArkhamMonitor(api_key=api_key)`.
        *   Вернуть экземпляр в случае успеха.
        *   В случае `Exception` (например, если ключ невалидный и библиотека это проверяет при инициализации), вернуть `None` (или можно логировать и возвращать `None`).
    *   Если `api_key` не предоставлен, вернуть `None`.

**1.3. Функция `populate_arkham_cache(monitor: ArkhamMonitor, lookback: str, min_usd: float, limit: int) -> tuple[list, list, str | None]`:**
*   **Назначение:** Наполняет внутренний кеш `ArkhamMonitor` (адреса, токены) и возвращает эти списки.
*   **Параметры:**
    *   `monitor`: Экземпляр `ArkhamMonitor`.
    *   `lookback`, `min_usd`, `limit`: Параметры для первоначального запроса транзакций для наполнения кеша.
*   **Логика:**
    *   В `try-except` блоке:
        *   Вызвать `monitor.set_filters(min_usd=min_usd, lookback=lookback)`.
        *   Вызвать `initial_df = monitor.get_transactions(limit=limit)`. (DataFrame `initial_df` сам по себе здесь не критичен, важен побочный эффект наполнения кеша).
        *   Получить списки: `known_tokens = monitor.get_known_token_symbols()`
        *   Получить списки: `known_addresses = monitor.get_known_address_names()`
        *   Вернуть `(known_tokens, known_addresses, None)` в случае успеха.
    *   **Обработка Исключений:**
        *   Перехватить `requests.exceptions.RequestException` (сетевые ошибки, проблемы с API Arkham). Сформировать понятное сообщение об ошибке.
        *   Перехватить общие `Exception` для непредвиденных ошибок. Сформировать сообщение.
        *   В случае ошибки вернуть `([], [], error_message_string)`.

**1.4. Функция `fetch_transactions(monitor: ArkhamMonitor, filter_params: dict, query_limit: int) -> tuple[pd.DataFrame | None, str | None]`:**
*   **Назначение:** Получает транзакции на основе заданных фильтров.
*   **Параметры:**
    *   `monitor`: Экземпляр `ArkhamMonitor`.
    *   `filter_params`: Словарь с фильтрами: `{'min_usd': float, 'lookback': str, 'token_symbols': list, 'from_address_names': list, 'to_address_names': list}`. Некоторые ключи могут отсутствовать или иметь значение `None`, если фильтр не применяется.
    *   `query_limit`: Целое число, лимит для запроса транзакций.
*   **Логика:**
    *   В `try-except` блоке:
        *   Распаковать `filter_params` и вызвать `monitor.set_filters(...)`, передавая только те параметры, которые действительно установлены (не `None` и не пустые списки, если библиотека этого требует).
        *   Вызвать `transactions_df = monitor.get_transactions(limit=query_limit)`.
        *   Вернуть `(transactions_df, None)` в случае успеха.
    *   **Обработка Исключений:**
        *   Аналогично `populate_arkham_cache`, перехватить `requests.exceptions.RequestException` и `Exception`.
        *   В случае ошибки вернуть `(None, error_message_string)`.

---

**II. План для `app.py`**

**Цель `app.py`:** Реализовать UI, управлять состоянием сессии, обрабатывать ввод пользователя и взаимодействовать с `arkham_service.py`.

**2.1. Импорты:**
```python
import streamlit as st
import pandas as pd
import os
from dotenv import load_dotenv
import arkham_service # Модуль с логикой Arkham
# Нужен typing для подсказок типов, если используется
from typing import List, Dict, Any, Tuple, Optional 
```

**2.2. Функция `load_custom_css(file_path: str)`:**
*   **Назначение:** Загружает и применяет CSS из файла.
*   **Логика:**
    *   Проверяет существование `file_path`.
    *   Если существует, читает содержимое и вставляет в `st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)`.

**2.3. Функция `initialize_session_state()`:**
*   **Назначение:** Инициализирует `st.session_state` при первом запуске или если ключевые переменные отсутствуют.
*   **Логика:** Вызывается один раз в начале скрипта.
    ```python
    if 'initialized' not in st.session_state:
        # 1. Загрузка API ключа
        dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env') # Путь к .env в корне arkham_web
        load_dotenv(dotenv_path=dotenv_path)
        api_key = os.getenv("ARKHAM_API_KEY")
        st.session_state.api_key = api_key
        st.session_state.api_key_loaded = bool(api_key)

        # 2. Инициализация монитора (если ключ есть)
        if st.session_state.api_key_loaded:
            st.session_state.arkham_monitor = arkham_service.create_monitor(st.session_state.api_key)
            if st.session_state.arkham_monitor is None: # Ошибка создания монитора
                st.session_state.api_key_loaded = False # Считаем, что ключ невалиден или проблема
                st.session_state.error_message = "Не удалось инициализировать Arkham Monitor. Проверьте API ключ или настройки сети."
            else:
                 st.session_state.error_message = None
        else:
            st.session_state.arkham_monitor = None
            st.session_state.error_message = "ARKHAM_API_KEY не найден в .env файле."

        # 3. Инициализация остальных переменных состояния
        st.session_state.cache_initialized_flag = False
        st.session_state.known_tokens = []
        st.session_state.known_addresses = []
        st.session_state.transactions_df = pd.DataFrame() # Пустой DataFrame
        
        # Значения по умолчанию для фильтров кеша (из UI_Specification)
        st.session_state.lookback_cache_input = '7d'
        st.session_state.min_usd_cache_input = 10000.0 # float
        st.session_state.limit_cache_input = 1000

        # Значения по умолчанию для фильтров запроса (из UI_Specification)
        st.session_state.min_usd_query_input = 1000000.0 # float
        st.session_state.lookback_query_input = '7d'
        st.session_state.token_symbols_multiselect = []
        st.session_state.from_address_names_multiselect = []
        st.session_state.to_address_names_multiselect = []
        st.session_state.limit_query_input = 50
        
        st.session_state.initialized = True # Флаг, что инициализация прошла
    ```

**2.4. Функции Обработчики (Callbacks для кнопок):**
    *   **`handle_populate_cache_button()`:**
        *   Вызывается при нажатии кнопки "Загрузить/Обновить данные для кеша".
        *   Проверить, что `st.session_state.arkham_monitor` существует.
        *   Получить параметры `lookback`, `min_usd`, `limit` из соответствующих виджетов (или `st.session_state` если они там хранятся по `key`).
 