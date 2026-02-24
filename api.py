from fastapi import FastAPI, Query, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from kokoro.pipeline import KPipeline
from kokoro.model import KModel
from pydantic import BaseModel
from en_replace_number import NumberReplacer, SpecialSymbolProcessor
from markdown_cleaner import MarkdownCleaner
from sentence_splitter import SentenceSplitter
import os
import torch
import tqdm
import soundfile as sf
import numpy as np
import io
from typing import Literal, Optional
import tempfile
import uuid
import re
import asyncio
import json
from collections import deque
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

repo_id='kokoro_api'

# 在启动时添加检查
def check_files():
    required_files = [
        os.path.join("models_zh", "config.json"),
        os.path.join("models_zh", "kokoro-v1_1-zh.pth")
    ]

    for file_path in required_files:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Required file not found: {file_path}")
        print(f"Found: {file_path}")

check_files()

# 添加设备检查
def check_device():
    if torch.cuda.is_available():
        print(f"CUDA available: {torch.cuda.get_device_name()}")
        print(f"CUDA version: {torch.version.cuda}")
        return 'cuda'
    else:
        print("Using CPU")
        return 'cpu'

device = check_device()

try:
    kmodel = KModel(
        config=os.path.join("models_zh", "config.json"),
        model=os.path.join("models_zh", "kokoro-v1_1-zh.pth"),
        repo_id=repo_id
    ).to(device).eval()
except Exception as e:
    print(f"Model loading error: {e}")
    raise RuntimeError(f"Failed to load model: {e}")

# 多语言 pipeline 缓存
lang_pipelines = {}

en_pipeline = KPipeline(lang_code='a', repo_id=repo_id, model=False)
def en_callable(text):
    if text == 'Kokoro':
        return 'kˈOkəɹO'
    elif text == 'Sol':
        return 'sˈOl'
    return next(en_pipeline(text)).phonemes

def get_pipeline(lang_code):
    if lang_code in lang_pipelines:
        return lang_pipelines[lang_code]
    pipe = KPipeline(lang_code=lang_code, model=kmodel, repo_id=repo_id, en_callable=en_callable)
    lang_pipelines[lang_code] = pipe
    return pipe

# Queue management for TTS requests
class TTSQueueManager:
    """Manages TTS request queue to prevent concurrent access conflicts"""
    def __init__(self):
        self.queue = deque()
        self.processing = False
        self.max_queue_size = 100
        self.lock = asyncio.Lock()

    async def add_request(self, request_data: dict) -> bool:
        """Add a request to the queue"""
        async with self.lock:
            if len(self.queue) >= self.max_queue_size:
                logger.warning("Queue is full, rejecting request")
                return False
            self.queue.append(request_data)
            logger.info(f"Request added to queue. Queue size: {len(self.queue)}")
            return True

    async def get_next_request(self) -> Optional[dict]:
        """Get the next request from the queue"""
        async with self.lock:
            if self.queue:
                return self.queue.popleft()
            return None

    async def process_queue(self):
        """Process requests in the queue"""
        while True:
            request = await self.get_next_request()
            if request:
                self.processing = True
                try:
                    # Process the request - this will be handled by the WebSocket handler
                    yield request
                finally:
                    self.processing = False
            else:
                await asyncio.sleep(0.1)

    def get_queue_size(self) -> int:
        """Get current queue size"""
        return len(self.queue)

# Global queue manager
queue_manager = TTSQueueManager()

# 创建 FastAPI 应用
api = FastAPI(title="Kokoro TTS API with OpenAI Compatibility")

api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

replacer = NumberReplacer()

# 新增全局实例：Markdown 清洗、句子分割、特殊符号处理
markdown_cleaner = MarkdownCleaner()
sentence_splitter = SentenceSplitter()
symbol_processor = SpecialSymbolProcessor()

