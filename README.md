# MeloTTS API

基于 **MeloTTS** 模型的语音合成API服务，提供OpenAI兼容接口和WebSocket实时流式传输。

## 功能特性

- ✅ **文本转语音 (TTS)**：支持中文、英文及中英文混合文本合成
- ✅ **智能音色选择**：中文文本自动使用 ZH 模型，英文文本自动使用 EN 模型
- ✅ **中英双语音色**：alloy 音色始终使用 ZH 模型，完美支持中英文混合朗读
- ✅ **多英文口音**：支持美式、英式、澳大利亚等多种英文口音
- ✅ **OpenAI兼容接口**：标准 `/v1/audio/speech` 接口
- ✅ **传统接口**：GET `/tts` 和 POST `/tts_post`
- ✅ **WebSocket流式接口**：句子级流式音频传输，支持长文本分句处理
- ✅ **Markdown支持**：自动清洗Markdown格式，删除代码块和公式
- ✅ **特殊符号处理**：数学符号（×÷=≠）、单位符号（%℃℉）、货币符号
- ✅ **智能文本处理**：Markdown 清洗、特殊符号转换

## 快速开始

### 1. 安装依赖

```bash
# 使用现有的 conda 环境
conda activate xiaozhi-esp32-server

# 或安装依赖（如果需要）
pip install -r requirements.txt
```

### 2. 启动服务

#### 方式一：双击批处理文件
```
双击 start_service.bat
```

#### 方式二：命令行启动
```bash
conda activate xiaozhi-esp32-server
uvicorn api:api --host 0.0.0.0 --port 9880 --reload
```

### 3. 测试接口

#### Web界面测试
- Swagger UI: http://localhost:9880/docs
- WebSocket测试: 在浏览器中打开 `test_websocket.html`

#### curl命令测试
```bash
curl -X POST "http://localhost:9880/v1/audio/speech" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "tts-1",
    "input": "你好，这是一个测试。",
    "voice": "alloy",
    "response_format": "wav"
  }' \
  --output test.wav
```

## 音色列表

### 音色映射表

| OpenAI名称 | MeloTTS 模型 | Speaker ID | 说明 |
|-----------|-------------|-----------|------|
| **alloy** | ZH | 1 | 🌟 **中英双语** - 始终使用 ZH 模型，完美支持中英文混合 |
| echo | EN | EN-US (0) | 美式英语 |
| fable | EN | EN-BR (1) | 英式英语（巴西/英国变体） |
| onyx | EN | EN-Default (4) | 默认英语口音 |
| nova | EN | EN-US (0) | 美式英语 |
| shimmer | EN | EN-AU (3) | 澳大利亚英语 |

### 智能音色选择

API 会根据输入文本自动选择最佳模型：

- **中文文本** → 自动使用 ZH 模型（speaker_id=1）
- **英文文本** → 自动使用 EN 模型，根据选择的音色使用对应口音
- **alloy 音色** → 始终使用 ZH 模型（无论中英文）

### 英文口音说明

| 口音 | 音色 | 特点 |
|------|------|------|
| 美式英语 (EN-US) | echo, nova | 美国通用口音 |
| 英式英语 (EN-BR) | fable | 英国/巴西变体 |
| 澳大利亚英语 (EN-AU) | shimmer | 澳大利亚口音 |
| 默认英语 (EN-Default) | onyx | 标准英语口音 |

### 使用建议

- 如需**中英混合朗读**，请使用 `alloy` 音色
- 如需**特定英文口音**，选择对应的音色名称
- 如不确定，`onyx` 提供标准的默认英语口音

## API 接口

### OpenAI 兼容接口

**POST** `/v1/audio/speech`

请求体：
```json
{
  "model": "tts-1",
  "input": "你好，这是一个测试。",
  "voice": "alloy",
  "response_format": "wav",
  "speed": 1.0
}
```

参数说明：
- `model`: 模型名称（任意字符串，兼容OpenAI格式）
- `input`: 要合成的文本
- `voice`: 音色名称（支持OpenAI音色名，见上方音色列表）
- `response_format`: 音频格式（wav/mp3，默认wav）
- `speed`: 语速（0.25-4.0，默认1.0）
- `input_format`: 输入格式（可选）
  - `"plain"` - 纯文本（默认）
  - `"markdown"` - Markdown格式（自动清洗格式符号）

### 传统 GET 接口

