"""
WebSocket TTS Audio Playback Test Script
WebSocket TTS 音频播放测试脚本（需要音频播放库）

Requirements:
    pip install websockets sounddevice soundfile

Usage:
    python test_websocket_audio.py
"""
import asyncio
import websockets
import json
import io
import soundfile as sf
import sounddevice as sd
from typing import Optional


class AudioPlayer:
    """简单的音频播放器"""

    def __init__(self):
        self.default_samplerate = 24000
        # 查看可用设备
        print(sd.query_devices())

    def play_audio(self, audio_bytes: bytes) -> float:
        """
        播放音频字节数据

        Args:
            audio_bytes: WAV格式的音频字节数据

        Returns:
            播放时长（秒）
        """
        try:
            # 从字节数据读取音频
            audio, sr = sf.read(io.BytesIO(audio_bytes))

            # 播放音频
            sd.play(audio, sr)
            sd.wait()  # 等待播放完成

            duration = len(audio) / sr
            return duration
        except Exception as e:
            print(f"  播放错误: {e}")
            return 0.0


async def stream_tts(text: str, voice: str = "af_heart", speed: float = 1.0,
                    player: Optional[AudioPlayer] = None, play_audio: bool = False):
    """
    流式TTS并可选地播放音频

    Args:
        text: 要合成的文本
        voice: 音色
        speed: 语速
        player: 音频播放器
        play_audio: 是否播放音频
    """
    uri = "ws://localhost:9880/ws/tts"

    print(f"\n正在合成: {text[:50]}...")
    print(f"  音色: {voice}, 语速: {speed}")

    try:
        async with websockets.connect(uri) as ws:
            # 发送请求
            await ws.send(json.dumps({
                "text": text,
                "voice": voice,
                "speed": speed
            }))

            # 接收并播放音频流
            chunk_count = 0
            total_duration = 0.0
            total_bytes = 0

            while True:
                try:
                    message = await asyncio.wait_for(ws.recv(), timeout=10.0)

                    # 检查消息类型（文本还是二进制）
                    if isinstance(message, bytes):
                        # 音频数据（二进制）
                        chunk_count += 1
                        total_bytes += len(message)
                        duration = len(message) / (48000 * 2)  # 估算时长（假设16bit PCM）

                        if play_audio and player:
                            print(f"  音频块 #{chunk_count}: {len(message)} 字节, 播放中...")
                            actual_duration = player.play_audio(message)
                            total_duration += actual_duration
                        else:
                            print(f"  音频块 #{chunk_count}: {len(message)} 字节")
                    else:
                        # 文本消息（JSON）
                        try:
                            msg = json.loads(message)
                            if msg.get("type") == "done":
                                print(f"  ✓ 完成!")
                                print(f"    音频块: {msg.get('chunks', chunk_count)} 个")
                                print(f"    总大小: {msg.get('total_bytes', total_bytes)/1024:.2f} KB")
                                if play_audio:
                                    print(f"    总时长: {total_duration:.2f} 秒")
                                break
                            elif msg.get("type") == "error":
                                print(f"  ✗ 错误: {msg.get('message')}")
                                break
                        except json.JSONDecodeError:
                            pass

                except asyncio.TimeoutError:
                    print("  ⏱ 超时，等待下一个音频块...")
                    continue

    except websockets.exceptions.WebSocketException as e:
        print(f"  ✗ WebSocket 连接错误: {e}")
        print("\n请确保服务正在运行:")
        print("  1. 双击 start_service.bat")
        print("  2. 或运行: uvicorn api:api --host 0.0.0.0 --port 9880 --reload")
    except Exception as e:
        print(f"  ✗ 错误: {e}")


async def test_single(play_audio: bool = False):
    """单次播放测试"""
    print("\n=== 单次播放测试 ===")

    player = AudioPlayer() if play_audio else None
    await stream_tts(
        "你好，这是一个WebSocket TTS测试。This is a test of the WebSocket text-to-speech system.",
        voice="af_maple",  # 使用双语音色
        speed=1.0,
        player=player,
        play_audio=play_audio
    )


async def test_conversation(play_audio: bool = False):
    """连续对话测试"""
    print("\n=== 连续对话测试（使用双语音色）===")

    conversations = [
        ("你好，今天天气怎么样？How's the weather today?", "af_maple", 1.0),
        ("我觉得天气不错，要不要出去走走？I think it's nice, want to go out?", "af_maple", 1.0),
        ("好的，那我们走吧。去哪里呢？OK, let's go. Where to?", "af_maple", 1.0),
        ("我们可以去公园。We can go to the park.", "af_maple", 1.0),
    ]

    player = AudioPlayer() if play_audio else None

    for text, voice, speed in conversations:
        await stream_tts(text, voice, speed, player, play_audio)
        await asyncio.sleep(0.5)  # 间隔0.5秒


