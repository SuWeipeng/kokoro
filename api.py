from fastapi import FastAPI, Query, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from melo.api import TTS
from pydantic import BaseModel
from en_replace_number import SpecialSymbolProcessor
from markdown_cleaner import MarkdownCleaner
from sentence_splitter import SentenceSplitter
import os
import torch
import soundfile as sf
import numpy as np
import io
import scipy.signal
from typing import Literal, Optional
import tempfile
import uuid
import re
import asyncio
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 设备检查（跨平台兼容）
def check_device():
    if torch.cuda.is_available():
        device_name = torch.cuda.get_device_name(0)
        device_count = torch.cuda.device_count()
        print(f"CUDA available: {device_name}")
        print(f"CUDA version: {torch.version.cuda}")
        print(f"GPU count: {device_count}")
        # 支持多 GPU 环境，自动选择可用设备
        return 'cuda:0'
    elif torch.backends.mps.is_available():
        # macOS MPS 支持
        print("MPS (Apple Silicon) available")
        return 'mps'
    else:
        print("Using CPU")
        return 'cpu'

# 从环境变量读取设备（支持覆盖自动检测）
# 支持的值: auto, cuda:0, cuda:1, cpu, mps
device = os.environ.get('MeloTTS_DEVICE', 'auto')
if device == 'auto':
    device = check_device()
print(f"Using device: {device}")

# MeloTTS 模型单例（中文和英文分别加载）
tts_models = {}  # {language: TTS instance}
speaker_ids_map = {}  # {language: {speaker_name: speaker_id}}

def load_melo_model(language='ZH'):
    """延迟加载 MeloTTS 模型（支持 ZH 和 EN）"""
    if language not in tts_models:
        print(f"Loading MeloTTS model ({language})...")
        try:
            # 使用 device 参数直接指定设备，避免 meta 张量问题
            tts_models[language] = TTS(language=language, device=device)
            speaker_ids_map[language] = dict(tts_models[language].hps.data.spk2id)
            print(f"MeloTTS {language} model loaded. Speaker IDs: {speaker_ids_map[language]}")
        except NotImplementedError as e:
            if "meta tensor" in str(e):
                print(f"尝试重新加载 {language} 模型，使用设备重置...")
                # 清理 CUDA 缓存后重试
                if 'cuda' in device:
                    torch.cuda.empty_cache()
                    torch.cuda.reset_peak_memory_stats()
                tts_models[language] = TTS(language=language, device=device)
                speaker_ids_map[language] = dict(tts_models[language].hps.data.spk2id)
                print(f"MeloTTS {language} model loaded (retry). Speaker IDs: {speaker_ids_map[language]}")
            else:
                raise
    return tts_models[language], speaker_ids_map[language]

# 创建 FastAPI 应用
api = FastAPI(title="MeloTTS API with OpenAI Compatibility")

api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局实例：Markdown 清洗、句子分割、特殊符号处理
markdown_cleaner = MarkdownCleaner()
sentence_splitter = SentenceSplitter()
symbol_processor = SpecialSymbolProcessor()

# MeloTTS speaker_id 映射
# 中文音色和英文音色的映射关系
# 注意：alloy 是双语音色，始终使用 ZH 模型
SPEAKER_MAPPING = {
    # 双语音色（始终使用 ZH 模型）
    "alloy": "BILINGUAL",  # 中英双语
    
    # 英文音色（根据口音选择）
    "echo": "EN-US",         # 美式英语
    "fable": "EN-BR",        # 英式英语
    "onyx": "EN-Default",    # 默认英语
    "nova": "EN-US",         # 美式英语
    "shimmer": "EN-AU",      # 澳大利亚英语
}

# 英文口音映射
EN_ACCENT_MAPPING = {
    "EN-US": "EN-US",    # 美式英语
    "EN-BR": "EN-BR",    # 英式英语
    "EN_INDIA": "EN_INDIA",  # 印度英语
    "EN-AU": "EN-AU",    # 澳大利亚英语
    "EN-Default": "EN-Default",  # 默认英语
}

def detect_language(text: str) -> str:
    """
    检测文本语言
    如果包含中文字符返回 'ZH'，否则返回 'EN'
    """
    if not text:
        return 'EN'
    
    # 检查中文字符
    for char in text:
        if '\u4e00' <= char <= '\u9fff':
            return 'ZH'
    
    return 'EN'

