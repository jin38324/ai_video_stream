现在已经做出来的包括个模块（能跑，但是需要调优）：

- 3.2：将文件已上传信息发送入消息队列，模拟的场景是每5秒1个视频块，上传到对象存储后发送消息的streaming，消息内容包括设备号、开始时间戳、存储桶信息等（使用本地文件模拟消息队列，没有实际调用streaming服务）；

- 4-6：从队列中获取消息，得到每个文件的信息（本地文件读取模拟streaming）；

- 7：调用大模型分析视频，过程包括：
  -  从消息中拼接对象存储URL（使用预授权链接）；
  -  从URL读取视频文件，计算fps等基本信息；
  -  每N帧抽取1帧，计算时间戳（可配置）；
  - 使用算法对比每一帧和前一个关键帧的相似度，小于阈值的作为关键帧；
  - 关键帧发送到大模型，获得事件描述、事件分类、触发警报的置信度（使用模拟数据，因为小模型的结果不能支持后面的分析和告警过程）；
  - 帧信息、缩略图、LLM的响应存储为关系型表（本地sqlite模拟），后面需要接事件分析，还没有完成。


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