# 定义 Kokoro 声音到 OpenAI 风格的映射
VOICE_MAPPING = {
    # OpenAI voices -> Kokoro voices
    "alloy": "bf_vale",
    "echo": "am_adam", 
    "fable": "af_sol",
    "onyx": "am_michael",
    "nova": "af_sarah",
    "shimmer": "af_maple",
    
    # Extension voice names -> Kokoro voices (based on the extension docs)
    "am_adam": "am_adam",      # Adam (Alloy)
    "af_nicole": "af_nicole",  # Nicole (Ash) 
    "bf_emma": "bf_vale",      # Emma (Coral) - mapped to bf_vale
    "af_bella": "af_heart",    # Bella (Echo) - mapped to af_heart
    "af_sarah": "af_sarah",    # Sarah (Fable)
    "bm_george": "am_michael", # George (Onyx) - mapped to am_michael
    "bf_isabella": "bf_vale",  # Isabella (Nova) - mapped to bf_vale
    "am_michael": "am_michael", # Michael (Sage)
    "af_sky": "af_maple",      # Sky (Shimmer) - mapped to af_maple
    
    # Keep original Kokoro voices for backward compatibility
    "af_heart": "af_heart",
    "af_maple": "af_maple", 
    "af_sol": "af_sol",
    "bf_vale": "bf_vale",
    "am_adam": "am_adam",
    "am_michael": "am_michael",
    "af_nicole": "af_nicole",
    "af_sarah": "af_sarah",
}

def _is_chinese_dominant(text: str) -> bool:
    """检查文本中中文字符是否超过60%"""
    if not text:
        return False

    chinese_count = 0
    total_chars = len(text)

    for char in text:
        # 检查是否为中文字符（包括中文标点符号）
        if '\u4e00' <= char <= '\u9fff' or '\u3000' <= char <= '\u303f' or '\uff00' <= char <= '\uffef':
            chinese_count += 1

    res = chinese_count / total_chars

    #print(res)

    return res > 0.35

def _replace_range_symbols(text: str) -> str:
    """将数字之间的-或~替换为'到'"""
    # 匹配数字-数字或数字~数字的模式
    pattern = r'(\d+)\s*[-~]\s*(\d+)'

    def replace_func(match):
        return f"{match.group(1)}到{match.group(2)}"

    return re.sub(pattern, replace_func, text)

def get_optimal_voice(user_voice: str, text: str) -> str:
    """
    根据文本语言选择最佳音色

    中文文本自动切换到双语音色，避免用纯英文音色读中文效果差。

    Args:
        user_voice: 用户指定的音色
        text: 要处理的文本

    Returns:
        最佳音色名称
    """
    # 双语音色列表（支持中英混合）
    bilingual_voices = ['af_maple', 'af_sol', 'bf_vale']

    # 检测文本是否包含中文
    has_chinese = any('\u4e00' <= c <= '\u9fff' for c in text)

    if has_chinese and user_voice not in bilingual_voices:
        # 中文文本自动切换到默认双语音色
        logger.info(f"音色自动调整: {user_voice} → af_maple (文本包含中文)")
        return 'af_maple'

    return user_voice

def process_text(text: str, input_format: str = "plain") -> str:
    """
    处理输入文本

    处理流程:
        1. 清洗 Markdown 格式 (如果 input_format="markdown")
        2. 特殊符号处理
        3. 现有数字处理逻辑

    Args:
        text: 输入文本
        input_format: "plain" (纯文本) 或 "markdown" (Markdown格式)

    Returns:
        处理后的文本
    """
    # 1. 清洗 Markdown 格式（先清洗，再检测语言）
    if input_format == "markdown":
        text = markdown_cleaner.clean(text)

    # 2. 特殊符号处理
    text = symbol_processor.process(text)

    # 3. 现有数字处理逻辑
    if _is_chinese_dominant(text):
        # 如果中文字符超过35%，只处理数字范围符号
        text = _replace_range_symbols(text)
    else:
        # 如果中文字符不超过35%，则进行原有的处理
        text = replacer.replace_phone_numbers_with_words(text)
        text = replacer.replace_ip_addresses_with_words(text)
        text = replacer.clean_numbers_in_text(text)
        text = replacer.replace_numbers_with_words(text, year_mode=True)
        text = replacer.replace_list_number_with_words(text)

    return text

def get_lang_code(voice: str) -> str:
    """根据声音获取语言代码"""
    bilingual_voice = ['af_maple', 'af_sol', 'bf_vale']
    if voice in bilingual_voice:
        return 'z'
    else:
        return voice[0]

def audio_to_wav_bytes(audio_array: np.ndarray) -> bytes:
    """将numpy数组转换为WAV字节"""
    buffer = io.BytesIO()
    sf.write(buffer, audio_array, 24000, format='WAV')
    buffer.seek(0)
    return buffer.read()