def get_speaker_and_model(voice: str, text: str) -> tuple:
    """
    根据音色和文本语言获取对应的 MeloTTS 模型和 speaker_id
    
    双语音色（alloy）始终使用 ZH 模型，支持中英文混合文本。
    
    Returns:
        (model, speaker_id, language) 元组
    """
    # 检测文本语言
    language = detect_language(text)
    
    # 检查是否是双语音色
    if SPEAKER_MAPPING.get(voice) == "BILINGUAL":
        # 双语音色始终使用 ZH 模型
        model, speaker_ids = load_melo_model('ZH')
        speaker_id = speaker_ids.get('ZH', 1)
        return model, speaker_id, 'ZH'
    
    # 根据语言选择 speaker
    if language == 'ZH':
        speaker_name = 'ZH'
        model, speaker_ids = load_melo_model('ZH')
    else:
        # 英文文本使用英文音色
        speaker_name = SPEAKER_MAPPING.get(voice, "EN-Default")
        model, speaker_ids = load_melo_model('EN')
    
    speaker_id = speaker_ids.get(speaker_name, 'ZH' if language == 'ZH' else 'EN-Default')
    
    return model, speaker_id, language

def audio_file_to_bytes(file_path: str) -> bytes:
    """从文件读取 WAV 数据为 bytes"""
    with open(file_path, 'rb') as f:
        return f.read()

def audio_to_wav_bytes(audio_array: np.ndarray, sample_rate: int = 24000) -> bytes:
    """将numpy数组转换为WAV字节（保留用于兼容性）"""
    buffer = io.BytesIO()
    sf.write(buffer, audio_array, sample_rate, format='WAV')
    buffer.seek(0)
    return buffer.read()

def convert_audio_to_target_format(audio_bytes: bytes, target_sample_rate: int = 24000, target_format: str = "wav") -> tuple:
    """
    将音频数据转换为目标格式和采样率
    
    Args:
        audio_bytes: 原始音频字节数据
        target_sample_rate: 目标采样率
        target_format: 目标格式 ("wav" 或 "mp3")
    
    Returns:
        (audio_bytes, media_type) 元组
    """
    # 读取音频数据
    audio_array, source_sr = sf.read(io.BytesIO(audio_bytes))
    
    # 如果采样率不同，进行重采样
    if source_sr != target_sample_rate:
        # 计算重采样后的长度
        ratio = target_sample_rate / source_sr
        new_length = int(len(audio_array) * ratio)
        audio_array = scipy.signal.resample(audio_array, new_length)
    
    # 转换为指定格式
    buffer = io.BytesIO()
    if target_format.lower() in ["wav", "wave"]:
        sf.write(buffer, audio_array, target_sample_rate, format='WAV')
        media_type = "audio/wav"
    elif target_format.lower() in ["mp3", "mpeg"]:
        # 尝试使用 soundfile 编码 MP3
        mp3_success = False
        try:
            sf.write(buffer, audio_array, target_sample_rate, format='MP3')
            media_type = "audio/mpeg"
            mp3_success = True
        except Exception as e:
            print(f"soundfile MP3 encoding failed: {e}, trying ffmpeg...")
        
        # 如果 soundfile 不支持 MP3，使用 ffmpeg 命令转换
        if not mp3_success:
            try:
                import subprocess
                
                # 先将音频数据写入临时 WAV 文件（使用正确的参数）
                temp_wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
                temp_wav_path = temp_wav.name
                temp_wav.close()
                
                # 使用 soundfile 写入 WAV，指定正确的参数
                # soundfile 默认将 float 数据视为归一化浮点数，范围 [-1, 1]
                sf.write(temp_wav_path, audio_array, source_sr, format='WAV', subtype='PCM_16')
                
                # 使用 ffmpeg 转换为 MP3
                temp_mp3 = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
                temp_mp3_path = temp_mp3.name
                temp_mp3.close()
                
                cmd = [
                    'ffmpeg', '-y', '-i', temp_wav_path,
                    '-acodec', 'libmp3lame',
                    '-b:a', '64k',
                    '-ar', str(target_sample_rate),
                    temp_mp3_path
                ]
                
                subprocess.run(cmd, capture_output=True, check=True)
                
                # 读取 MP3 数据
                with open(temp_mp3_path, 'rb') as f:
                    audio_bytes = f.read()
                
                buffer = io.BytesIO(audio_bytes)
                media_type = "audio/mpeg"
                print(f"ffmpeg MP3 encoding successful")
                
                # 清理临时文件
                os.unlink(temp_wav_path)
                os.unlink(temp_mp3_path)
                
            except FileNotFoundError:
                print("ffmpeg not installed, falling back to WAV")
                sf.write(buffer, audio_array, target_sample_rate, format='WAV')
                media_type = "audio/wav"
            except Exception as e:
                print(f"ffmpeg MP3 encoding failed: {e}, falling back to WAV")
                sf.write(buffer, audio_array, target_sample_rate, format='WAV')
                media_type = "audio/wav"
                # 清理可能的临时文件
                try:
                    os.unlink(temp_wav_path)
                except:
                    pass
                try:
                    os.unlink(temp_mp3_path)
                except:
                    pass
    else:
        # 默认使用 WAV
        sf.write(buffer, audio_array, target_sample_rate, format='WAV')
        media_type = "audio/wav"
    
    buffer.seek(0)
    return buffer.read(), media_type

