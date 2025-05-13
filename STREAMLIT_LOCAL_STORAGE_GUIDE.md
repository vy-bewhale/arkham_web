# Руководство по использованию streamlit-local-storage

В этом документе описаны особенности работы с библиотекой `streamlit-local-storage`, выявленные в ходе отладки.

## Проблема: `streamlit.errors.StreamlitDuplicateElementKey` при использовании `localS.setItem()`

**Причина:**
Ошибка `StreamlitDuplicateElementKey: There are multiple elements with the same key='set'` (или другой ключ по умолчанию) возникает, если функция `localS.setItem()` вызывается несколько раз в рамках одного запуска скрипта Streamlit без явного указания уникального параметра `key` для каждого вызова. Каждый вызов `setItem` по умолчанию пытается создать или использовать компонент Streamlit с одним и тем же внутренним ключом, что приводит к конфликту.

**Решение:**
При каждом вызове функции `localS.setItem()` необходимо передавать уникальное значение для строкового параметра `key`. Это гарантирует, что для каждого сохраняемого элемента будет использоваться отдельный внутренний компонент Streamlit.

Пример:
```python
localS.setItem("app_state", data_to_save, key="unique_key_for_app_state")
localS.setItem("user_preferences", preferences, key="unique_key_for_user_prefs")
```

## Проблема: `TypeError` при использовании `localS.getItem()` или `localS.getAll()` с параметром `key`

**Причина:**
Функции `localS.getItem()` и `localS.getAll()` в данной библиотеке **не принимают** параметр `key` в своей Python-сигнатуре. Попытка передать им именованный аргумент `key` приведет к ошибке `TypeError: got an unexpected keyword argument 'key'`.

**Решение:**
Не передавайте параметр `key` в функции `localS.getItem()` и `localS.getAll()`. Эти функции работают с ключами элементов, хранящихся в localStorage, а не с ключами компонентов Streamlit.

Пример:
```python
# Правильно
retrieved_data = localS.getItem("app_state")
all_data = localS.getAll()

# Неправильно (приведет к TypeError)
# retrieved_data = localS.getItem("app_state", key="some_key")
# all_data = localS.getAll(key="another_key")
``` 