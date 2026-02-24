"""
Markdown 清洗模块

从 Markdown 文本中提取纯文本，去除格式符号，删除代码块和公式。
"""

import re
from typing import Optional


class MarkdownCleaner:
    """清洗 Markdown 格式，提取纯文本"""

    # 正则表达式模式
    HEADING = r'^#{1,6}\s+(.+)$'
    BOLD = r'\*\*(.+?)\*\*'
    ITALIC = r'\*(.+?)\*'
    STRIKETHROUGH = r'~~(.+?)~~'
    UNORDERED_LIST = r'^[\-\*+]\s+(.+)$'
    ORDERED_LIST = r'^\d+[\.\)]\s+(.+)$'
    BLOCKQUOTE = r'^>\s+(.+)$'
    INLINE_CODE = r'`([^`]+)`'
    CODE_BLOCK = r'```[\w]*\n[\s\S]+?```'
    INLINE_MATH = r'\$[^$]+\$'
    BLOCK_MATH = r'\$\$[^$]+\$\$'
    DISPLAY_MATH = r'\\\[^\s]+?\\\]'
    LINK = r'\[([^\]]+)\]\([^\)]+\)'
    IMAGE = r'!\[([^\]]*)\]\([^\)]+\)'
    HORIZONTAL_RULE = r'^[\-\*_]{3,}$'
    STRANGE_SYMBOLS = r'[^\w\s\u4e00-\u9fff\u3000-\u303f\uff00-\uffef。！？，、；：.""''(),.!?;:<>+=\/\\\-]'

    def __init__(self, preserve_images: bool = False):
        """
        初始化 Markdown 清洗器

        Args:
            preserve_images: 是否保留图片描述（默认 False，完全删除图片）
        """
        self.preserve_images = preserve_images

    def clean(self, text: str) -> str:
        """
        清洗 Markdown 文本

        清洗规则:
            - 标题 # ## → 去除 # 号
            - 粗体 **text** → text
            - 斜体 *text* → text
            - 删除线 ~~text~~ → text
            - 列表 - item / 1. item → item
            - 引用 > text → text
            - 代码行 `code` → code
            - 代码块 → 完全删除
            - Latex 公式 $..$ → "公式"
            - 链接 [text](url) → text
            - 图片 ![alt](url) → "[图片: alt]" (或完全删除)
            - 表格 |a|b| → a, b
            - 分隔线 --- → 删除
            - 容错：删除剩余的奇怪符号

        Args:
            text: Markdown 文本

        Returns:
            清洗后的纯文本
        """
        if not text:
            return ""

        # 按行处理（用于行级模式）
        lines = text.split('\n')
        cleaned_lines = []

        for line in lines:
            # 1. 删除代码块（整行）
            if re.match(r'.*```.*', line):
                continue

            # 2. 删除分隔线
            if re.match(self.HORIZONTAL_RULE, line.strip()):
                continue

            # 3. 删除 Latex 公式（替换为"公式"）
            line = re.sub(self.BLOCK_MATH, '公式', line)
            line = re.sub(self.INLINE_MATH, '公式', line)
            line = re.sub(self.DISPLAY_MATH, '公式', line)

            # 4. 处理标题（去除 # 号）
            line = re.sub(self.HEADING, r'\1', line)

            # 5. 处理列表（去除列表符号）
            line = re.sub(self.UNORDERED_LIST, r'\1', line)
            line = re.sub(self.ORDERED_LIST, r'\1', line)

            # 6. 处理引用（去除 > 符号）
            line = re.sub(self.BLOCKQUOTE, r'\1', line)

            # 7. 处理链接和图片
            line = re.sub(self.LINK, r'\1', line)

            if self.preserve_images:
                line = re.sub(self.IMAGE, r'[图片: \1]', line)
            else:
                line = re.sub(self.IMAGE, '', line)

            # 8. 处理行内代码（去除反引号）
            line = re.sub(self.INLINE_CODE, r'\1', line)

            # 9. 处理粗体、斜体、删除线
            line = re.sub(self.BOLD, r'\1', line)
            line = re.sub(self.ITALIC, r'\1', line)
            line = re.sub(self.STRIKETHROUGH, r'\1', line)

            # 10. 处理表格（将 | 替换为逗号或空格）
            if '|' in line:
                # 移除表格边界的 |
                line = line.strip('|')
                # 将 | 替换为逗号
                line = re.sub(r'\s*\|\s*', ', ', line)

            cleaned_lines.append(line)

        # 合并行
        result = '\n'.join(cleaned_lines)

        # 11. 容错：删除剩余的奇怪符号（保留中文、英文、基本标点）
        # 只删除明显的垃圾符号，不过度清理
        result = re.sub(self.STRANGE_SYMBOLS, '', result)

        # 12. 清理多余的空白
        result = re.sub(r'\n{3,}', '\n\n', result)  # 最多保留两个换行
        result = re.sub(r'[ \t]{2,}', ' ', result)  # 多个空格合并为一个
        result = result.strip()

        return result

    def clean_inline(self, text: str) -> str:
        """
        清洗单行 Markdown 文本（用于不保留换行的场景）

        Args:
            text: Markdown 文本

        Returns:
            清洗后的单行文本
        """
        cleaned = self.clean(text)
        # 将换行替换为空格
        cleaned = re.sub(r'\s+', ' ', cleaned)
        return cleaned.strip()
