# Промт 05 (Версия 2): Интеграция Персистентного Состояния (Памяти) в Arkham Alert

**Роль:** Ведущий Разработчик / Архитектор Streamlit-приложений

**Дата:** {{YYYY-MM-DD}}

**Контекст:**
Приложение Arkham Alert на Streamlit успешно взаимодействует с библиотекой `arkham_client`. Библиотека `arkham_client` теперь поддерживает методы `get_full_cache_state()` и `load_full_cache_state()` для сериализации и десериализации своего внутреннего кеша. Текущая задача — реализовать механизм "памяти" для пользователя, чтобы состояние кеша `ArkhamMonitor` и выбранные пользователем настройки фильтров сохранялись между сеансами работы с приложением.

**Цель:**
Разработать и описать детальный план интеграции персистентного хранения состояния в приложение `streamlit_app/app.py`. План должен включать:
1.  Механизм сохранения и загрузки полного состояния кеша `ArkhamMonitor`.
2.  Механизм сохранения и загрузки пользовательских настроек фильтров.
3.  Способ идентификации пользователя/профиля.
4.  Использование `localStorage` браузера для хранения данных.
5.  Необходимые изменения в `streamlit_app/app.py`.
6.  Обработку ошибок и крайних случаев, включая ограничения `localStorage`.

**Технологические Предпосылки:**
*   Streamlit не предоставляет прямого Python API для записи в `localStorage`.
*   Будет использован надежный существующий компонент Streamlit для взаимодействия с `localStorage` или, в крайнем случае, создан минимально необходимый кастомный компонент.
*   Состояние кеша и настройки фильтров будут сериализованы в JSON.

**Детальный План Интеграции:**

**I. Компонент для Работы с `localStorage`**

