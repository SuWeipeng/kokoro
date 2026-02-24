"""
Markdown TTS Test Script
测试 Markdown 格式支持、特殊符号处理、智能音色选择等功能

Requirements:
    pip install websockets

Usage:
    python test_markdown_tts.py
"""
import asyncio
import websockets
import json
from typing import List, Tuple


async def test_markdown_cleaning():
    """测试 Markdown 格式清洗"""
    print("\n" + "=" * 60)
    print("测试 1: Markdown 格式清洗")
    print("=" * 60)

    markdown_texts = [
        ("# 欢迎使用\n\n这是**粗体**文本。", "标题和粗体"),
        ("## 功能介绍\n\n- 功能一\n- 功能二", "列表"),
        ("这是[链接](https://example.com)和`代码`。", "链接和代码"),
        ("普通文本。", "纯文本"),
    ]

    uri = "ws://localhost:9880/ws/tts"

    try:
        async with websockets.connect(uri) as ws:
            for text, description in markdown_texts:
                print(f"\n测试: {description}")
                print(f"输入: {text[:50]}...")

                await ws.send(json.dumps({
                    "text": text,
                    "voice": "af_maple",
                    "input_format": "markdown"
                }))

                # 接收响应
                sentence_count = 0
                while True:
                    try:
                        message = await asyncio.wait_for(ws.recv(), timeout=5.0)

                        if isinstance(message, str):
                            msg = json.loads(message)
                            if msg.get("type") == "sentence_start":
                                sentence_count += 1
                                print(f"  句子 {msg['index']}: {msg['text'][:50]}...")
                            elif msg.get("type") == "done":
                                print(f"  ✓ 完成，共 {msg.get('total_sentences', sentence_count)} 句")
                                break
                            elif msg.get("type") == "error":
                                print(f"  ✗ 错误: {msg.get('message')}")
                                break
                    except asyncio.TimeoutError:
                        print(f"  ✓ 完成（超时退出）")
                        break

                await asyncio.sleep(0.3)

    except websockets.exceptions.WebSocketException as e:
        print(f"✗ WebSocket 连接错误: {e}")
        print("\n请确保服务正在运行:")
        print("  uvicorn api:api --host 0.0.0.0 --port 9880 --reload")


async def test_special_symbols():
    """测试特殊符号处理"""
    print("\n" + "=" * 60)
    print("测试 2: 特殊符号处理")
    print("=" * 60)

    symbol_tests = [
        ("3乘以4等于12。", "数学符号（乘法）"),
        ("温度是25摄氏度。", "单位符号（温度）"),
        ("折扣是50%。", "单位符号（百分比）"),
        ("价格是100美元。", "货币符号"),
    ]

    uri = "ws://localhost:9880/ws/tts"

    try:
        async with websockets.connect(uri) as ws:
            for text, description in symbol_tests:
                print(f"\n测试: {description}")
                print(f"输入: {text}")

                await ws.send(json.dumps({
                    "text": text,
                    "voice": "af_maple",
                    "input_format": "plain"
                }))

                # 接收响应
                while True:
                    try:
                        message = await asyncio.wait_for(ws.recv(), timeout=5.0)

                        if isinstance(message, str):
                            msg = json.loads(message)
                            if msg.get("type") == "sentence_start":
                                print(f"  处理后: {msg['text'][:50]}...")
                            elif msg.get("type") == "done":
                                print(f"  ✓ 完成")
                                break
                            elif msg.get("type") == "error":
                                print(f"  ✗ 错误: {msg.get('message')}")
                                break
                    except asyncio.TimeoutError:
                        print(f"  ✓ 完成（超时退出）")
                        break

                await asyncio.sleep(0.3)

    except websockets.exceptions.WebSocketException as e:
        print(f"✗ WebSocket 连接错误: {e}")


