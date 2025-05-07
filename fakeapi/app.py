from fastapi import FastAPI
import time
import json
import uvicorn


app = FastAPI()

with open("llmindex","w") as f:
    f.write("0")
with open("fakedata.jsonl", "r",encoding="utf-8-sig") as f:
    lines = f.readlines()

@app.get("/fakellm")
def increment_index():
    # 读取当前索引
    with open("llmindex", "r") as f:
        index = int(f.read())
    time.sleep(2)  # 等待2秒
    index += 1     # 索引自增
    # 写回文件
    with open("llmindex", "w") as f:
        f.write(str(index))
    # 返回对应行内容，去除首尾空白
    return json.loads(lines[index].strip())

if __name__ == "__main__":
    uvicorn.run( 
        app="app:app",
        host="127.0.0.1",
        port=8088,
        workers=1
    )