**GET** `/tts?text=你好&voice=alloy&speed=1.0`

### 传统 POST 接口

**POST** `/tts_post`

```json
{
  "text": "你好世界",
  "voice": "alloy",
  "speed": 1.0,
  "input_format": "plain"
}
```

### WebSocket 流式接口

**WebSocket** `/ws/tts`

连接URL：
```
ws://localhost:9880/ws/tts
```

发送消息：
```json
{
  "text": "你好，这是一个WebSocket测试。",
  "voice": "alloy",
  "speed": 1.0,
  "input_format": "plain"
}
```

参数说明：
- `text`: 要合成的文本（支持Markdown格式）
- `voice`: 音色名称
- `speed`: 语速（0.25-4.0）
- `input_format`: 输入格式（`"plain"` 或 `"markdown"`）

响应：
- JSON消息：
  - `{"type": "sentence_start", "index": 0, "text": "...", "voice": "..."}` - 句子开始
  - `{"type": "sentence_end", "index": 0}` - 句子结束
  - `{"type": "done", "total_sentences": N, "total_chunks": M, "total_bytes": X}` - 完成
  - `{"type": "error", "message": "错误信息"}` - 错误
- 二进制消息：WAV音频块

**优点**：
- 更低的延迟，开始播放更快
- 内存占用更小
- 支持长文本实时合成（自动分句处理）
- 适合连续对话场景

## 测试工具

### Python WebSocket 测试

#### 简单测试（不播放音频）
```bash
python test_websocket_simple.py
```

#### 音频播放测试
```bash
# 需要安装额外依赖
pip install sounddevice soundfile
python test_websocket_audio.py
```

### 浏览器测试

在浏览器中直接打开 `test_websocket.html` 文件，即可使用可视化界面测试WebSocket接口。

## 示例代码

### Python 客户端（HTTP）

```python
import requests

response = requests.post(
    "http://localhost:9880/v1/audio/speech",
    json={
        "model": "tts-1",
        "input": "你好，这是一个测试。",
        "voice": "alloy",
        "response_format": "wav"
    }
)

with open("output.wav", "wb") as f:
    f.write(response.content)
```

### Python 客户端（WebSocket）

```python
import asyncio
import websockets
import json
import io
import soundfile as sf

async def stream_tts(text, voice="alloy", speed=1.0):
    uri = "ws://localhost:9880/ws/tts"

    async with websockets.connect(uri) as ws:
        # 发送请求
        await ws.send(json.dumps({
            "text": text,
            "voice": voice,
            "speed": speed
        }))

        # 接收音频流
        chunk_count = 0
        while True:
            message = await ws.recv()

            # 检查消息类型（二进制音频或JSON文本）
            if isinstance(message, bytes):
                # 音频数据（二进制）
                chunk_count += 1
                audio, sr = sf.read(io.BytesIO(message))
                # 播放或处理音频...
                print(f"收到音频块 #{chunk_count}: {len(message)} 字节")
            else:
                # JSON文本消息
                msg = json.loads(message)
                if msg.get("type") == "done":
                    print(f"完成: {msg.get('chunks')} 个音频块")
                    break
                elif msg.get("type") == "error":
                    print(f"错误: {msg.get('message')}")
                    break

# 运行
asyncio.run(stream_tts("你好，这是一个测试。"))
```

### JavaScript 客户端（浏览器）

```javascript
const ws = new WebSocket('ws://localhost:9880/ws/tts');
const audioContext = new AudioContext();

ws.onopen = () => {
    // 发送请求
    ws.send(JSON.stringify({
        text: "你好，这是一个测试。",
        voice: "alloy",
        speed: 1.0
    }));
};

ws.onmessage = async (event) => {
    const data = event.data;

    // 检查是否是JSON消息
    try {
        const msg = JSON.parse(data);
        if (msg.type === 'done') {
            console.log('完成!');
        }
        return;
    } catch {}

    // 播放音频
    const audioBuffer = await audioContext.decodeAudioData(await data.arrayBuffer());
    const source = audioContext.createBufferSource();
    source.buffer = audioBuffer;
    source.connect(audioContext.destination);
    source.start();
};
```

## 配置说明

### 跨平台支持

本 API 支持 **Windows、Linux (Ubuntu)、macOS** 平台运行。

#### Windows 启动

