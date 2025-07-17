
import streamlit as st
import jwt
import time
import os
from dotenv import load_dotenv

def show_metabase_dashboard(dashboard_id: int, height: int = 600, width: int = 1300):
    load_dotenv()

    url = os.getenv("METABASE_SITE_URL")
    key = os.getenv("METABASE_SECRET_KEY")

    payload = {
        "resource": {"dashboard": dashboard_id},
        "params": {},  # 필요한 경우 여기에 필터 추가
        "exp": round(time.time()) + (60 * 10)
    }

    token = jwt.encode(payload, key, algorithm="HS256")
    if isinstance(token, bytes):
        token = token.decode('utf-8')

    iframe_url = f"{url}/embed/dashboard/{token}?bordered=true&titled=true"


    print("KEY:", key)
    print(token)
    print(iframe_url)

    st.components.v1.iframe(iframe_url, height=height, width=width)
