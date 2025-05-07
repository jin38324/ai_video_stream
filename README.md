# 项目概述

----

本文档全面概述了 AI 视频流分析系统。该系统旨在处理视频流，使用大型语言模型 (LLM) 分析内容，检测事件，生成摘要并提供实时通知。它采用模块化架构，包含用于视频处理、事件摘要、API 通信和 Web 用户界面的组件。

该系统使用 Python 构建，并使用 FastAPI 作为 API 后端，Streamlit 作为 Web UI，SQLite 用于数据持久化（可替换为其它数据库）。在开发和测试方面，它集成了 LLM、Redis 和 OCI Streaming 等外部服务的“虚拟”实现，从而允许在本地执行，而无需依赖实际的云资源。

### 核心功能：

- **视频提取：** 使用OCI对象存储，基于对视频进行切片的流机制模拟视频流输入。

- **帧提取与分析：** 从视频片段中提取关键帧，通过比较帧的相似性来减少冗余，确定关键帧。过滤后的关键帧由 LLM 处理，以识别事件、进行分类并评估警报级别。

- **事件检测与跟踪：** 存储检测到的事件信息，包括描述、类别和时间戳。使用类似 Redis 的本地存储来跟踪正在进行的事件窗口。

- **事件摘要：** 定期处理相关事件序列，以使用另一个 LLM 生成简洁的摘要。

- **实时通知：** 通过 WebSockets 向连接的客户端广播检测到的事件和摘要。

- **Web 用户界面：** 基于 Streamlit 的 UI 显示实时事件和摘要。

### 关键设计选择：


- **模块化：** 系统分为不同的组件（视频处理、摘要、API、UI），提高可维护性和关注点分离。


- **异步操作：** 用于`asyncio`I/O 密集型任务（如 API 调用和视频处理），​​从而提高性能。


- **本地开发重点：** 包含`fakeapi`、`fakeredis`和`fakestreaming`模块，无需实时云服务即可进行开发和测试，从而降低成本和设置复杂性。


- **可配置性：** 系统行为（例如帧分析间隔、LLM 参数和摘要逻辑）通过`config.py`文件进行管理。


- **LLM 驱动的分析：** 利用支持视觉的 LLM 理解视频内容，并利用自然语言 LLM 生成摘要。精心设计的题目将指导 LLM 的输出。


# 业务逻辑

## 实时视频事件分析器

### 1. 组件名称

实时视频事件分析器

### 2. 目的

该组件解决了需要监控安全摄像机的视频源、自动近乎实时地检测重大活动或变化并对这些事件进行分类的业务问题。它代表安全系统的“眼睛”，将原始视频转换为有关潜在火灾、入侵或其他用户定义事件等事件的可操作情报。

### 3. 主要职责

- **视频提取**：处理由传入消息（例如来自模拟流）识别的视频片段。
- **优化帧选择**：按配置的间隔从视频中提取帧，并根据与前一帧的视觉差异智能选择“关键帧”，减少冗余分析。规则：“仅分析显示显著视觉变化的帧。”
- **人工智能事件识别**：对每个关键帧使用大型语言模型 (LLM) 生成中文事件描述，将事件分类为预定义类别（如火灾、异常停留、入侵检测），并评估警报严重性（`trigger_alarm` 0.0–1.0）。
- **数据持久性**：将每个关键帧的时间戳、缩略图、AI 生成的描述、事件类别和警报级别存入结构化数据库。
- **实时警报**：检测到新事件时立即向事件通知发射器发送通知（包括事件详情和缩略图）。
- **事件状态跟踪**：维护每个设备和事件类别的事件开始和结束时间，便于后续汇总分析。

### 4. 工作流程/用例

#### 新的视频片段处理流程

- **触发器**：从流媒体服务接收到表示新视频片段可用的消息。