async def generate_audio_stream(text: str, voice: str, speed: float = 1.0, skip_processing: bool = False):
    """
    流式生成音频数据，用于WebSocket传输

    Args:
        text: 输入文本
        voice: 音色
        speed: 语速
        skip_processing: 是否跳过文本处理（如果文本已经处理过）
    """
    if not text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty.")

    # 处理文本（如果需要）
    processed_text = text if skip_processing else process_text(text)

    # 获取语言代码
    lang_code = get_lang_code(voice)

    # 获取对应语言的 pipeline
    try:
        pipeline = get_pipeline(lang_code)
    except AssertionError:
        raise HTTPException(status_code=400, detail=f"Unsupported lang_code: {lang_code}")

    # 流式合成音频 - 逐句生成并发送
    voice_path = os.path.join('voices', voice + '.pt')
    chunk_count = 0
    for _, _, audio in pipeline(text=processed_text, voice=voice_path, speed=speed):
        if audio is not None:
            chunk_count += 1
            # 将每个chunk转换为WAV字节数据
            audio_bytes = audio_to_wav_bytes(audio.cpu().numpy())
            yield audio_bytes
            logger.info(f"Generated audio chunk #{chunk_count}, size: {len(audio_bytes)} bytes")

    logger.info(f"Audio generation complete. Total chunks: {chunk_count}")

def generate_audio(text: str, voice: str, speed: float = 1.0, skip_processing: bool = False) -> np.ndarray:
    """
    生成音频数据（完整版本）

    Args:
        text: 输入文本
        voice: 音色
        speed: 语速
        skip_processing: 是否跳过文本处理（如果文本已经处理过）
    """
    if not text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty.")

    # 处理文本（如果需要）
    processed_text = text if skip_processing else process_text(text)

    # 获取语言代码
    lang_code = get_lang_code(voice)

    # 获取对应语言的 pipeline
    try:
        pipeline = get_pipeline(lang_code)
    except AssertionError:
        raise HTTPException(status_code=400, detail=f"Unsupported lang_code: {lang_code}")

    # 合成音频
    audios = []
    for _, _, audio in pipeline(text=processed_text, voice=os.path.join('voices', voice + '.pt'), speed=speed):
        if audio is not None:
            audios.append(audio.cpu().numpy())

    full_audio = np.concatenate(audios) if audios else np.array([], dtype=np.float32)
    return full_audio

# OpenAI 兼容的数据模型
class OpenAITTSRequest(BaseModel):
    model: str = "tts-1"  # More flexible - accept any string
    input: str
    voice: str = "alloy"  # More flexible - accept any string, will be mapped later
    response_format: Optional[str] = "mp3"  # More flexible format options
    speed: Optional[float] = 1.0
    input_format: Optional[str] = "plain"  # "plain" | "markdown"

class TTSRequest(BaseModel):
    text: str
    voice: str = "zf_001"
    speed: float = 1.0
    input_format: Optional[str] = "plain"  # "plain" | "markdown"

