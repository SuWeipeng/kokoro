# Kokoro TTS API

基于 **Kokoro TTS** 模型的语音合成API服务，提供OpenAI兼容接口和WebSocket实时流式传输。

## 功能特性

- ✅ **文本转语音 (TTS)**：支持中文和英文文本合成
- ✅ **多种音色**：8种预置音色（4女声、2男声、2双语声）
- ✅ **OpenAI兼容接口**：标准 `/v1/audio/speech` 接口
- ✅ **传统接口**：GET `/tts` 和 POST `/tts_post`
- ✅ **WebSocket流式接口**：实时流式音频传输，支持长文本分句处理
- ✅ **智能文本处理**：数字转换、电话号码、IP地址处理
- ✅ **双语音色**：支持中英文混合文本自动切换
- ✅ **Markdown支持**：自动清洗Markdown格式，删除代码块和公式
- ✅ **特殊符号处理**：数学符号（×÷=≠）、单位符号（%℃℉）、货币符号
- ✅ **智能音色选择**：中文文本自动切换到双语音色

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

| OpenAI名称 | Kokoro音色文件 | 类型 | 说明 |
|-----------|---------------|------|------|
| alloy | bf_vale.pt | 双语声 | ✅ 中英文自动切换 |
| echo | am_adam.pt | 男声 | 英文 |
| fable | af_sol.pt | 女声(双语) | ✅ 中英文自动切换 |
| onyx | am_michael.pt | 男声 | 英文 |
| nova | af_sarah.pt | 女声 | 英文 |
| shimmer | af_maple.pt | 女声(双语) | ✅ 中英文自动切换 |

**额外可用的音色**（直接使用Kokoro名称）：
- `af_heart` - 女声
- `af_nicole` - 女声
- `af_sarah` - 女声
- `am_adam` - 男声
- `am_michael` - 男声
- `af_maple` - 双语声（推荐用于中英文混合）
- `af_sol` - 双语声（推荐用于中英文混合）
- `bf_vale` - 双语声（推荐用于中英文混合）

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
- `voice`: 音色名称（支持OpenAI音色名或Kokoro音色名）
- `response_format`: 音频格式（wav/mp3，默认wav）
- `speed`: 语速（0.25-4.0，默认1.0）
- `input_format`: 输入格式（可选）
  - `"plain"` - 纯文本（默认）
  - `"markdown"` - Markdown格式（自动清洗格式符号）

### 传统 GET 接口

**GET** `/tts?text=你好&voice=af_heart&speed=1.0`

### 传统 POST 接口

**POST** `/tts_post`

```json
{
  "text": "你好世界",
  "voice": "af_heart",
  "speed": 1.0,
  "input_format": "plain"
}
```

### WebSocket 流式接口 ⭐ NEW

**WebSocket** `/ws/tts`

连接URL：
```
ws://localhost:9880/ws/tts
```

发送消息：
```json
{
  "text": "你好，这是一个WebSocket测试。",
  "voice": "af_heart",
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
- 智能音色选择（中文自动切换双语音色）
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

async def stream_tts(text, voice="af_heart", speed=1.0):
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
        voice: "af_heart",
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

### 端口配置

默认端口：`9880`

修改端口（编辑 `start_service.bat`）：
```bash
uvicorn api:api --host 0.0.0.0 --port <新端口> --reload
```

### 音频格式

- 采样率：24000 Hz
- 格式：WAV (PCM 16-bit)
- 比特率：自动

## 智能文本处理

API会自动处理以下情况：

1. **数字转文字**：`123` → `一百二十三`
2. **电话号码**：`138-1234-5678` → `一三八一二三四五六七八`
3. **IP地址**：`192.168.1.1` → `一百九十二点一百六十八点一点一`
4. **中英文判断**：自动检测文本类型，选择合适的处理方式
5. **数字范围**：`1-10` → `1到10`

### Markdown 格式支持 ⭐ NEW

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

### 特殊符号处理 ⭐ NEW

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

### 智能音色选择 ⭐ NEW

当检测到文本包含中文时，会自动切换到双语音色：

- 用户指定 `am_adam` (男声) + 中文文本 → 自动使用 `af_maple` (双语音色)
- 避免用纯英文音色朗读中文导致效果差
- 服务器日志会记录音色调整信息

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

- 使用双语音色：`af_maple`, `af_sol`, `bf_vale`
- 这些音色使用语言代码 `'z'`，可以智能处理中英文混合文本

## 性能优化建议

1. **使用双语音色**：中英文混合文本使用 `af_maple` 等双语音色
2. **WebSocket流式**：长文本使用WebSocket接口，实时性更好
3. **并发控制**：建议同时请求数不超过5个
4. **缓存音频**：常用短语可以缓存音频文件

## 文件说明

```
kokoro/
├── api.py                      # 主API文件
├── markdown_cleaner.py         # Markdown清洗模块 ⭐ NEW
├── sentence_splitter.py        # 句子分割模块 ⭐ NEW
├── en_replace_number.py        # 数字和特殊符号处理
├── start_service.bat           # Windows启动脚本
├── start_service.vbs           # 后台启动脚本
├── requirements.txt            # Python依赖
├── test_websocket_simple.py    # WebSocket简单测试
├── test_websocket_audio.py     # WebSocket音频测试
├── test_markdown_tts.py        # Markdown TTS测试 ⭐ NEW
├── test_websocket.html         # 浏览器测试页面
├── models_zh/                  # 模型文件目录
│   ├── config.json
│   └── kokoro-v1_1-zh.pth
└── voices/                     # 音色文件目录
    ├── af_heart.pt
    ├── am_adam.pt
    └── ...
```

## 技术栈

- **Web框架**: FastAPI
- **ASGI服务器**: Uvicorn
- **深度学习**: PyTorch
- **TTS模型**: Kokoro
- **音频处理**: SoundFile
- **WebSocket**: FastAPI WebSocket

## 许可证

本项目基于 Kokoro TTS 模型构建。请遵守相关模型的使用条款。

## 支持

如有问题，请检查：
1. FastAPI 文档：http://localhost:9880/docs
2. 健康检查接口：http://localhost:9880/health
3. 日志输出

## 更新日志

### v1.2 (当前版本) ⭐ Markdown TTS
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
