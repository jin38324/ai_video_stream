import streamlit as st
import threading
import time
import websocket
import queue
from streamlit.runtime.scriptrunner import add_script_run_ctx
import pandas as pd
import json
import base64, io
from datetime import datetime, timezone
from utils.models import (
    timestamp_to_str
    )


WEBSOCKET_URL = "ws://localhost:16532/ws/notify"


st.set_page_config(layout="wide")



# Streamlit UI setup
st.title("SenseAct AI 实时感知")


# --- Streamlit Session State Initialization ---
# Initialize session state variables
if "message_queue" not in st.session_state:
    st.session_state.message_queue = queue.Queue(maxsize=10)

if "messages" not in st.session_state:
    st.session_state.messages = []

if "websocket_thread" not in st.session_state:
    st.session_state.websocket_thread = None

# ---------------------------------------------

def on_message(ws, message):
    data = json.loads(message)
    print(data)
    #st.session_state.message_queue.put(data)
    st.session_state.messages.append(data)

def on_error(ws, error):
    print(f"WebSocket Error: {error}")

def on_close(ws, close_status_code, close_msg):
    print("WebSocket connection closed")

def on_open(ws):
    ws.send('{"userKey": "<YOUR_KEY>"}')

def run_websocket():
    ws = websocket.WebSocketApp(
        WEBSOCKET_URL,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    ws.on_open = on_open    
    print("WebSocket thread started")
    ws.run_forever()


if st.session_state.websocket_thread is None or not st.session_state.websocket_thread.is_alive():
    print("Starting WebSocket connection...")
    websocket_thread = threading.Thread(target=run_websocket, daemon=True)
    add_script_run_ctx(websocket_thread)
    websocket_thread.start()
    st.session_state.websocket_thread = websocket_thread


def decode_base64_image(b64_str: str) -> bytes:
    # 如果包含 data URI 前缀，就去掉它
    if ',' in b64_str:
        b64_str = b64_str.split(',', 1)[1]
    # 解码成原始二进制
    return base64.b64decode(b64_str)  # :contentReference[oaicite:0]{index=0}


LEVELS = {
    "ok":"✅",
    "warning":"⚠️",
    "danger":"🚨",
    }

def set_level(triger_alarm):
    level = "ok"
    if triger_alarm > 0.5:
        level = "warning"
    if triger_alarm > 0.8:
        level = "danger"
    # stars = LEVELS["star"] * int(triger_alarm * 10/2)
    return LEVELS[level]

def render(messages):
    for i,msg in enumerate(messages):
        
        # 卡片容器
        with st.container(border=True):        
            # 两列布局：缩略图 + 描述
            col1, col2 = st.columns([1, 3], gap="small")
            with col1:
                if msg.get("thumbnail"):
                    raw_bytes = decode_base64_image(msg["thumbnail"])
                    bytes_io = io.BytesIO(raw_bytes) 
                    st.image(bytes_io, width=400, caption=None) 
                else:
                    st.markdown("— 无缩略图 —")
            with col2:
                if msg.get("type") == "event":
                    ts = timestamp_to_str(msg['timestamp'],style="simple")
                    st.markdown(f'<span class="timestamp">{ts}</span>', unsafe_allow_html=True)
                    level = set_level(msg["triger_alarm"])
                    title = msg["event_catagory"]
                    st.markdown(f"{level} **{title}**")
                    st.markdown(msg["description"])
                
                elif msg.get("type") == "summary":
                    #st.markdown("<div class='summary'>",unsafe_allow_html=True)
                    ts_start = timestamp_to_str(msg['start_timestamp'],style="simple")
                    ts_end = timestamp_to_str(msg['end_timestamp'],style="simple")
                    st.markdown(f'<span class="timestamp">{ts_start}</span> -- <span class="timestamp">{ts_end}</span>',
                                 unsafe_allow_html=True)
                    title = msg["title"]
                    st.markdown(f"**{title}**")
                    st.markdown(msg["description"])
                
                    with st.popover("查看事件详情"):
                        for ev in msg["events"]:
                            ev_ts = timestamp_to_str(ev["timestamp"],style="simple")
                            level = set_level(ev["triger_alarm"])
                            title = ev["event_catagory"]
                            st.markdown(f"")
                            st.markdown(f"{ev_ts} — {level} **{title}** {ev['description']}")
                    #st.markdown("</div>",unsafe_allow_html=True)
                else:
                    st.markdown(msg["description"])



# st.json(st.session_state.messages)

# while True:
# # while not st.session_state.message_queue.empty():
#     while st.session_state.messages:
#         #message = st.session_state.message_queue.get()
#         #st.session_state.messages.append(message)
#         # Function to render messages in time order

with st.container():
    render(st.session_state.messages)

time.sleep(2)

st.rerun()
    