1.  **Поиск и Выбор Компонента:**
    *   **Задача:** Найти и интегрировать существующий, хорошо зарекомендовавший себя Streamlit компонент для двунаправленного взаимодействия с `localStorage`.
    *   **Приоритетные кандидаты для исследования:**
        *   `streamlit-cookies-manager` (хотя ориентирован на cookies, проверить, нет ли у него функционала для `localStorage` или легко адаптируемых примеров).
        *   `streamlit-local-storage` (https://github.com/jrieke/streamlit-local-storage) - выглядит обещающе, необходимо проверить его текущее состояние, поддержку и простоту использования.
        *   Поиск по ключевым словам: "streamlit localstorage", "streamlit session storage component", "streamlit browser storage".
    *   **Критерии выбора:**
        *   **Надежность и Поддержка:** Активность репозитория, количество issues, наличие обновлений.
        *   **Простота API:** Интуитивно понятные функции для `set_item(key, value)` и `get_item(key)`.
        *   **Обработка ошибок:** Как компонент сообщает об ошибках JavaScript (например, если `localStorage` отключен).
        *   **Производительность:** Отсутствие известных проблем с производительностью при частых вызовах (хотя мы постараемся их минимизировать).
    *   **Если надежный компонент не найден (План Б - создание своего - ИЗБЕГАТЬ ПО ВОЗМОЖНОСТИ):**
        *   Если абсолютно необходимо, создать минимальный компонент, как описано в Версии 1 промта, с акцентом на надежную обработку ошибок на стороне JS и четкую передачу статуса в Python. Компонент должен быть тщательно протестирован отдельно.
    *   **Действие:** В `streamlit_app/requirements.txt` добавить выбранный компонент. Обернуть вызовы компонента в helper-функции в `app.py` для унификации интерфейса, например:
        ```python
        # В app.py
        # import json # Уже должен быть импортирован
        # import streamlit as st # Уже должен быть импортирован
        # from streamlit_local_storage import LocalStorage # Пример, зависит от выбранного компонента
        # storage_manager = LocalStorage() # Или другая инициализация в зависимости от API компонента

        def set_to_localStorage(key: str, value_dict: dict) -> bool:
            try:
                json_value = json.dumps(value_dict)
                # Проверка размера перед записью
                # Учитываем, что символы UTF-8 могут занимать больше 1 байта
                estimated_size_bytes = len(json_value.encode('utf-8')) 
                # Оставляем запас, например, 4.5MB из 5MB общего лимита
                if estimated_size_bytes > 4.5 * 1024 * 1024: 
                     st.warning(f"Данные для ключа '{key}' ({estimated_size_bytes / (1024*1024):.2f} MB) слишком велики для сохранения в localStorage (лимит ~4.5MB).")
                     return False
                
                # ЗАМЕНИТЬ ЭТО РЕАЛЬНЫМ ВЫЗОВОМ КОМПОНЕНТА:
                # component_set_item_status = storage_manager.setItem(key, json_value) 
                # if not component_set_item_status: # Если компонент возвращает статус записи
                #    st.error(f"Компонент не смог записать данные в localStorage (ключ: {key}).")
                #    return False
                print(f"DEBUG: Пытаюсь записать в localStorage: key='{key}', value='{json_value[:100]}...'") # Убрать в продакшене
                # Предполагаем, что если исключения нет, то запись успешна, или компонент сам обработает
                return True 
            except TypeError as e: 
                st.error(f"Ошибка сериализации данных для localStorage (ключ: {key}): {e}")
                return False
            except Exception as e: 
                st.error(f"Ошибка записи в localStorage (ключ: {key}): {e}")
                return False

        def get_from_localStorage(key: str) -> dict | None:
            try:
                # ЗАМЕНИТЬ ЭТО РЕАЛЬНЫМ ВЫЗОВОМ КОМПОНЕНТА:
                # json_value = storage_manager.getItem(key) 
                json_value = None # Заглушка
                print(f"DEBUG: Пытаюсь прочитать из localStorage: key='{key}', получил='{str(json_value)[:100]}...'") # Убрать в продакшене
                
                if json_value:
                    return json.loads(json_value)
                return None
            except json.JSONDecodeError:
                st.warning(f"Ошибка десериализации данных из localStorage (ключ: {key}). Данные могут быть повреждены. Ключ будет очищен.")
                # ЗАМЕНИТЬ ЭТО РЕАЛЬНЫМ ВЫЗОВОМ КОМПОНЕНТА ДЛЯ УДАЛЕНИЯ:
                # storage_manager.deleteItem(key) 
                print(f"DEBUG: Пытаюсь удалить поврежденный ключ: '{key}'") # Убрать в продакшене
                return None
            except Exception as e:
                st.error(f"Ошибка чтения из localStorage (ключ: {key}): {e}")
                return None
        
        def delete_from_localStorage(key: str) -> bool:
            try:
                # ЗАМЕНИТЬ ЭТО РЕАЛЬНЫМ ВЫЗОВОМ КОМПОНЕНТА:
                # storage_manager.deleteItem(key)
                print(f"DEBUG: Пытаюсь удалить ключ: '{key}'") # Убрать в продакшене
                return True
            except Exception as e:
                st.error(f"Ошибка удаления ключа из localStorage (ключ: {key}): {e}")
                return False
        ```

2.  **Определение Ключей для `localStorage` (с версионированием):**
    *   `PROFILE_ID_KEY = "arkham_alert_profile_id_v1"`
    *   `CACHE_STATE_KEY_TEMPLATE = "arkham_alert_cache_state_v{version}_{profile_id}"`
    *   `FILTER_SETTINGS_KEY_TEMPLATE = "arkham_alert_filter_settings_v{version}_{profile_id}"`
    *   Текущая версия для данных: `DATA_VERSION = "1"` (определить как константу в `app.py`).

**II. Идентификация Пользователя/Профиля**

1.  **Механизм Профилей (Уникальный ID Браузера):**
    *   **Задача:** Автоматически генерировать и использовать уникальный идентификатор для каждого браузера пользователя.
    *   **Реализация (в `app.py`):**
        ```python
        # import uuid # Уже должен быть импортирован

        def get_or_create_profile_id() -> str:
            profile_data = get_from_localStorage(PROFILE_ID_KEY) 
            if profile_data and isinstance(profile_data, dict) and "id" in profile_data:
                 return profile_data["id"]
            
            new_profile_id = str(uuid.uuid4())
            # Сохраняем ID в виде словаря, чтобы в будущем можно было добавить другие метаданные профиля
            success = set_to_localStorage(PROFILE_ID_KEY, {"id": new_profile_id, "created_at": time.time()}) 
            if success:
                return new_profile_id
            else:
                st.warning("Не удалось сохранить ID профиля в localStorage. " 
                           "Сохранение состояния будет недоступно в этой сессии. "
                           "Возможно, localStorage отключен или переполнен.")
                # Возвращаем временный ID, чтобы остальная логика не падала, но понимала, что сохранение не работает
                return f"session_only_{str(uuid.uuid4())}" 
        ```
    *   `profile_id` будет получен один раз при инициализации `st.session_state` и сохранен в `st.session_state.current_profile_id`.
    *   Проверить, что если `profile_id` начинается с `"session_only_"`, то функции сохранения не будут пытаться писать в `localStorage`.

**III. Модификация `streamlit_app/app.py` (Загрузка и Сохранение Состояния)**

1.  **Импорты:** `json`, `uuid`, `time`.

2.  **Обновление `initialize_session_state()`:**
    *   **В самом начале функции (до загрузки API ключа):**
        *   `st.session_state.current_profile_id = get_or_create_profile_id()`
        *   `st.session_state.localStorage_available = not st.session_state.current_profile_id.startswith("session_only_")`
    *   **После инициализации `st.session_state.arkham_monitor` (если `api_key_loaded` И `st.session_state.localStorage_available`):**
        *   `profile_id = st.session_state.current_profile_id`
        *   `cache_ls_key = CACHE_STATE_KEY_TEMPLATE.format(version=DATA_VERSION, profile_id=profile_id)`
        *   **Загрузка Состояния Кеша:**
            *   `saved_cache_state_dict = get_from_localStorage(cache_ls_key)`
            *   Если `saved_cache_state_dict` (уже словарь):
                *   В `try-except` блоке (на случай проблем с `load_full_cache_state` несмотря на успешную десериализацию):
                    *   `st.session_state.arkham_monitor.load_full_cache_state(saved_cache_state_dict)`
                    *   Обновить `st.session_state.cache_initialized_flag = True`.
                    *   Обновить `st.session_state.known_tokens` и `st.session_state.known_addresses` из загруженного монитора.
                    *   Обновить `st.session_state.detailed_token_info` и `st.session_state.detailed_address_info`.
                    *   `st.toast("Кеш Arkham загружен из памяти браузера.", icon="✅")`
                *   При ошибке: `st.warning(f"Ошибка применения сохраненного кеша Arkham: {e}")`
        *   **Загрузка Настроек Фильтров:**
            *   `filters_ls_key = FILTER_SETTINGS_KEY_TEMPLATE.format(version=DATA_VERSION, profile_id=profile_id)`
            *   `loaded_filters = get_from_localStorage(filters_ls_key)`
            *   Если `loaded_filters` (уже словарь):
                *   Безопасно обновить ключи в `st.session_state` для фильтров, используя `loaded_filters.get(key, st.session_state.get(key))` (чтобы не перезаписать значения по умолчанию, если ключ есть в session_state, но отсутствует в loaded_filters).
                *   `st.toast("Настройки фильтров загружены.", icon="✅")`

3.  **Функция `save_arkham_cache_to_localStorage()`:**
    *   Если не `st.session_state.localStorage_available`, то выход.
    *   Проверить `st.session_state.arkham_monitor`.
    *   `cache_state_dict = st.session_state.arkham_monitor.get_full_cache_state()`.
    *   Если `cache_state_dict`:
        *   `profile_id = st.session_state.current_profile_id`
        *   `cache_ls_key = CACHE_STATE_KEY_TEMPLATE.format(version=DATA_VERSION, profile_id=profile_id)`
        *   Если `set_to_localStorage(cache_ls_key, cache_state_dict)` вернуло `True`:
            *   `st.toast("Кеш Arkham сохранен в памяти браузера.", icon="💾")`
    *   **Вызывать:** После успешного `handle_populate_cache_button()`.

4.  **Функция `save_filter_settings_to_localStorage()`:**
    *   Если не `st.session_state.localStorage_available`, то выход.
    *   Собрать словарь `settings_to_save` из `st.session_state` (только ключи, относящиеся к настройкам виджетов фильтров, например, `lookback_cache_input`, `min_usd_query_input` и т.д.).
    *   `profile_id = st.session_state.current_profile_id`
    *   `filters_ls_key = FILTER_SETTINGS_KEY_TEMPLATE.format(version=DATA_VERSION, profile_id=profile_id)`
    *   Если `set_to_localStorage(filters_ls_key, settings_to_save)` вернуло `True`:
        *   `st.toast("Настройки фильтров сохранены.", icon="💾")`
    *   **Вызывать:** После успешного `handle_fetch_transactions_button()`.

**IV. Пользовательский Интерфейс (Изменения)**

1.  **Индикация доступности localStorage:**
    *   В `initialize_session_state`, если `localStorage_available` равно `False`, можно однократно показать `st.warning("Функция сохранения состояния в браузере недоступна. Данные не будут сохраняться между сессиями.")`.
2.  **Кнопка "Сбросить сохраненное состояние":**
    *   Добавить в сайдбар. Сделать ее неактивной (`disabled=not st.session_state.localStorage_available`), если localStorage недоступен.
    *   При нажатии:
        *   Запросить подтверждение `st.confirm("Вы уверены, что хотите удалить все сохраненные данные для этого браузера (кеш Arkham и настройки фильтров)?")`.
        *   Если подтверждено:
            *   `profile_id = st.session_state.current_profile_id`
            *   `cache_ls_key = CACHE_STATE_KEY_TEMPLATE.format(version=DATA_VERSION, profile_id=profile_id)`
            *   `filters_ls_key = FILTER_SETTINGS_KEY_TEMPLATE.format(version=DATA_VERSION, profile_id=profile_id)`
            *   `delete_from_localStorage(cache_ls_key)`
            *   `delete_from_localStorage(filters_ls_key)`
            *   `delete_from_localStorage(PROFILE_ID_KEY)`
            *   `st.success("Сохраненные данные сброшены. При следующей перезагрузке страницы будет создан новый профиль и данные будут загружаться с API Arkham.")`
            *   Можно предложить `st.button("Перезагрузить страницу сейчас")`, по клику на который выполнить `st.experimental_rerun()` (хотя полная перезагрузка Ctrl+R надежнее для сброса всего).

**V. Обработка Крайних Случаев и Ошибок (Усилено)**

1.  **Общие Принципы:** Функции-обертки `set_to_localStorage`, `get_from_localStorage`, `delete_from_localStorage` инкапсулируют базовую обработку ошибок и логирование. Вызывающий код проверяет их возвращаемые значения.
2.  **Поврежденные Данные:** `get_from_localStorage` уже пытается удалить ключ при ошибке десериализации.
3.  **Лимиты `localStorage`:** Базовая проверка размера в `set_to_localStorage`. При отказе в записи из-за размера, пользователь получит `st.warning`.

**VI. Тестирование Компонента `localStorage`**
*   Первоочередная задача - найти и протестировать надежный сторонний компонент.
*   Тестирование должно включать:
    *   Успешную запись/чтение/удаление.
    *   Поведение при попытке чтения несуществующего ключа (должен возвращать `None` без ошибок).
    *   Обработку ошибок при попытке записать слишком большие данные (если компонент это поддерживает).
    *   Как компонент ведет себя, если `localStorage` в браузере отключен или переполнен (должен корректно сообщать об ошибке в Python, не вызывая падение JS).

**Константы в `app.py`:**
```python
DATA_VERSION = "1"
PROFILE_ID_KEY = "arkham_alert_profile_id_v1" # Ключ для хранения самого ID профиля
CACHE_STATE_KEY_TEMPLATE = "arkham_alert_cache_state_v{version}_{profile_id}"
FILTER_SETTINGS_KEY_TEMPLATE = "arkham_alert_filter_settings_v{version}_{profile_id}"
MAX_LOCAL_STORAGE_ITEM_SIZE_MB = 4.5 # Максимальный размер одного элемента для сохранения
```

**Ожидаемый Результат:**
Детальный, надежный и готовый к имплементации план, который позволит разработчику интегрировать персистентное состояние с высокой вероятностью успеха с первого раза, учитывая множество нюансов работы с `localStorage` в Streamlit. 