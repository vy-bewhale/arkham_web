# 06. Реализация алертов в Telegram с повторными попытками и хранением истории

*(Версия 2, с учетом критики и обсуждения)*

## Цель
Добавить в Streamlit-приложение Arkham Client Explorer возможность отправки алертов о **новых** транзакциях в Telegram-группу через Bot API. Реализовать механизм повторных попыток при ошибках отправки, визуализацию статуса отправки в таблице транзакций (с использованием текстовых индикаторов), хранение истории отправленных алертов (по `TxID`) и настроек Telegram.

---

## Требования к функционалу

### 1. **UI (Боковая панель)**

- Добавить новый `st.sidebar.expander("Настройки алертов Telegram")`.
    - Поле для ввода **Chat ID** (`st.text_input`).
    - Переключатель "Включить алерты Telegram" (`st.toggle`).
    - **Примечание:** Поле для **Telegram Bot Token** **НЕ ДОЛЖНО** быть в UI из соображений безопасности.
- Изменения Chat ID и состояния переключателя должны автоматически сохраняться в `localStorage` (ключи: `telegram_chat_id`, `telegram_alerts_enabled`).
- Экспандер должен быть доступен всегда, но переключатель "Включить алерты" должен быть активен (`disabled=False`) только если:
    - `ARKHAM_API_KEY` успешно загружен.
    - `TELEGRAM_BOT_TOKEN` доступен (см. п. 6).
    - В поле Chat ID введено значение.

### 2. **Логика отправки алертов**

- **При каждом обновлении данных** (автоматическом или ручном, например, внутри `_fetch_and_update_table` после получения `df`):
    - Получить текущий список транзакций (`transactions_df` из `st.session_state`). Убедиться, что колонка `TxID` присутствует.
    - Загрузить историю отправленных алертов из `localStorage` (ключ `alert_history`). Если истории нет или она некорректна, инициализировать как пустой словарь.
    - **Для каждой транзакции в `transactions_df` (каждой строки):**
        - Получить `tx_hash` (значение из колонки `TxID`). Если `TxID` отсутствует или 'N/A', пропустить эту транзакцию для алертов.
        - Проверить, есть ли запись с этим `tx_hash` в `alert_history`.
        - **Если записи нет И `st.session_state.get('telegram_alerts_enabled', False)` И `tx_hash` валиден:**
            - Попытаться отправить алерт в Telegram (попытка №1). Результат (True/False) получить от функции отправки.
            - Создать запись в `alert_history[tx_hash]`: `{status: "success" if success else "pending", attempt: 1, last_attempt_time: time.time(), sent_time: time.time() if success else None}`. (Если первая попытка неудачна, статус сразу "pending", т.к. ошибка будет обработана следующей итерацией)
        - **Если запись есть с `alert_history[tx_hash].status` in ["pending", "error"] И `st.session_state.get('telegram_alerts_enabled', False)` И `alert_history[tx_hash].attempt < 5`:**
            - Проверить `alert_history[tx_hash].last_attempt_time`. Если `(time.time() - alert_history[tx_hash].last_attempt_time) >= 60` (прошла минута):
                - Увеличить `alert_history[tx_hash].attempt` на 1.
                - Попытаться отправить алерт снова. Результат (True/False) получить от функции отправки.
                - Обновить `alert_history[tx_hash].status` ("success" if success else "error" if `attempt` == 5 else "pending").
                - Обновить `alert_history[tx_hash].last_attempt_time = time.time()`.
                - Если успех, установить `alert_history[tx_hash].sent_time = time.time()`.
- Отправка должна происходить в основном потоке Streamlit.
- После обработки всех транзакций сохранить обновленную `alert_history` обратно в `localStorage`.

### 3. **Хранение состояния (`localStorage`)**

- **Настройки Telegram:**
    - `telegram_chat_id` (str): ID чата.
    - `telegram_alerts_enabled` (bool): Включены ли алерты.