# OpenAI 兼容的 TTS 接口
@api.post("/v1/audio/speech")
def create_speech(request: OpenAITTSRequest):
    try:
        print(f"Received request: {request}")  # 添加日志

        # 映射声音名称，如果不存在则使用默认声音
        kokoro_voice = VOICE_MAPPING.get(request.voice, "af_heart")
        print(f"Requested voice: {request.voice}, Using voice: {kokoro_voice}")  # 添加日志

        # Validate speed range
        if request.speed and (request.speed < 0.25 or request.speed > 4.0):
            raise HTTPException(status_code=400, detail="Speed must be between 0.25 and 4.0")

        # 处理文本（支持 Markdown 清洗和特殊符号处理）
        input_format = request.input_format or "plain"
        processed_text = process_text(request.input, input_format)
        print(f"Processed text (input_format={input_format}): {processed_text[:100]}...")

        # 智能选择音色
        optimal_voice = get_optimal_voice(kokoro_voice, processed_text)
        if optimal_voice != kokoro_voice:
            print(f"Voice auto-adjusted: {kokoro_voice} → {optimal_voice}")

        # 生成音频（文本已处理，跳过二次处理）
        audio_data = generate_audio(
            text=processed_text,
            voice=optimal_voice,
            speed=request.speed or 1.0,
            skip_processing=True
        )

        print(f"Generated audio length: {len(audio_data)}")  # 添加日志

        if len(audio_data) == 0:
            raise HTTPException(status_code=500, detail="Generated audio is empty.")

        # 创建内存中的音频文件
        audio_buffer = io.BytesIO()

        # 根据请求的格式返回音频
        format_lower = (request.response_format or "mp3").lower()
        if format_lower in ["wav"]:
            sf.write(audio_buffer, audio_data, 24000, format='WAV')
            media_type = "audio/wav"
        elif format_lower in ["mp3"]:
            # Note: soundfile might not support mp3 directly, so fallback to wav
            try:
                sf.write(audio_buffer, audio_data, 24000, format='mp3')
                media_type = "audio/mp3"
            except:
                sf.write(audio_buffer, audio_data, 24000, format='WAV')
                media_type = "audio/wav"
        else:
            # Default to WAV for any other format
            sf.write(audio_buffer, audio_data, 24000, format='WAV')
            media_type = "audio/wav"

        audio_buffer.seek(0)

        return StreamingResponse(
            io.BytesIO(audio_buffer.read()),
            media_type=media_type,
            headers={
                "Content-Disposition": "inline",
                "Cache-Control": "no-cache",
                "Access-Control-Allow-Origin": "*"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in create_speech: {str(e)}")  # 添加详细错误日志
        import traceback
        traceback.print_exc()  # 打印完整的错误堆栈
        raise HTTPException(status_code=500, detail=f"Audio generation failed: {str(e)}")

# 原有的 GET 接口
@api.get("/tts")
def tts_get(
    text: str = Query(..., description="要合成的文本内容"),
    voice: str = Query("af_heart", description="参考音色名称，如 af_heart"),
    speed: float = Query(1.0, description="语速调节，如 0.9 或 1.2")
):
    audio_data = generate_audio(text, voice, speed)

    if len(audio_data) > 0:
        # 使用临时文件，避免路径问题
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
            sf.write(tmp_file.name, audio_data, 24000, format='WAV')
            output_path = tmp_file.name

        return FileResponse(
            path=output_path,
            media_type="audio/wav",
            filename="output.wav",
            background=lambda: os.unlink(output_path)  # 自动清理临时文件
        )
    else:
        raise HTTPException(status_code=500, detail="Generated audio is empty.")

# 原有的 POST 接口
@api.post("/tts_post")
def tts_post(request: TTSRequest):
    """
    POST 接口：接收 JSON 格式的文本、音色、语速，生成 `.wav` 音频文件。

    示例请求体：
    {
        "text": "你好世界",
        "voice": "af_heart",
        "speed": 1.0,
        "input_format": "plain"  // 可选: "plain" 或 "markdown"
    }
    """
    # 处理文本（支持 Markdown 清洗和特殊符号处理）
    input_format = request.input_format or "plain"
    processed_text = process_text(request.text, input_format)

    # 智能选择音色
    optimal_voice = get_optimal_voice(request.voice, processed_text)
    if optimal_voice != request.voice:
        print(f"Voice auto-adjusted: {request.voice} → {optimal_voice}")

    audio_data = generate_audio(processed_text, optimal_voice, request.speed, skip_processing=True)

    if len(audio_data) > 0:
        # 写入临时 WAV 文件
        output_path = f"output.wav"
        sf.write(output_path, audio_data, 24000, format='WAV')

        # 返回文件给客户端
        return FileResponse(path=output_path, media_type="audio/wav", filename=output_path)
    else:
        raise HTTPException(status_code=500, detail="Generated audio is empty.")

# 获取可用声音列表的接口
@api.get("/v1/audio/voices")
def list_voices():
    """
    返回可用的声音列表（OpenAI 兼容格式）
    """
    return {
        "data": [
            {"id": "alloy", "name": "Alloy", "description": "Female voice (af_heart)"},
            {"id": "echo", "name": "Echo", "description": "Male voice (am_adam)"},
            {"id": "fable", "name": "Fable", "description": "Female voice (af_nicole)"},
            {"id": "onyx", "name": "Onyx", "description": "Male voice (am_michael)"},
            {"id": "nova", "name": "Nova", "description": "Female voice (af_sarah)"},
            {"id": "shimmer", "name": "Shimmer", "description": "Bilingual voice (af_maple)"},
        ]
    }

# 健康检查接口
@api.get("/health")
def health_check():
    """健康检查接口"""
    return {"status": "healthy", "model_loaded": True}

# WebSocket 流式 TTS 接口
@api.websocket("/ws/tts")
async def websocket_tts(websocket: WebSocket):
    """
    WebSocket 流式 TTS 接口，用于实时语音合成

    请求格式：
    {
        "text": "要合成的文本",
        "voice": "af_heart",     // 可选，默认 af_heart
        "speed": 1.0,            // 可选，默认 1.0
        "input_format": "plain"  // 可选，"plain" 或 "markdown"
    }

    响应格式：
    - JSON: {"type": "sentence_start", "index": 0, "text": "...", "voice": "..."}
    - 二进制数据：WAV 音频块
    - JSON: {"type": "sentence_end", "index": 0}
    - JSON: {"type": "done", "total_sentences": N}
    - JSON: {"type": "error", "message": "错误信息"}
    """
    await websocket.accept()
    logger.info("WebSocket connection established")

    try:
        while True:
            # 接收客户端发送的数据
            data = await websocket.receive_text()
            logger.info(f"Received WebSocket message: {data[:100]}...")

            try:
                # 解析JSON数据
                request_data = json.loads(data)
                text = request_data.get("text", "")
                voice = request_data.get("voice", "af_heart")
                speed = request_data.get("speed", 1.0)
                input_format = request_data.get("input_format", "plain")

                if not text:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Text cannot be empty"
                    })
                    continue

                # 映射声音名称
                kokoro_voice = VOICE_MAPPING.get(voice, voice)
                logger.info(f"Processing TTS: voice={voice} -> {kokoro_voice}, speed={speed}, input_format={input_format}")

                # 验证语速范围
                if speed < 0.25 or speed > 4.0:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Speed must be between 0.25 and 4.0"
                    })
                    continue

                # 处理文本（支持 Markdown 清洗和特殊符号处理）
                processed_text = process_text(text, input_format)

                # 分句处理
                sentences = sentence_splitter.split(processed_text)
                logger.info(f"Split into {len(sentences)} sentences")

                if not sentences:
                    await websocket.send_json({
                        "type": "error",
                        "message": "No sentences found after processing"
                    })
                    continue

                # 逐句生成并发送
                total_chunks = 0
                total_bytes = 0

                for idx, sentence in enumerate(sentences):
                    # 每句独立选择音色
                    optimal_voice = get_optimal_voice(kokoro_voice, sentence)
                    if optimal_voice != kokoro_voice:
                        logger.info(f"Sentence {idx}: voice adjusted {kokoro_voice} → {optimal_voice}")

                    # 发送句子开始标记
                    await websocket.send_json({
                        "type": "sentence_start",
                        "index": idx,
                        "text": sentence,
                        "voice": optimal_voice
                    })

                    # 生成并发送音频（文本已处理，跳过二次处理）
                    chunk_count = 0
                    async for audio_chunk in generate_audio_stream(sentence, optimal_voice, speed, skip_processing=True):
                        chunk_count += 1
                        total_chunks += 1
                        total_bytes += len(audio_chunk)
                        await websocket.send_bytes(audio_chunk)
                        # 让出控制权，允许其他协程执行
                        await asyncio.sleep(0)

                    logger.info(f"Sentence {idx}: sent {chunk_count} chunks")

                    # 发送句子结束标记
                    await websocket.send_json({
                        "type": "sentence_end",
                        "index": idx
                    })

                # 发送完成标记
                await websocket.send_json({
                    "type": "done",
                    "total_sentences": len(sentences),
                    "total_chunks": total_chunks,
                    "total_bytes": total_bytes
                })
                logger.info(f"TTS completed: {len(sentences)} sentences, {total_chunks} chunks, {total_bytes} bytes")

            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON format"
                })
            except HTTPException as e:
                await websocket.send_json({
                    "type": "error",
                    "message": e.detail
                })
            except Exception as e:
                logger.error(f"Error processing TTS request: {e}")
                import traceback
                traceback.print_exc()
                await websocket.send_json({
                    "type": "error",
                    "message": str(e)
                })

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        try:
            await websocket.close()
        except:
            pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(api, host="0.0.0.0", port=8000)