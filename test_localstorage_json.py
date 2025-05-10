import streamlit as st
from streamlit_local_storage import LocalStorage
import json

# Инициализация LocalStorage
localS = LocalStorage()

# Инициализация сессионного состояния
if "loaded_text" not in st.session_state:
    st.session_state.loaded_text = localS.getItem("savedText") or "Нет сохраненных данных"
if "loaded_json" not in st.session_state:
    try:
        raw_json = localS.getItem("savedJson")
        st.session_state.loaded_json = json.loads(raw_json) if raw_json else {"message": "Нет сохраненных данных"}
    except Exception:
        st.session_state.loaded_json = {"message": "Нет сохраненных данных"}

# Заголовок приложения
st.title("Приложение с памятью браузера (текст + JSON)")

# --- Секция для текста ---
st.header("Сохранение текста")
st.markdown(f"**Текущий сохраненный текст:** {st.session_state.loaded_text}")
text_input = st.text_input("Введите текст для сохранения:", value=st.session_state.loaded_text, key="text_input")
if st.button("Сохранить текст в localStorage"):
    localS.setItem("savedText", text_input)
    st.session_state.loaded_text = text_input
    st.success("Текст сохранен!")

# --- Секция для JSON ---
st.header("Сохранение JSON")
json_input = st.text_area(
    "Введите данные в формате JSON:",
    value=json.dumps(st.session_state.loaded_json, indent=2, ensure_ascii=False),
    height=150,
    key="json_input"
)
if st.button("Сохранить JSON в localStorage"):
    try:
        json_data = json.loads(json_input)
        localS.setItem("savedJson", json.dumps(json_data, ensure_ascii=False))
        st.session_state.loaded_json = json_data
        st.success("JSON сохранен!")
    except json.JSONDecodeError:
        st.error("Ошибка: введите корректный JSON!")

st.markdown("**Текущий сохраненный JSON:**")
st.json(st.session_state.loaded_json)

st.markdown("""
### Инструкции:
1. **Для текста:**
   - Введите текст в поле ввода.
   - Нажмите "Сохранить текст в localStorage", чтобы сохранить текст.
   - Текст автоматически отобразится в разделе "Текущий сохраненный текст".

2. **Для JSON:**
   - Введите данные в формате JSON в текстовое поле.
   - Нажмите "Сохранить JSON в localStorage", чтобы сохранить JSON.
   - Данные отобразятся в разделе "Текущий сохраненный JSON".
""") 