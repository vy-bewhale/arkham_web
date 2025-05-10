import streamlit as st
from streamlit_local_storage import LocalStorage

localS = LocalStorage()

if "loaded_text" not in st.session_state:
    st.session_state.loaded_text = localS.getItem("savedText") or "Нет сохраненных данных"

st.title("Приложение с памятью браузера")

st.markdown(f"**Текущий сохраненный текст:** {st.session_state.loaded_text}")

user_input = st.text_input("Введите текст для сохранения:", value=st.session_state.loaded_text)

if st.button("Сохранить в localStorage"):
    localS.setItem("savedText", user_input)
    st.session_state.loaded_text = user_input
    st.success("Текст сохранен!")

st.markdown("""
### Инструкции:
1. Введите текст в поле ввода.
2. Нажмите "Сохранить в localStorage", чтобы сохранить текст.
3. Текст автоматически отобразится в разделе "Текущий сохраненный текст".
""") 