- **步骤**：
  1. 提取视频片段元数据（`VideoInfo`）。
  2. 访问视频内容（例如从 URL 下载）。
  3. 使用 `VideoProcessor` 以 `VideoConfig.FRAME_INTERVAL` 提取帧。
  4. 比较每帧与上一关键帧的相似度（`media._similarity_score`）。
  5. 若相似度低于 `VideoConfig.SIMILARITY_THRESHOLD` 或为第一帧，则为关键帧。
  6. 对于关键帧：
     - a. 生成缩略图（`media.ndarray_to_base64`）
     - b. 发送 base64 图像至 LLM（`utils.llm.video_analyzer`），使用 `LLMConfig.PROMPT` 提示生成描述、事件类别和警报级别。
     - c. 将 LLM 的 JSON 响应解析为 `LLMOutput`。
     - d. 保存完整的 `FrameInfo` 至 SQLite 数据库（通过 `DataProcessor`）。
     - e. 使用 `fakeredis` 更新设备与事件类别的缓存，记录时间戳。
     - f. 构建 `MessagePayload` 并通过 HTTP POST 发送至事件通知发射器的 `/sendjson` 端点。

- **结果**：识别、分类、存储关键事件并发送通知，系统准备分析下一个片段。

### 5. 输入和输出

- **输入**：
  - 视频片段元数据（`VideoInfo`）：设备 ID、时间戳、视频源 URL
  - 视频文件内容（例如 MP4）
  - 系统配置（如 `VideoConfig` 的帧间隔、相似度阈值、缩略图比例，`LLMConfig` 的 API 详情等）
  - 关键帧图像数据（用于相似度比较）

- **输出/效果**：
  - `FrameInfo`（含事件描述、类别、警报级别、缩略图）插入 `video_info` 数据库
  - 使用 `fakeredis` 更新事件时间范围（`min_time` / `max_time`）
  - 构建并发送 `MessagePayload` 至事件通知发射器
  - 生成日志条目记录每步处理详情

### 6. 依赖项

- `fakestreaming.get_streaming`：用于消费视频片段元数据（模拟）
- `cv2`：OpenCV 库，用于解码、帧提取、图像处理
- `utils.media`：图像转 base64、相似度计算（SSIM）
- `utils.llm`：与 LLM 交互进行图像分析
- `utils.models`：Pydantic 模型定义（`VideoInfo`, `LLMOutput`, `FrameInfo`, `MessagePayload`）
- `DataProcessor`（在 `video_server.py`）：处理 SQLite 数据库交互
- `fakeredis.LocalRedis`：模拟 Redis 缓存
- `requests`：发送 HTTP POST
- `config.py`：集中配置参数和提示词

### 7. 业务规则和约束

- **帧分析频率**：按 `VideoConfig.FRAME_INTERVAL`（如每 N 帧）处理。
- **关键帧判断标准**：若与上一关键帧的 SSIM < `VideoConfig.SIMILARITY_THRESHOLD`，则视为关键帧。
- **LLM 响应格式**：
  - `description`：简短中文事件描述
  - `event_category`：以下之一：
    - 火灾（Fire）
    - 异常停留（Abnormal Loitering）
    - 占领入侵检测（IntrusionDetection）
    - 人员跌倒（Person Fall）
    - 包裹投递（Package Delivery）
    - 无事件（No Event）
    - 其他（Other）
  - `trigger_alarm`：0–1 的浮点值，表示警报级别
- **缩略图生成**：按 `VideoConfig.SCALE` 缩放

### 8. 设计考虑

- **性能优化**：通过帧相似度检查减少 LLM 调用次数。
- **异步处理**：`extract_frames` 异步设计，减少 I/O 和 LLM 延迟影响。
- **模块化与可测试性**：依赖 `fakeredis`、`fakestreaming` 和 `fakeapi`，便于本地开发测试，`is_fake` 标志支持模拟与真实环境切换。
- **数据存储**：使用 SQLite 简化事件和帧信息管理。
- **配置集中管理**：如帧间隔、提示词、API 配置统一放在 `config.py`。



## 自动事件摘要器

### 1. 组件名称
- 自动事件摘要器

### 2. 目的
- 通过对一段时间内的相关事件进行分组并生成简洁的 AI 摘要，解决理解大量单独事件警报的问题。
- 提供一个“智能层”，生成更高级别的活动叙述，帮助用户快速掌握事件序列的本质，而无需筛选众多离散警报。