- **История алертов (`alert_history`):**
    - Хранить как **словарь** в `localStorage` (ключ `alert_history`), где сам словарь: `{ tx_hash_1: {status_info_1}, tx_hash_2: {status_info_2}, ... }`.
    - `status_info`: `{status: str, attempt: int, sent_time: Optional[float], last_attempt_time: float}`. Время хранить как timestamp (например, `time.time()`).
    - `status`: "success", "pending", "error".
    - `attempt`: 1-5.
    - `sent_time`: Timestamp успешной отправки, иначе `None`.
    - `last_attempt_time`: Timestamp последней попытки.
    - Хранить **только последние 100 записей**. При добавлении 101-й уникальной `tx_hash` записи, удалить самую старую по `last_attempt_time` из существующих записей.

### 4. **Изменения в таблице транзакций (`st.dataframe`)**

- В функции `render_main_content` перед созданием `df_display`:
    - Загрузить `alert_history` из `localStorage`. Если нет или ошибка, использовать пустой словарь.
    - Создать новую колонку в `transactions_df` (которая в `st.session_state`), например `"Статус Telegram"`.
    - Для каждой строки `transactions_df`:
        - Получить `tx_hash = row['TxID']`.
        - Если `st.session_state.get('telegram_alerts_enabled', False)`:
            - Если `tx_hash` есть в `alert_history`:
                - `info = alert_history[tx_hash]`
                - `status = info['status']`
                - `attempt = info['attempt']`
                - `sent_time = info.get('sent_time')`
                - Если `status == "success"`: `✅ Отпр. ({attempt}) {time.strftime('%H:%M', time.localtime(sent_time)) if sent_time else ''}`
                - Если `status == "pending"` и `attempt < 5`: `⏳ Поп. {attempt+1}...`
                - Если `status == "error"` или (`status == "pending"` и `attempt >= 5`): `❌ Ошибка ({attempt})`
                - Записать это значение в колонку `"Статус Telegram"` для текущей строки.
            - Иначе (нет в истории): `➖`
        - Иначе (алерты выключены): `끄 Выкл.`
        - Записать вычисленное значение в колонку `"Статус Telegram"`.
    - Убедиться, что `df_display` создается уже *после* добавления этой новой колонки статуса и включает ее. Колонку `TxID` по-прежнему исключать из `df_display`.

### 5. **Формат сообщения для Telegram**

- Сообщение должно содержать данные из строки DataFrame, соответствующей `tx_hash`:
    - Время транзакции (из колонки `"Время"`, как есть или дополнительно отформатированное).
    - Сеть (из колонки `"Сеть"`).
    - Откуда (из колонки `"Откуда"`). Если в строке есть "cex" или "dex" (регистронезависимо), выделить их тегом `<b>`).
    - Куда (из колонки `"Куда"`). Аналогично "Откуда".
    - Токен (из колонки `"Символ"`).
    - Сумма в долларах (из колонки `"USD"`). Преобразовать в число, форматировать с разделителями тысяч (запятая или пробел) и 2 знаками после запятой, выделить тегом `<b>`).
    - Ссылка на транзакцию: `https://app.arkhamintelligence.com/explorer/tx/<TxID>` (подставить реальный `TxID`).
- Использовать HTML-форматирование (`parse_mode=HTML`). Важно: перед вставкой строковых данных из DataFrame (Откуда, Куда, Сеть, Символ) в HTML-шаблон сообщения, их нужно экранировать с помощью `html.escape()` для предотвращения HTML-инъекций или ошибок парсинга, если в данных содержатся символы `<`, `>`, `&`.
- Пример сообщения (HTML):
    ```html
    🕒 <i>{time_str}</i> (Tx Time)
    🌐 {network_str}
    <b>Откуда:</b> {from_str}
    <b>Куда:</b> {to_str}
    <b>Сумма:</b> <b>{usd_amount_formatted}</b> {token_symbol_str}
    🔗 <a href="https://app.arkhamintelligence.com/explorer/tx/{tx_id_str}">View on Arkham</a>
    ```

