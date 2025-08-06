import streamlit as st
from st_pages import add_page_title, get_nav_from_toml
import sys
import os

st.set_page_config(page_title="立体库控制系统", page_icon="🤖", layout="wide")

# If you want to use the no-sections version, this
# defaults to looking in .streamlit/pages.toml, so you can
# just call `get_nav_from_toml()`
nav = get_nav_from_toml(".streamlit/pages.toml")

pg = st.navigation(nav)

add_page_title(pg)

pg.run()