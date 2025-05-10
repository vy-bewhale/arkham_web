# NOTE: This feature uses browser local storage! AKA it stores data on a viewer's
# machine. This may have privacy and compliance implications for your app. Be sure
# to take that into account with any usage.

import json
import streamlit as st
from streamlit_js import st_js

KEY_PREFIX = "st_localstorage_"

class StLocalStorage:
    def __getitem__(self, key: str):
        code = f"return localStorage.getItem('{KEY_PREFIX + key}');"
        result = st_js(code, key=f"get_{key}")
        if isinstance(result, list) and result and result[0] is not None:
            try:
                return json.loads(result[0])
            except Exception:
                return result[0]
        return None

    def __setitem__(self, key: str, value):
        value_json = json.dumps(value, ensure_ascii=False)
        code = f"localStorage.setItem('{KEY_PREFIX + key}', {json.dumps(value_json)}); return true;"
        st_js(code, key=f"set_{key}_{value_json}")

st_local_storage = StLocalStorage()

if __name__ == "__main__":
    st.set_page_config(layout="wide")
    st.title("StLocalStorage: Минимализм")
    key = st.text_input("Ключ")
    value = st.text_area("Значение (строка или JSON)")
    if st.button("Сохранить"):
        try:
            st_local_storage[key] = json.loads(value)
        except Exception:
            st_local_storage[key] = value
        st.success("Сохранено!")
    if key:
        st.write("Текущее значение:")
        st.json(st_local_storage[key]) 