async def generate_audio_stream(text: str, speaker: str = "ZH", speed: float = 1.0, skip_processing: bool = False):
    """
    流式生成音频数据，用于WebSocket传输
    
    由于 MeloTTS 不支持真正的流式输出，采用句子级流式：
    1. 将文本分句
    2. 对每句调用 tts_to_file 生成完整音频
    3. 生成完成后立即发送该句音频
    
    Args:
        text: 输入文本
        speaker: MeloTTS speaker_id
        speed: 语速
        skip_processing: 是否跳过文本处理（如果文本已经处理过）
    """
    if not text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty.")
    
    # 处理文本（如果需要）
    processed_text = text if skip_processing else process_text(text)
    
    # 检测语言并加载对应模型
    language = detect_language(processed_text)
    model, spk_ids = load_melo_model(language)
    # speaker 已经是整数 speaker_id（由 get_speaker_and_model 返回）
    speaker_id = int(speaker)
    
    # 分句处理
    sentences = sentence_splitter.split(processed_text)
    logger.info(f"Split into {len(sentences)} sentences")
    
    if not sentences:
        raise HTTPException(status_code=400, detail="No sentences found after processing")
    
    # 逐句生成并发送
    total_chunks = 0
    total_bytes = 0
    
    for idx, sentence in enumerate(sentences):
        # 创建临时文件
        temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        temp_path = temp_file.name
        temp_file.close()
        
        try:
            # 生成音频到文件
            model.tts_to_file(sentence, speaker_id, temp_path, speed=speed)
            logger.info(f"Generated sentence {idx}: {sentence[:50]}...")
            
            # 读取文件数据
            audio_bytes = audio_file_to_bytes(temp_path)
            total_chunks += 1
            total_bytes += len(audio_bytes)
            
            # 发送句子开始标记
            yield {
                "type": "sentence_start",
                "index": idx,
                "text": sentence,
                "voice": speaker
            }, audio_bytes
            
            # 发送句子结束标记
            yield {
                "type": "sentence_end",
                "index": idx
            }, None
            
        finally:
            # 清理临时文件
            try:
                os.unlink(temp_path)
            except:
                pass
    
    # 发送完成标记
    yield {
        "type": "done",
        "total_sentences": len(sentences),
        "total_chunks": total_chunks,
        "total_bytes": total_bytes
    }, None

def generate_audio(text: str, speaker_id: int = 1, speed: float = 1.0, skip_processing: bool = False,
                   target_format: str = "wav", target_sample_rate: int = 24000) -> tuple:
    """
    生成音频数据（完整版本）
    
    Args:
        text: 输入文本
        speaker_id: MeloTTS speaker_id (整数)
        speed: 语速
        skip_processing: 是否跳过文本处理（如果文本已经处理过）
        target_format: 目标格式 ("wav" 或 "mp3")
        target_sample_rate: 目标采样率
    
    Returns:
        (audio_bytes, media_type) 元组
    """
    if not text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty.")
    
    # 处理文本（如果需要）
    processed_text = text if skip_processing else process_text(text)
    
    # 检测语言并加载对应模型
    language = detect_language(processed_text)
    model, spk_ids = load_melo_model(language)
    
    # 创建临时文件
    temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    temp_path = temp_file.name
    temp_file.close()
    
    try:
        # 生成音频到文件（speaker_id 已经是整数）
        model.tts_to_file(processed_text, speaker_id, temp_path, speed=speed)
        logger.info(f"Generated audio for: {processed_text[:50]}...")
        
        # 读取文件数据并转换格式
        audio_bytes = audio_file_to_bytes(temp_path)
        return convert_audio_to_target_format(audio_bytes, target_sample_rate, target_format)
        
    finally:
        # 清理临时文件
        try:
            os.unlink(temp_path)
        except:
            pass

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
    voice: str = "alloy"
    speed: float = 1.0
    input_format: Optional[str] = "plain"  # "plain" | "markdown"