async def test_voices(play_audio: bool = False):
    """测试不同音色"""
    print("\n=== 不同音色测试 ===")

    # 定义音色和对应的测试文本
    voice_tests = [
        # 双语音色使用中英文混合文本
        ("af_maple", "双语声 (Maple)", "你好，这是双语测试。Hello, this is a bilingual test."),
        ("af_sol", "双语声 (Sol)", "你好，我是Sol。Hi, I'm Sol."),
        ("bf_vale", "双语声 (Vale)", "欢迎来到Kokoro TTS。Welcome to Kokoro TTS."),
        # 非双语音色使用英文文本
        ("af_heart", "女声 (Heart)", "Hello, this is a test of the Heart voice. It sounds natural and clear."),
        ("af_sarah", "女声 (Sarah)", "Hi there! My name is Sarah. Nice to meet you."),
        ("af_nicole", "女声 (Nicole)", "Hello, I'm Nicole. This voice is perfect for narration."),
        ("am_adam", "男声 (Adam)", "Good morning! I'm Adam. This is a male voice example."),
        ("am_michael", "男声 (Michael)", "Hello everyone, I'm Michael. This is a professional male voice."),
    ]

    player = AudioPlayer() if play_audio else None

    for voice, description, test_text in voice_tests:
        print(f"\n测试音色: {description}")
        print(f"  文本: {test_text[:55]}...")
        await stream_tts(test_text, voice, 1.0, player, play_audio)
        await asyncio.sleep(1.0)  # 增加延迟到1秒，避免连接冲突


async def test_bilingual(play_audio: bool = False):
    """测试中英文混合"""
    print("\n=== 中英文混合测试（使用双语音色）===")

    bilingual_texts = [
        "你好Hello世界World",
        "Today is 今天，and tomorrow is 明天。",
        "这个price是$100，非常cheap！",
        "I think 这个idea很good，你觉得how？",
        ("The weather today is 天气很好，let's go out 出去玩！", "af_maple"),
        ("这个API API非常powerful强大，easy to use 很好用！", "af_sol"),
        ("Welcome欢迎 to Kokoro TTS，enjoy享受 it！", "bf_vale"),
    ]

    player = AudioPlayer() if play_audio else None

    # 使用不同双语音色测试
    for item in bilingual_texts:
        if isinstance(item, tuple):
            text, voice = item
        else:
            text, voice = item, "af_maple"
        print(f"\n测试 [{voice}]: {text}")
        await stream_tts(text, voice, 1.0, player, play_audio)
        await asyncio.sleep(0.5)


async def test_speed(play_audio: bool = False):
    """测试不同语速"""
    print("\n=== 语速测试（使用双语音色）===")

    test_text = "这是一个语速测试。This is a speed test for bilingual voice."
    speeds = [0.5, 0.8, 1.0, 1.2, 1.5, 2.0]

    player = AudioPlayer() if play_audio else None

    for speed in speeds:
        print(f"\n测试语速: {speed}x")
        await stream_tts(test_text, "af_maple", speed, player, play_audio)
        await asyncio.sleep(0.3)


async def test_markdown_format(play_audio: bool = False):
    """测试 Markdown 格式支持"""
    print("\n=== Markdown 格式测试 ===")

    markdown_tests = [
        ("# 欢迎使用\n\n这是**粗体**文本。", "标题和粗体"),
        ("## 功能\n\n- 功能一\n- 功能二\n- 功能三", "列表"),
        ("这是[链接](url)和`代码`。", "链接和代码"),
        ("普通文本测试。", "纯文本对照"),
    ]

    player = AudioPlayer() if play_audio else None

    for text, description in markdown_tests:
        print(f"\n测试: {description}")
        print(f"  Markdown: {text[:50]}...")

        # 使用 WebSocket 发送 Markdown 格式请求
        uri = "ws://localhost:9880/ws/tts"

        try:
            async with websockets.connect(uri) as ws:
                await ws.send(json.dumps({
                    "text": text,
                    "voice": "af_maple",
                    "input_format": "markdown"  # 关键：指定 Markdown 格式
                }))

                sentence_count = 0
                while True:
                    try:
                        message = await asyncio.wait_for(ws.recv(), timeout=5.0)

                        if isinstance(message, str):
                            msg = json.loads(message)
                            if msg.get("type") == "sentence_start":
                                sentence_count += 1
                                print(f"  句子 {msg['index']}: {msg['text'][:50]}")
                                if play_audio and player:
                                    # 下一个消息应该是音频
                            elif msg.get("type") == "sentence_end":
                                pass
                            elif msg.get("type") == "done":
                                print(f"  ✓ 完成，共 {msg.get('total_sentences', sentence_count)} 句")
                                break
                            elif msg.get("type") == "error":
                                print(f"  ✗ 错误: {msg.get('message')}")
                                break
                        elif isinstance(message, bytes) and play_audio and player:
                            player.play_audio(message)

                    except asyncio.TimeoutError:
                        print(f"  ✓ 完成（超时）")
                        break

        except websockets.exceptions.WebSocketException as e:
            print(f"  ✗ 连接错误: {e}")

        await asyncio.sleep(0.5)