```bash
# 方式一：双击批处理文件
start_service.bat

# 方式二：命令行启动
conda activate xiaozhi-esp32-server
uvicorn api:api --host 0.0.0.0 --port 9880 --reload

# PowerShell（指定设备）
$env:MeloTTS_DEVICE="cuda:0"
uvicorn api:api --host 0.0.0.0 --port 9880 --reload
```

#### Ubuntu/Linux 启动

```bash
# 激活环境
conda activate xiaozhi-esp32-server

# 启动服务
uvicorn api:api --host 0.0.0.0 --port 9880 --reload

# 指定 GPU 设备
MeloTTS_DEVICE=cuda:0 uvicorn api:api --host 0.0.0.0 --port 9880 --reload

# 后台运行（nohup）
nohup uvicorn api:api --host 0.0.0.0 --port 9880 --reload > api.log 2>&1 &

# 后台运行（systemd）
# 创建 /etc/systemd/system/melotts.service
# [Unit]
# Description=MeloTTS Service
# After=network.target
# [Service]
# User=your_user
# WorkingDirectory=/path/to/project
# ExecStart=/path/to/conda/envs/xiaozhi-esp32-server/bin/uvicorn api:api --host 0.0.0.0 --port 9880
# [Install]
# WantedBy=multi-user.target
# systemctl enable melotts
# systemctl start melotts
```

#### macOS 启动

```bash
# 激活环境
conda activate xiaozhi-esp32-server

# 启动服务（自动使用 MPS Apple Silicon）
uvicorn api:api --host 0.0.0.0 --port 9880 --reload
```

#### 设备环境变量

通过 `MeloTTS_DEVICE` 环境变量控制计算设备：

| 值 | 说明 | 适用平台 |
|----|------|----------|
| `auto`（默认）| 自动检测（CUDA > MPS > CPU） | 所有平台 |
| `cuda:0` | 使用 CUDA GPU 0 | Windows/Linux |
| `cuda:1` | 使用 CUDA GPU 1 | Windows/Linux（多 GPU）|
| `cpu` | 使用 CPU | 所有平台 |
| `mps` | 使用 Apple Silicon MPS | macOS |

示例：
```bash
# Linux
MeloTTS_DEVICE=cuda:1 uvicorn api:api --host 0.0.0.0 --port 9880

# Windows PowerShell
$env:MeloTTS_DEVICE="cpu"; uvicorn api:api --host 0.0.0.0 --port 9880

# macOS
uvicorn api:api --host 0.0.0.0 --port 9880  # 自动使用 MPS
```

### 端口配置

默认端口：`9880`

修改端口（编辑 `start_service.bat` 或命令行）：
```bash
uvicorn api:api --host 0.0.0.0 --port <新端口> --reload
```

### 音频格式

- 采样率：24000 Hz（输出时自动从 44100Hz 重采样）
- 格式：WAV (PCM 16-bit) 或 MP3
- 比特率：自动

### 双模型架构

服务启动后会自动加载两个 MeloTTS 模型：

1. **ZH 模型**：处理中文和中英混合文本
2. **EN 模型**：处理英文文本，支持多种口音

模型采用懒加载方式，在第一次请求时自动加载，无需等待启动。

## 智能文本处理

API会自动处理以下情况：

1. **Markdown 清洗**：自动去除格式符号
2. **特殊符号处理**：数学符号、单位符号、货币符号转换
3. **中英文混合**：MeloTTS ZH 模型天然支持中英文混合朗读

### Markdown 格式支持

设置 `input_format: "markdown"` 后，API会自动清洗Markdown格式：

- **标题**：`# 标题` → `标题`
- **粗体/斜体**：`**粗体**` → `粗体`
- **列表**：`- 项目` → `项目`
- **链接**：`[文本](url)` → `文本`
- **代码块**：完全删除（不朗读代码）
- **公式**：`$E=mc^2$` → `公式`

示例：
```bash
curl -X POST "http://localhost:9880/v1/audio/speech" \
  -H "Content-Type: application/json" \
  -d '{
    "input": "# 欢迎\n\n这是**粗体**，包含3×4=12。",
    "voice": "alloy",
    "input_format": "markdown"
  }' \
  --output output.wav
```

### 特殊符号处理

自动将特殊符号转换为可朗读的文字：

**数学符号**：
- `3×4` → `3乘以4`
- `10÷2` → `10除以2`
- `a=b` → `a等于b`
- `a≠b` → `a不等于b`
- `a<b` → `a小于b`