# OpenAI 兼容的 TTS 接口
@api.post("/v1/audio/speech")
def create_speech(request: OpenAITTSRequest):
    try:
        print(f"Received request: {request}")
        
        # 根据文本语言智能选择模型和音色
        model, speaker_id, language = get_speaker_and_model(request.voice, request.input)
        print(f"Requested voice: {request.voice}, Language: {language}, Using speaker_id: {speaker_id}")
        
        # Validate speed range
        if request.speed and (request.speed < 0.25 or request.speed > 4.0):
            raise HTTPException(status_code=400, detail="Speed must be between 0.25 and 4.0")
        
        # 处理文本（支持 Markdown 清洗和特殊符号处理）
        input_format = request.input_format or "plain"
        processed_text = process_text(request.input, input_format)
        print(f"Processed text (input_format={input_format}): {processed_text[:100]}...")
        
        # 生成音频（直接传入 speaker_id 整数）
        response_format = (request.response_format or "wav").lower()
        audio_bytes, media_type = generate_audio(
            text=processed_text,
            speaker_id=speaker_id,
            speed=request.speed or 1.0,
            skip_processing=True,
            target_format=response_format,
            target_sample_rate=24000
        )
        
        print(f"Generated audio size: {len(audio_bytes)} bytes, format: {media_type}")
        
        if len(audio_bytes) == 0:
            raise HTTPException(status_code=500, detail="Generated audio is empty.")
        
        # 返回音频
        return StreamingResponse(
            io.BytesIO(audio_bytes),
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
        print(f"Error in create_speech: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Audio generation failed: {str(e)}")

# 原有的 GET 接口
@api.get("/tts")
def tts_get(
    text: str = Query(..., description="要合成的文本内容"),
    voice: str = Query("alloy", description="音色名称"),
    speed: float = Query(1.0, description="语速调节，如 0.9 或 1.2")
):
    # 根据文本语言智能选择模型
    model, speaker_id, language = get_speaker_and_model(voice, text)
    audio_bytes, media_type = generate_audio(text, speaker_id, speed, target_sample_rate=24000)
    print(f"Voice: {voice}, Language: {language}, Speaker_id: {speaker_id}")
    
    if len(audio_bytes) > 0:
        return StreamingResponse(
            io.BytesIO(audio_bytes),
            media_type=media_type,
            headers={"Access-Control-Allow-Origin": "*"}
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
        "voice": "alloy",
        "speed": 1.0,
        "input_format": "plain"  // 可选: "plain" 或 "markdown"
    }
    """
    # 处理文本（支持 Markdown 清洗和特殊符号处理）
    input_format = request.input_format or "plain"
    processed_text = process_text(request.text, input_format)
    
    # 根据文本语言智能选择模型和音色
    model, speaker_id, language = get_speaker_and_model(request.voice, processed_text)
    audio_bytes, media_type = generate_audio(processed_text, speaker_id, request.speed, skip_processing=True, target_sample_rate=24000)
    print(f"Voice: {request.voice}, Language: {language}, Speaker_id: {speaker_id}")
    
    if len(audio_bytes) > 0:
        # 根据格式确定文件扩展名
        ext = "wav" if "wav" in media_type else "mp3"
        
        # 创建临时文件
        temp_file = tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False)
        temp_path = temp_file.name
        temp_file.close()
        
        try:
            with open(temp_path, 'wb') as f:
                f.write(audio_bytes)
            
            # 返回文件给客户端
            return FileResponse(path=temp_path, media_type=media_type, filename=f"output.{ext}",
                              background=lambda: os.unlink(temp_path))
        except:
            os.unlink(temp_path)
            raise
    else:
        raise HTTPException(status_code=500, detail="Generated audio is empty.")

# 获取可用声音列表的接口
@api.get("/v1/audio/voices")
def list_voices():
    """
    返回可用的声音列表（OpenAI 兼容格式）
    注意：MeloTTS 使用统一音色，支持中英文混合
    """
    return {
        "data": [
            {"id": "alloy", "name": "Alloy", "description": "🌏 Bilingual Chinese-English voice (中英双语)"},
            {"id": "echo", "name": "Echo", "description": "English (US) voice"},
            {"id": "fable", "name": "Fable", "description": "English (British) voice"},
            {"id": "onyx", "name": "Onyx", "description": "English (Default) voice"},
            {"id": "nova", "name": "Nova", "description": "English (US) voice"},
            {"id": "shimmer", "name": "Shimmer", "description": "English (Australian) voice"},
        ]
    }

# 健康检查接口
@api.get("/health")
def health_check():
    """健康检查接口"""
    model_status = "loaded" if tts_models else "not_loaded"
    return {"status": "healthy", "model_loaded": True, "model_status": model_status}

# WebSocket 流式 TTS 接口
@api.websocket("/ws/tts")
async def websocket_tts(websocket: WebSocket):
    """
    WebSocket 流式 TTS 接口，用于实时语音合成
    
    请求格式：
    {
        "text": "要合成的文本",
        "voice": "alloy",     // 可选，默认 alloy
        "speed": 1.0,         // 可选，默认 1.0
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
                voice = request_data.get("voice", "alloy")
                speed = request_data.get("speed", 1.0)
                input_format = request_data.get("input_format", "plain")
                
                if not text:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Text cannot be empty"
                    })
                    continue
                
                # 根据文本语言智能选择模型
                model, speaker, language = get_speaker_and_model(voice, text)
                logger.info(f"Processing TTS: voice={voice}, language={language}, speaker={speaker}, speed={speed}, input_format={input_format}")
                
                # 验证语速范围
                if speed < 0.25 or speed > 4.0:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Speed must be between 0.25 and 4.0"
                    })
                    continue
                
                # 处理文本（支持 Markdown 清洗和特殊符号处理）
                processed_text = process_text(text, input_format)
                
                # speaker 已经是整数 speaker_id（由 get_speaker_and_model 返回）
                speaker_id = int(speaker)
                
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
                    # 发送句子开始标记
                    await websocket.send_json({
                        "type": "sentence_start",
                        "index": idx,
                        "text": sentence,
                        "voice": speaker
                    })
                    
                    # 创建临时文件
                    temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
                    temp_path = temp_file.name
                    temp_file.close()
                    
                    try:
                        # 生成音频到文件
                        model.tts_to_file(sentence, speaker_id, temp_path, speed=speed)
                        logger.info(f"Generated sentence {idx}: {sentence[:50]}...")
                        
                        # 读取文件数据
                        audio_bytes = audio_file_to_bytes(temp_path)
                        total_chunks += 1
                        total_bytes += len(audio_bytes)
                        
                        # 发送音频数据
                        await websocket.send_bytes(audio_bytes)
                        
                        # 让出控制权，允许其他协程执行
                        await asyncio.sleep(0)
                        
                    finally:
                        # 清理临时文件
                        try:
                            os.unlink(temp_path)
                        except:
                            pass
                    
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

def process_text(text: str, input_format: str = "plain") -> str:
    """
    处理输入文本
    
    处理流程:
        1. 清洗 Markdown 格式 (如果 input_format="markdown")
        2. 特殊符号处理
        3. 注意：不再执行数字转英文逻辑，因为 MeloTTS ZH 模型可以直接处理中英文混合
    
    Args:
        text: 输入文本
        input_format: "plain" (纯文本) 或 "markdown" (Markdown格式)
    
    Returns:
        处理后的文本
    """
    # 1. 清洗 Markdown 格式
    if input_format == "markdown":
        text = markdown_cleaner.clean(text)
    
    # 2. 特殊符号处理（保留中英文版本）
    text = symbol_processor.process(text)
    
    # 3. 不再执行数字转英文逻辑，MeloTTS ZH 模型可以直接处理中英文混合文本
    
    return text

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(api, host="0.0.0.0", port=8000)
