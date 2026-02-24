"""
WebSocket TTS Simple Test Script
简单的WebSocket TTS测试脚本（不播放音频，只测试连接）

Requirements:
    pip install websockets

Usage:
    python test_websocket_simple.py
"""
import asyncio
import websockets
import json


async def test_websocket():
    """测试WebSocket TTS接口"""
    uri = "ws://localhost:9880/ws/tts"

    print("=== WebSocket TTS 简单测试 ===")
    print(f"正在连接到 {uri}...")

    try:
        async with websockets.connect(uri) as ws:
            print("✓ 连接成功!")

            # 发送测试文本
            test_request = {
                "text": "你好，这是一个WebSocket测试。This is a test.",
                "voice": "af_heart",
                "speed": 1.0
            }

            print(f"发送请求: {test_request['text'][:50]}...")
            await ws.send(json.dumps(test_request))

            # 统计接收到的音频块
            chunk_count = 0
            total_bytes = 0

            while True:
                message = await ws.recv()

                # 检查消息类型（文本还是二进制）
                if isinstance(message, bytes):
                    # 音频数据（二进制）
                    chunk_count += 1
                    total_bytes += len(message)
                    print(f"收到音频块 #{chunk_count}: {len(message)} 字节")
                else:
                    # 文本消息（JSON）
                    try:
                        msg = json.loads(message)
                        if msg.get("type") == "done":
                            print(f"\n✓ 完成!")
                            print(f"  音频块数量: {msg.get('chunks', chunk_count)}")
                            print(f"  总字节数: {msg.get('total_bytes', total_bytes)} 字节")
                            print(f"  总大小: {msg.get('total_bytes', total_bytes)/1024:.2f} KB")
                            break
                        elif msg.get("type") == "error":
                            print(f"\n✗ 错误: {msg.get('message')}")
                            break
                    except json.JSONDecodeError:
                        pass

    except websockets.exceptions.WebSocketException as e:
        print(f"✗ WebSocket 连接错误: {e}")
        print("\n请确保服务正在运行:")
        print("  1. 双击 start_service.bat")
        print("  2. 或运行: uvicorn api:api --host 0.0.0.0 --port 9880 --reload")
    except Exception as e:
        print(f"✗ 错误: {e}")


async def test_multiple_requests():
    """测试多个连续请求"""
    uri = "ws://localhost:9880/ws/tts"

    print("\n=== 多请求测试 ===")

    test_cases = [
        {"text": "你好，我是第一个测试。", "voice": "af_heart"},
        {"text": "This is the second test.", "voice": "am_adam"},
        {"text": "你好，这是第三个测试。", "voice": "af_maple"},
    ]

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n测试 #{i}: {test_case['text'][:30]}...")

        try:
            async with websockets.connect(uri) as ws:
                await ws.send(json.dumps(test_case))

                chunk_count = 0
                while True:
                    message = await ws.recv()

                    if isinstance(message, bytes):
                        # 音频数据
                        chunk_count += 1
                    else:
                        # JSON消息
                        try:
                            msg = json.loads(message)
                            if msg.get("type") == "done":
                                print(f"  ✓ 完成 ({msg.get('chunks')} 个音频块)")
                                break
                            elif msg.get("type") == "error":
                                print(f"  ✗ 错误: {msg.get('message')}")
                                break
                        except json.JSONDecodeError:
                            pass

                # 短暂等待
                await asyncio.sleep(0.5)

        except Exception as e:
            print(f"  ✗ 失败: {e}")


async def test_different_voices():
    """测试不同音色"""
    uri = "ws://localhost:9880/ws/tts"

    print("\n=== 不同音色测试 ===")

    voices = [
        ("af_heart", "女声 (Heart)"),
        ("am_adam", "男声 (Adam)"),
        ("af_maple", "双语声 (Maple)"),
        ("af_sol", "双语声 (Sol)"),
    ]

    for voice, description in voices:
        print(f"\n测试音色: {voice} - {description}")

        try:
            async with websockets.connect(uri) as ws:
                await ws.send(json.dumps({
                    "text": f"这是{description}的测试。",
                    "voice": voice,
                    "speed": 1.0
                }))

                chunk_count = 0
                while True:
                    message = await ws.recv()

                    if isinstance(message, bytes):
                        # 音频数据
                        chunk_count += 1
                    else:
                        # JSON消息
                        try:
                            msg = json.loads(message)
                            if msg.get("type") == "done":
                                print(f"  ✓ 完成")
                                break
                        except json.JSONDecodeError:
                            pass

        except Exception as e:
            print(f"  ✗ 失败: {e}")


if __name__ == "__main__":
    print("=" * 50)
    print("选择测试类型:")
    print("1. 简单测试")
    print("2. 多请求测试")
    print("3. 不同音色测试")
    print("=" * 50)

    choice = input("\n请输入选择 (1/2/3，默认1): ").strip() or "1"

    if choice == "1":
        asyncio.run(test_websocket())
    elif choice == "2":
        asyncio.run(test_multiple_requests())
    elif choice == "3":
        asyncio.run(test_different_voices())
    else:
        print("无效选择，运行简单测试...")
        asyncio.run(test_websocket())

    print("\n" + "=" * 50)
    print("测试完成!")
