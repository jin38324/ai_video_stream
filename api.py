import uvicorn 
import requests
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState
from typing import Optional, Dict, Any , List,Set
from utils.models import (
    MessagePayload
    )
from config import VideoConfig, ServerConfig

# FastAPI应用配置 
app = FastAPI(title="SenseAct AI 实时感知")

# 用于存储当前连接的 WebSocket 客户端
connected_websockets: Set[WebSocket] = set()

@app.websocket("/ws/notify")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket 端点，处理客户端连接和断开。
    后端只发送消息，不接收。
    """
    await websocket.accept()
    # 将新的连接添加到集合中
    connected_websockets.add(websocket)
    print(f"WebSocket accepted: {websocket}")

    try:
        # 这个循环是为了保持连接开放。因为我们只推送，所以这里只等待断开。
        # 实际上，你可以省略这个接收循环，但为了优雅地处理断开，保留它比较好。
        # 任何从客户端发来的消息都会触发 WebSocketDisconnect 异常。
        while True:
            # 后端不接收消息，所以我们只是等待任何客户端活动（例如断开）
            # 如果客户端发送消息，这里会捕获到并触发异常或处理
            # 但在这个例子中，我们只关注连接的保持和断开
            data = await websocket.receive_text()
            # Optional: Log received data if you ever wanted to inspect
            # print(f"Received data (will be ignored): {data}")

    except WebSocketDisconnect:
        # 客户端断开连接
        connected_websockets.remove(websocket)
        print(f"WebSocket disconnected: {websocket}")
    except Exception as e:
        # 处理其他可能的异常
        print(f"WebSocket error with {websocket}: {e}")
        if websocket in connected_websockets:
             connected_websockets.remove(websocket)




@app.post("/sendjson")
async def send_json_message(payload: MessagePayload):
    # 将 Pydantic 模型对象转换为字典，再转换为 JSON 字符串
    message_to_send = payload.model_dump_json()

    print(f"Attempting to send JSON message to {len(connected_websockets)} clients")
    # 异步地向所有连接的客户端发送消息
    await send_message_to_clients(message_to_send)

    return {"status": "JSON message sent", "data": message_to_send}

async def send_message_to_clients(message: str):
    """
    向所有连接的 WebSocket 客户端发送消息。
    """
    # 创建一个列表副本，以防在迭代时集合被修改（客户端断开）
    disconnected_clients = []
    for client in list(connected_websockets):
        try:
            # WebSocket 连接是异步的，使用 await 发送
            await client.send_text(message)
            print(f"Sent message to {client}")
        except RuntimeError as e:
            # 客户端可能已经断开，但在集合中还没移除
            print(f"Error sending to {client}: {e}. Marking for removal.")
            disconnected_clients.append(client)
        except Exception as e:
             print(f"Unexpected error sending to {client}: {e}. Marking for removal.")
             disconnected_clients.append(client)

    # 移除发送失败的客户端
    for client in disconnected_clients:
        if client in connected_websockets:
            connected_websockets.remove(client)
            print(f"Removed disconnected client {client}")


if __name__ == "__main__":
    uvicorn.run( 
        app="api:app",
        host=ServerConfig.HOST,
        port=ServerConfig.PORT,
        reload=ServerConfig.RELOAD,
        workers=ServerConfig.WORKERS
    )