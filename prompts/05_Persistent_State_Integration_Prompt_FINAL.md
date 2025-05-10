# Интеграция persistent state (памяти) для всех настроек и кеша Arkham через st_local_storage

**Задача:**
В приложении Arkham Alert на Streamlit реализовать механизм persistent state (памяти) для хранения кеша Arkham и всех пользовательских настроек фильтров между сессиями пользователя. Используй библиотеку `st_local_storage`, чтобы сохранять и восстанавливать эти данные через localStorage браузера. После интеграции все фильтры и кеш должны автоматически сохраняться после изменений и восстанавливаться при запуске приложения.

**Используй только этот способ! Не реализуй delete, проверки наличия, обёртки, версионирование, лимиты и т.д.**

---

## Шаг 1. Импорт библиотеки

> Импортируй минималистичную библиотеку для работы с localStorage.

```python
from streamlit_app.st_local_storage import st_local_storage
```

---

## Шаг 2. Ключи для хранения

> Используй фиксированные ключи для кеша и фильтров, чтобы данные не путались между пользователями и сессиями.

- Кеш Arkham: "arkham_alert_cache"
- Настройки фильтров: "arkham_alert_filters"
- (опционально) Профиль пользователя: "arkham_alert_profile_id"

---

## Шаг 3. Чтение состояния при запуске

> Выполняй до рендера виджетов, чтобы значения подтянулись в UI. Если данных нет — используются значения по умолчанию.

```python
cache = st_local_storage["arkham_alert_cache"]
if cache is not None:
    arkham_monitor.load_full_cache_state(cache)

filters = st_local_storage["arkham_alert_filters"]
if filters is not None:
    for k, v in filters.items():
        st.session_state[k] = v
```

---

## Шаг 4. Сохранение состояния после изменений

> Выполняй после успешного обновления кеша или изменения фильтров, чтобы сохранить актуальные данные для пользователя.

```python
st_local_storage["arkham_alert_cache"] = arkham_monitor.get_full_cache_state()

# Сохраняй только нужные ключи фильтров:
filter_keys = [
    "lookback_cache_input", "min_usd_cache_input", "limit_cache_input",
    "min_usd_query_input", "lookback_query_input", "token_symbols_multiselect",
    "from_address_names_multiselect", "to_address_names_multiselect", "limit_query_input"
]
filters_to_save = {k: st.session_state[k] for k in filter_keys if k in st.session_state}
st_local_storage["arkham_alert_filters"] = filters_to_save
```

---

## Шаг 5. Особенности и ограничения

> Нет удаления, нет проверки наличия, все данные только в браузере, лимит localStorage ~5MB. Нет синхронизации между пользователями или устройствами. Вся сложность реализована внутри самой библиотеки.

- Если ключа нет — возвращается None, ошибок не возникает.
- Нет удаления и проверки наличия ключа.
- Все данные хранятся только в браузере пользователя (localStorage, лимит ~5MB).
- Нет синхронизации между пользователями или устройствами.
- Вся сложность реализована внутри самой библиотеки.

---

## Шаг 6. Итоговый пример интеграции (минимальный)

> Минимальный рабочий пример, который можно сразу вставить в проект. Чтение — до рендера виджетов, запись — после изменений кеша или фильтров.

```python
from streamlit_app.st_local_storage import st_local_storage

# Загрузка состояния (до рендера виджетов)
cache = st_local_storage["arkham_alert_cache"]
if cache is not None:
    arkham_monitor.load_full_cache_state(cache)
filters = st_local_storage["arkham_alert_filters"]
if filters is not None:
    for k, v in filters.items():
        st.session_state[k] = v

# ... (основная логика приложения)

# Сохранять после изменений (например, после обновления кеша или фильтров)
st_local_storage["arkham_alert_cache"] = arkham_monitor.get_full_cache_state()
filter_keys = [
    "lookback_cache_input", "min_usd_cache_input", "limit_cache_input",
    "min_usd_query_input", "lookback_query_input", "token_symbols_multiselect",
    "from_address_names_multiselect", "to_address_names_multiselect", "limit_query_input"
]
filters_to_save = {k: st.session_state[k] for k in filter_keys if k in st.session_state}
st_local_storage["arkham_alert_filters"] = filters_to_save
```

---

## Результат

> После интеграции все фильтры и кеш будут автоматически сохраняться и восстанавливаться между сессиями браузера. Не реализуй ничего лишнего. Вся интеграция — это две строчки на чтение и две на запись. Если нужен профиль — просто сохрани/прочитай profile_id отдельным ключом.

---

**Этот промт заменяет все предыдущие инструкции.  
Следуй только ему.  
Гарантированно рабочий код с первого раза.** 