### 3. 主要职责
- **定期审查**：根据预定义的时间规则，定期扫描可汇总的事件序列。
- **事件聚合**：从数据库中检索特定设备和事件类别的数据（描述、时间戳），基于活动时间窗口进行缓存管理。
- **人工智能摘要**：
  - 构建上下文，汇总事件描述。
  - 利用大语言模型（LLM）生成摘要标题与详细中文叙述。
- **摘要持久性**：将摘要内容（标题、时间范围、事件类别、缩略图）存储至专用数据库表中。
- **水印机制**：更新缓存，防止已汇总事件再次被包含进新的摘要中。
  - 规则：事件一旦被汇总，其组成事件不得重复参与同类别的摘要。

### 4. 工作流程 / 用例

#### 定期总结周期：
- **触发器**：`main_sum.py` 调度器定期触发每个设备的汇总。
- **步骤**：
  1. 从 `fakeredis` 缓存中读取每个设备事件类别的时间窗口（`min_time`, `max_time`）。
  2. 判断是否达到汇总条件：
     - `max_time` 距当前时间超过 `SummaryConfig.MAX_GAP_LENGTH`。
     - 时间窗口持续时间超过 `SummaryConfig.MAX_TIME_LENGTH`。
  3. 如果触发汇总：
     - `EventDataProcessor` 提取 `video_info` 中对应时间范围内的事件（描述、时间戳）。
     - 如果存在事件，使用 `EventProcessor.llm_summary`：
       - 拼接事件描述构建上下文。
       - 调用 LLM API（`utils.llm_sum.call_api`），根据提示（`SummaryLLMConfig.PROMPT`）生成摘要。
     - 解析 JSON 响应。
     - 使用 `EventDataProcessor.save_events`：
       - 使用第一个事件的缩略图作为摘要缩略图。
       - 保存摘要标题、内容、时间、设备 ID、类别、缩略图至 `video_event_summary` 表。
     - 更新缓存，`min_time` = 当前 `max_time`，关闭当前窗口，开启新一轮监听。
- **结果**：生成并存储事件摘要，准备下一个时间窗口的总结。

### 5. 输入和输出

#### 输入：
- `device_id`
- SQLite 表 `video_info` 的事件数据（时间戳、描述、类别）
- 缓存中的事件时间窗口：`min_time`, `max_time`（由 `fakeredis` 提供）
- 系统配置：
  - `SummaryConfig`（最大时间间隔、最大持续时间）
  - `SummaryLLMConfig`（API 信息、提示、模型参数）

#### 输出：
- 将摘要记录写入 `video_event_summary` 表
- 更新缓存中的 `min_time`
- 生成日志记录总结过程

### 6. 依赖项
- `fakeredis.LocalRedis`：管理每个设备事件类别的时间窗口状态
- `EventDataProcessor`（在 `summary.py` 中）：处理数据库交互
- `utils.llm_sum`：与 LLM API 交互进行摘要生成
- `utils.models`：例如 `timestamp_to_str` 等实用函数
- `config.py`：配置参数与提示模板
- `main_sum.py`：定时运行汇总流程的主调度程序

### 7. 业务规则与约束
- **摘要触发条件**：
  - 某类别在 `SummaryConfig.MAX_GAP_LENGTH` 内无新事件
  - 或事件序列持续时间超过 `SummaryConfig.MAX_TIME_LENGTH`
- **事件分组**：按 `device_id` 和 `event_category` 聚合
- **LLM 输出要求**：
  - `title`：简短中文摘要标题
  - `event_summary`：详细中文事件叙述
- **缩略图**：使用序列中第一个事件的缩略图
- **无事件重叠**：缓存中更新 `min_time` 以防止重复汇总

### 8. 设计考虑
- **批处理性质**：不需实时处理，适用于定期总结
- **轮询机制**：使用基于时间的简单循环实现
- **LLM 依赖性**：摘要质量受 LLM 能力与提示清晰度影响
- **状态管理**：`fakeredis` 关键在于控制时间窗口和状态隔离
- **可测试性**：`utils.llm_sum.py` 中的 `is_fake` 标志用于启用测试模式

## 事件通知发射器

### 1. 组件名称

- 事件通知发射器

### 2. 目的

