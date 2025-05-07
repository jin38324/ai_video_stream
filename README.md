# 运行

## 启动GPU上的Qwen 模型（用于事件总结）

```
conda activate vllm
vllm serve Qwen/Qwen2.5-VL-3B-Instruct
```

## 启动fakellm（用于视频流分析）

在`fakeapi`目录下启动

```
python app.py
```

## 清除数据

编辑`data.db`

```
DELETE FROM video_info;
DELETE FROM video_event_summary;
```

## 启动事件写入

在主目录下运行

```
python fakestreaming/put_streaming.py
```

## 启动Websocket API

```
python api.py
```

## 启动视频流分析

在主目录下运行

```
python main.py
```

## 启动事件总结

在主目录下运行

```
python main_sum.py
```