async def test_smart_voice_selection():
    """测试智能音色选择"""
    print("\n" + "=" * 60)
    print("测试 3: 智能音色选择")
    print("=" * 60)

    voice_tests = [
        ("Hello, this is English text.", "am_adam", "英文文本（男声→男声）"),
        ("你好，这是中文文本。", "am_adam", "中文文本（男声→双语音色）"),
        ("Hello 你好，this is mixed 中英混合。", "am_adam", "中英混合（男声→双语音色）"),
    ]

    uri = "ws://localhost:9880/ws/tts"

    try:
        async with websockets.connect(uri) as ws:
            for text, user_voice, description in voice_tests:
                print(f"\n测试: {description}")
                print(f"输入: {text[:50]}...")
                print(f"用户指定音色: {user_voice}")

                await ws.send(json.dumps({
                    "text": text,
                    "voice": user_voice,
                    "input_format": "plain"
                }))

                # 接收响应
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
                    except asyncio.TimeoutError:
                        print(f"  ✓ 完成（超时退出）")
                        break

                await asyncio.sleep(0.3)

    except websockets.exceptions.WebSocketException as e:
        print(f"✗ WebSocket 连接错误: {e}")


async def test_sentence_splitting():
    """测试长文本分句处理"""
    print("\n" + "=" * 60)
    print("测试 4: 长文本分句处理")
    print("=" * 60)

    long_text = """
欢迎使用Kokoro TTS API。这是一个功能强大的文本转语音系统。

它支持多种音色，包括女声、男声和双语音色。双语音色可以自动处理中英文混合文本。

您可以使用Markdown格式输入文本。系统会自动清洗格式符号，删除代码块和公式。

特殊符号也会被自动处理。例如，数学符号3×4=12会被读作"3乘以4等于12"。

感谢您的使用！
"""

    uri = "ws://localhost:9880/ws/tts"

    try:
        async with websockets.connect(uri) as ws:
            print(f"输入文本（{len(long_text)} 字符）:")
            print(long_text[:100] + "...")

            await ws.send(json.dumps({
                "text": long_text,
                "voice": "af_maple",
                "input_format": "markdown"
            }))

            # 接收响应
            sentence_count = 0
            total_chunks = 0

            while True:
                try:
                    message = await asyncio.wait_for(ws.recv(), timeout=10.0)

                    if isinstance(message, str):
                        msg = json.loads(message)
                        if msg.get("type") == "sentence_start":
                            sentence_count += 1
                            print(f"\n  句子 {msg['index']}: {msg['text'][:60]}...")
                        elif msg.get("type") == "sentence_end":
                            total_chunks += 1
                        elif msg.get("type") == "done":
                            print(f"\n  ✓ 完成")
                            print(f"    总句子数: {msg.get('total_sentences', sentence_count)}")
                            print(f"    总音频块: {msg.get('total_chunks', total_chunks)}")
                            print(f"    总字节数: {msg.get('total_bytes', 0)}")
                            break
                        elif msg.get("type") == "error":
                            print(f"  ✗ 错误: {msg.get('message')}")
                            break
                except asyncio.TimeoutError:
                    print(f"\n  ✓ 完成（超时退出）")
                    print(f"    已处理句子: {sentence_count}")
                    break

    except websockets.exceptions.WebSocketException as e:
        print(f"✗ WebSocket 连接错误: {e}")