- 提供标准化的实时通信渠道，用于将检测到的视频事件（以及未来可能的摘要）广播到订阅的客户端（例如用户界面或其他监控系统）。
- 它充当系统的中央“喉舌”，确保及时传递警报。

### 3. 主要职责

- **客户端连接管理**：同时与多个客户端建立并维护 WebSocket 连接。  
  规则：“客户端必须连接到 `/ws/notify` 端点才能接收通知。”

- **消息提取 API**：提供内部 HTTP POST 端点（`/sendjson`），供其他系统组件（例如实时视频事件分析器）提交通知消息。  
  规则：“内部服务必须以 `MessagePayload` 格式发送通知。”

- **消息广播**：有效地将在摄取 API 上收到的任何消息转发给所有当前连接的 WebSocket 客户端。

### 4. 工作流程/用例

#### 客户端订阅通知

- **触发器**：客户端应用程序（例如 `webui.py`）启动与端点 `/ws/notify` 的 WebSocket 连接。
- **步骤**：
  1. FastAPI 应用程序（`api.py`）通过处理程序接受 WebSocket 连接 `websocket_endpoint`。
  2. 新的 WebSocket 客户端对象被添加到中央集合 `connected_websockets`。
  3. 连接保持活动状态，等待消息广播或客户端断开连接。
- **结果**：客户端成功连接并将收到系统广播的任何后续通知。

#### 系统发布事件通知

- **触发器**：内部系统组件（例如 `VideoProcessor`）向 `/sendjson` 端点发送包含符合 `MessagePayload` 数据的 HTTP POST 请求。
- **步骤**：
  1. `api.py` 中的处理程序 `send_json_message` 接收 `MessagePayload`。
  2. 有效负载被序列化为 JSON 字符串。
  3. `send_message_to_clients` 函数遍历 `connected_websockets` 中的所有 WebSocket 对象。
  4. 对于每个客户端，尝试通过 `client.send_text()` 发送 JSON 消息。
  5. 如果客户端发送失败（如断开连接），该客户端将从 `connected_websockets` 中删除。
- **结果**：通知将广播至所有活动的 WebSocket 客户端。断开连接的客户端将被清理。

### 5. 输入和输出

- **输入**：
  - 来自客户端的 WebSocket 连接请求 `/ws/notify`。
  - 从其他内部服务通过 HTTP POST 请求发送的符合 `MessagePayload` 模型的 JSON 数据至 `/sendjson`。

- **输出/效果**：
  - 通过 WebSocket 向所有连接的客户端发送 JSON 格式的通知消息。
  - 管理 `connected_websockets` 集合（添加新连接、删除断开的连接）。
  - 客户端连接、断开连接和消息广播的日志条目。

### 6. 依赖项

- `fastapi` 库：用于创建 WebSocket 端点和 HTTP POST 端点。
- `uvicorn` ASGI 服务器：用于运行 FastAPI 应用程序。
- `utils.models.MessagePayload`：定义传入和传出通知消息的结构。
- `config.ServerConfig`：用于服务器托管配置（主机、端口）。

### 7. 业务规则和约束

- **通信协议**：主要使用 WebSocket 进行面向客户端的通知。
- **消息格式**：所有通知都遵循 `MessagePayload` 结构，包括以下字段：
  - `device_id`
  - `timestamp`
  - `type`
  - `event_catagory`
  - `description`
  - `thumbnail`
  - `triger_alarm`
- **单向流（针对客户端）**：WebSocket 端点专为服务器到客户端的推送通知而设计，不处理从客户端发送的消息（WebSocket 控制帧除外）。
- **内部 API**：`/sendjson` 端点仅供其他后端组件内部使用。

### 8. 设计考虑

- **可扩展性和并发性**：FastAPI 与 Uvicorn 支持异步操作，能高效处理大量并发 WebSocket 连接。
- **解耦**：Emitter 将通知生产者（如视频事件分析器）与消费者（客户端）解耦，生产者无需了解每个连接。
- **稳健性**：`send_message_to_clients` 功能包括错误处理，防止因某个客户端断开导致整个广播失败。
- **简单性**：使用简单集合（`connected_websockets`）管理活动连接。



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