async def test_special_symbols(play_audio: bool = False):
    """测试特殊符号处理"""
    print("\n=== 特殊符号处理测试 ===")

    symbol_tests = [
        ("3乘以4等于12。", "数学符号（乘法）"),
        ("10除以2等于5。", "数学符号（除法）"),
        ("温度是25摄氏度。", "单位符号（摄氏度）"),
        ("折扣是50%。", "单位符号（百分比）"),
        ("价格是100美元。", "货币符号（美元）"),
    ]

    player = AudioPlayer() if play_audio else None

    for text, description in symbol_tests:
        print(f"\n测试: {description}")
        print(f"  文本: {text}")

        await stream_tts(text, "af_maple", 1.0, player, play_audio)
        await asyncio.sleep(0.3)


async def test_smart_voice_selection(play_audio: bool = False):
    """测试智能音色选择"""
    print("\n=== 智能音色选择测试 ===")

    voice_tests = [
        ("Hello, this is English.", "am_adam", "英文文本"),
        ("你好，这是中文。", "am_adam", "中文文本（应自动切换）"),
        ("Hello 你好，mixed 混合。", "am_adam", "中英混合（应自动切换）"),
    ]

    player = AudioPlayer() if play_audio else None

    for text, user_voice, description in voice_tests:
        print(f"\n测试: {description}")
        print(f"  文本: {text[:50]}")
        print(f"  用户指定音色: {user_voice}")

        uri = "ws://localhost:9880/ws/tts"

        try:
            async with websockets.connect(uri) as ws:
                await ws.send(json.dumps({
                    "text": text,
                    "voice": user_voice,
                    "input_format": "plain"
                }))

                actual_voice = None
                while True:
                    try:
                        message = await asyncio.wait_for(ws.recv(), timeout=5.0)

                        if isinstance(message, str):
                            msg = json.loads(message)
                            if msg.get("type") == "sentence_start":
                                actual_voice = msg.get("voice")
                                print(f"  实际使用音色: {actual_voice}")
                                if actual_voice != user_voice:
                                    print(f"  → 音色自动调整: {user_voice} → {actual_voice}")
                            elif msg.get("type") == "done":
                                print(f"  ✓ 完成")
                                break
                            elif msg.get("type") == "error":
                                print(f"  ✗ 错误: {msg.get('message')}")
                                break
                        elif isinstance(message, bytes) and play_audio and player:
                            player.play_audio(message)

                    except asyncio.TimeoutError:
                        print(f"  ✓ 完成（超时）")
                        break

        except websockets.exceptions.WebSocketException as e:
            print(f"  ✗ 连接错误: {e}")

        await asyncio.sleep(0.5)


if __name__ == "__main__":
    print("=" * 60)
    print("WebSocket TTS 音频播放测试")
    print("=" * 60)

    print("\n请先确保:")
    print("1. 已安装依赖: pip install websockets sounddevice soundfile")
    print("2. 服务正在运行")

    print("\n" + "=" * 60)
    print("选择测试类型:")
    print("1. 单次播放测试")
    print("2. 连续对话测试")
    print("3. 不同音色测试")
    print("4. 中英文混合测试")
    print("5. 语速测试")
    print("6. Markdown 格式测试 ⭐ NEW")
    print("7. 特殊符号处理测试 ⭐ NEW")
    print("8. 智能音色选择测试 ⭐ NEW")
    print("=" * 60)

    choice = input("\n请输入选择 (1-8，默认1): ").strip() or "1"

    play_choice = input("是否播放音频? (y/n，默认n): ").strip().lower()
    play_audio = play_choice == 'y'

    if play_audio:
        print("\n注意: 音频播放需要音频输出设备")

    print("\n开始测试...")

    if choice == "1":
        asyncio.run(test_single(play_audio))
    elif choice == "2":
        asyncio.run(test_conversation(play_audio))
    elif choice == "3":
        asyncio.run(test_voices(play_audio))
    elif choice == "4":
        asyncio.run(test_bilingual(play_audio))
    elif choice == "5":
        asyncio.run(test_speed(play_audio))
    elif choice == "6":
        asyncio.run(test_markdown_format(play_audio))
    elif choice == "7":
        asyncio.run(test_special_symbols(play_audio))
    elif choice == "8":
        asyncio.run(test_smart_voice_selection(play_audio))
    else:
        print("无效选择，运行单次播放测试...")
        asyncio.run(test_single(play_audio))

    print("\n" + "=" * 60)
    print("测试完成!")