async def test_complex_markdown():
    """测试复杂 Markdown 文档"""
    print("\n" + "=" * 60)
    print("测试 5: 复杂 Markdown 文档")
    print("=" * 60)

    complex_markdown = """
# Kokoro TTS API 使用指南

## 简介
这是一个**非常好用**的文本转语音API！

## 主要功能
- 支持 Markdown 格式
- 智能句子分割
- 数学符号朗读: 3×4=12
- 单位转换: 25℃

## 代码示例
```python
print("Hello, World!")
```

## 链接
访问 [官方网站](https://example.com) 了解更多信息。

## 总结
欢迎使用！
"""

    uri = "ws://localhost:9880/ws/tts"

    try:
        async with websockets.connect(uri) as ws:
            print(f"输入 Markdown 文档（{len(complex_markdown)} 字符）:")
            print(complex_markdown[:150] + "...")

            await ws.send(json.dumps({
                "text": complex_markdown,
                "voice": "af_maple",
                "input_format": "markdown"
            }))

            # 接收响应
            sentence_count = 0
            sentences = []

            while True:
                try:
                    message = await asyncio.wait_for(ws.recv(), timeout=10.0)

                    if isinstance(message, str):
                        msg = json.loads(message)
                        if msg.get("type") == "sentence_start":
                            sentence_count += 1
                            sentences.append(msg['text'])
                            print(f"\n  句子 {msg['index']}: {msg['text'][:60]}...")
                        elif msg.get("type") == "done":
                            print(f"\n  ✓ 完成")
                            print(f"    总句子数: {msg.get('total_sentences', sentence_count)}")
                            break
                        elif msg.get("type") == "error":
                            print(f"  ✗ 错误: {msg.get('message')}")
                            break
                except asyncio.TimeoutError:
                    print(f"\n  ✓ 完成（超时退出）")
                    print(f"    已处理句子: {sentence_count}")
                    break

    except websockets.exceptions.WebSocketException as e:
        print(f"✗ WebSocket 连接错误: {e}")


async def test_http_api():
    """测试 HTTP API（带 Markdown 支持）"""
    print("\n" + "=" * 60)
    print("测试 6: HTTP API (Markdown 支持)")
    print("=" * 60)

    import requests

    test_cases = [
        ("# 测试\n\n这是**粗体**文本。", "markdown", "Markdown 格式"),
        ("这是纯文本。", "plain", "纯文本格式"),
        ("3×4=12，温度25℃", "plain", "特殊符号"),
    ]

    for text, input_format, description in test_cases:
        print(f"\n测试: {description}")
        print(f"输入: {text[:50]}...")

        try:
            response = requests.post(
                "http://localhost:9880/v1/audio/speech",
                json={
                    "model": "tts-1",
                    "input": text,
                    "voice": "alloy",
                    "input_format": input_format,
                    "response_format": "wav"
                }
            )

            if response.status_code == 200:
                print(f"  ✓ 成功，音频大小: {len(response.content)} 字节")
            else:
                print(f"  ✗ 失败，状态码: {response.status_code}")
                print(f"    错误: {response.text}")

        except requests.exceptions.ConnectionError:
            print(f"  ✗ 连接失败，请确保服务正在运行")
            break

        await asyncio.sleep(0.3)


async def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("Markdown TTS 功能测试")
    print("=" * 60)

    print("\n请先确保:")
    print("1. 已安装依赖: pip install websockets")
    print("2. 服务正在运行: uvicorn api:api --host 0.0.0.0 --port 9880 --reload")

    print("\n" + "=" * 60)
    print("选择测试类型:")
    print("1. Markdown 格式清洗")
    print("2. 特殊符号处理")
    print("3. 智能音色选择")
    print("4. 长文本分句处理")
    print("5. 复杂 Markdown 文档")
    print("6. HTTP API 测试")
    print("7. 运行所有测试")
    print("=" * 60)

    choice = input("\n请输入选择 (1-7，默认7): ").strip() or "7"

    tests = {
        "1": test_markdown_cleaning,
        "2": test_special_symbols,
        "3": test_smart_voice_selection,
        "4": test_sentence_splitting,
        "5": test_complex_markdown,
        "6": test_http_api,
        "7": "all"
    }

    if choice == "7":
        print("\n开始运行所有测试...")
        await test_markdown_cleaning()
        await test_special_symbols()
        await test_smart_voice_selection()
        await test_sentence_splitting()
        await test_complex_markdown()
        await test_http_api()
    elif choice in tests:
        test_func = tests[choice]
        if test_func != "all":
            await test_func()
    else:
        print("无效选择")

    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