### 6. **Технические детали**

- **Telegram Bot Token:** Загружать из переменной окружения `TELEGRAM_BOT_TOKEN` (через `os.getenv("TELEGRAM_BOT_TOKEN")` или `st.secrets["TELEGRAM_BOT_TOKEN"]`). Проверять наличие при инициализации `app.py`. Если отсутствует, выводить предупреждение и деактивировать UI для алертов.
- Для отправки сообщений использовать `requests.post` к `https://api.telegram.org/bot<TOKEN>/sendMessage`.
- Параметры запроса: `chat_id`, `text`, `parse_mode='HTML'`, `disable_web_page_preview=True`.
- Обрабатывать `requests.exceptions.RequestException` (например, `ConnectTimeout`, `ReadTimeout`) и ошибки API Telegram (проверять `response.status_code` и `response.json().get('ok')`). Логировать ошибки.
- **Структура кода:** Создать новый файл `streamlit_app/telegram_service.py`.
    - В нем функция `get_telegram_token()` -> `Optional[str]`.
    - Функция `format_telegram_message(transaction_row: pd.Series) -> str`. Принимает строку DataFrame, возвращает HTML-строку. Включает логику экранирования и форматирования `<b>`.
    - Функция `send_telegram_alert(bot_token: str, chat_id: str, message_html: str) -> bool`. Возвращает `True` при успехе, `False` при ошибке.
- В `app.py` импортировать и использовать эти функции. Логику определения, нужно ли отправлять алерт, и управление `alert_history` оставить в `app.py` (например, в `_fetch_and_update_table` или новой вспомогательной функции).

---

## Потоки взаимодействия

1.  **Настройка:** Администратор задает `TELEGRAM_BOT_TOKEN` в окружении. Пользователь в `app.py` вводит Chat ID и включает алерты. Настройки сохраняются в `localStorage`.
2.  **Обновление данных:** Приложение получает новые транзакции (например, `_fetch_and_update_table`).
3.  **Проверка и Отправка:** Внутри `_fetch_and_update_table` (или вызванной из нее функции), для каждой транзакции проверяется `alert_history` по `TxID`. Для новых или неудавшихся (с учетом лимита попыток и времени) вызывается `telegram_service.send_telegram_alert`. Статус обновляется в `alert_history` в `localStorage`.
4.  **Отображение:** Функция `render_main_content` использует `alert_history` для формирования колонки "Статус Telegram" в `transactions_df` перед передачей в `st.dataframe`.
5.  **Обновление страницы (F5):** Настройки (Chat ID, вкл/выкл) и `alert_history` восстанавливаются из `localStorage`, статусы в таблице отображаются корректно.

---

## Критерии готовности

- Telegram Bot Token безопасно загружается из окружения; UI алертов деактивируется, если токен отсутствует.
- Настройки (Chat ID, вкл/выкл) корректно сохраняются/загружаются из `localStorage`.
- Новые транзакции (с валидным `TxID`) инициируют отправку алертов (если включено).
- В таблице корректно отображается **текстовый статус** отправки (формат: `✅/⏳/❌/끄/➖`, номер попытки, время), используя данные из `localStorage`, связанные по `TxID`.
- Механизм повторных попыток (до 5 раз с интервалом ~1 мин при обновлениях данных) реализован и работает.
- История алертов (словарь `tx_hash` -> статус, последние ~100 записей, с ротацией) сохраняется/загружается из `localStorage`.
- Ошибки сети и API Telegram корректно обрабатываются, логируются, статус в истории обновляется на "error".
- Формат сообщения, HTML-экранирование и ссылка на Arkham соответствуют требованиям.
- Логика Telegram (получение токена, форматирование, отправка) вынесена в `streamlit_app/telegram_service.py`.

--- 