**单位符号**：
- `50%` → `百分之50`
- `25℃` → `25摄氏度`
- `77℉` → `77华氏度`

**货币符号**：
- `$100` → `100美元`
- `₽1000` → `1000卢布`
- `₹500` → `500卢比`
- `₩10000` → `10000韩元`

## 常见问题

### 1. 服务启动失败

- 确认 conda 环境已激活：`conda activate xiaozhi-esp32-server`
- 检查端口是否被占用：`netstat -ano | findstr 9880`
- 查看错误日志

### 2. WebSocket 连接失败

- 确认服务正在运行
- 检查防火墙设置
- 确认WebSocket URL正确：`ws://localhost:9880/ws/tts`

### 3. 音频播放问题

- 确认音频输出设备正常
- 检查音频格式是否为WAV
- 尝试降低语速

### 4. 中英文混合问题

- 使用 `alloy` 音色可完美支持中英文混合朗读
- 中文文本会自动使用 ZH 模型
- 英文文本会自动使用 EN 模型并选择对应口音

### 5. 英文口音不一致问题

- 确保使用正确的音色名称
- echo/nova = 美式英语
- fable = 英式英语
- shimmer = 澳大利亚英语
- onyx = 默认英语口音

## 性能优化建议

1. **WebSocket流式**：长文本使用WebSocket接口，实时性更好
2. **并发控制**：建议同时请求数不超过5个
3. **缓存音频**：常用短语可以缓存音频文件

## 文件说明

```
kokoro/
├── api.py                      # 主API文件
├── markdown_cleaner.py         # Markdown清洗模块
├── sentence_splitter.py        # 句子分割模块
├── en_replace_number.py        # 特殊符号处理
├── start_service.bat           # Windows启动脚本
├── start_service.vbs           # 后台启动脚本
├── requirements.txt            # Python依赖
├── test_websocket_simple.py    # WebSocket简单测试
├── test_websocket_audio.py     # WebSocket音频测试
├── test_markdown_tts.py        # Markdown TTS测试
├── test_websocket.html         # 浏览器测试页面
└── MeloTTS/                    # MeloTTS 源码目录
    └── test_melo.py            # MeloTTS 测试示例
```

## 技术栈

- **Web框架**: FastAPI
- **ASGI服务器**: Uvicorn
- **深度学习**: PyTorch
- **TTS模型**: MeloTTS (MIT & MyShell.ai)
- **音频处理**: SoundFile
- **WebSocket**: FastAPI WebSocket

## 许可证

本项目基于 MeloTTS 模型构建。MeloTTS 使用 MIT 许可证。

## 支持

如有问题，请检查：
1. FastAPI 文档：http://localhost:9880/docs
2. 健康检查接口：http://localhost:9880/health
3. 日志输出

## 更新日志

### v2.1 (当前版本) ⭐ 智能音色选择
- ✅ 新增双模型架构（ZH + EN）
- ✅ 智能语言检测：中文文本自动使用 ZH 模型
- ✅ 英文口音选择：英文文本自动使用 EN 模型并选择对应口音
- ✅ alloy 音色升级为中英双语专用音色
- ✅ 支持美式、英式、澳大利亚等多种英文口音
- ✅ 修复 speaker_id 类型问题

### v2.0
- ✅ 迁移到 MeloTTS 模型
- ✅ 统一使用 ZH 模型，天然支持中英文混合
- ✅ 简化音色系统
- ✅ 保留所有 API 接口兼容性
- ✅ 句子级 WebSocket 流式传输

### v1.2
- ✅ 新增 Markdown 格式支持（自动清洗格式符号）
- ✅ 新增特殊符号处理（数学、单位、货币符号）
- ✅ 新增智能音色选择（中文自动切换双语音色）
- ✅ 新增长文本分句处理（WebSocket逐句流式传输）
- ✅ 新增句子级事件通知（sentence_start/sentence_end）
- ✅ 扩展请求模型（input_format参数）

### v1.1
- ✅ 新增 WebSocket 流式 TTS 接口
- ✅ 修复硬编码路径问题
- ✅ 添加队列管理机制
- ✅ 提供多种测试工具
- ✅ 改进日志系统

### v1.0
- OpenAI 兼容接口
- 传统 HTTP 接口
- 智能文本处理
- 多音色支持
