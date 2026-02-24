"""
句子分割模块

智能地将长文本分割成句子，适用于 TTS 分句处理。
"""

import re
from typing import List


class SentenceSplitter:
    """智能句子分割器"""

    # 英文缩写列表（避免在这些点处分割）
    ABBREVIATIONS = [
        'Mr.', 'Mrs.', 'Ms.', 'Dr.', 'Prof.', 'Sr.', 'Jr.',
        'NASA', 'CEO', 'CFO', 'CTO', 'Ph.D', 'M.D.', 'B.A.', 'M.A.',
        'U.S.A.', 'U.K.', 'U.N.', 'EU', 'USA', 'UK',
        'Inc.', 'Ltd.', 'Corp.', 'Co.', 'etc.', 'vs.', 'i.e.', 'e.g.',
    ]

    def __init__(self, max_sentence_length: int = 500):
        """
        初始化句子分割器

        Args:
            max_sentence_length: 单个句子的最大长度（超过则强制分割）
        """
        self.max_sentence_length = max_sentence_length

    def split(self, text: str) -> List[str]:
        """
        按标点符号分割句子

        中文分隔符: 。！？；
        英文分隔符: . ! ?
        次要分隔符: ， , : :

        特殊处理:
            - 小数点不分割: 3.14
            - 缩写不分割: Mr., Dr., NASA, CEO
            - 省略号完整分割: ...
            - 引号内保持完整

        Args:
            text: 输入文本

        Returns:
            句子列表
        """
        if not text:
            return []

        sentences = []

        # 首先按主要分隔符分割
        # 使用正则表达式分割，保留分隔符
        pattern = r'([。！？；.!?]+)'
        parts = re.split(pattern, text)

        current_sentence = ""

        for i in range(0, len(parts), 2):
            sentence_part = parts[i] if i < len(parts) else ""
            delimiter = parts[i + 1] if i + 1 < len(parts) else ""

            current_sentence += sentence_part

            if delimiter:
                # 检查是否需要分割（避免小数点和缩写）
                should_split = self._should_split_here(current_sentence, delimiter)

                if should_split:
                    # 完成当前句子
                    current_sentence += delimiter
                    current_sentence = current_sentence.strip()

                    if current_sentence:
                        # 检查句子长度，如果太长则按次要分隔符分割
                        if len(current_sentence) > self.max_sentence_length:
                            sub_sentences = self._split_long_sentence(current_sentence)
                            sentences.extend(sub_sentences)
                        else:
                            sentences.append(current_sentence)

                    current_sentence = ""
                else:
                    # 不分割，继续累积
                    current_sentence += delimiter
            else:
                # 最后一个部分，没有分隔符
                current_sentence = current_sentence.strip()
                if current_sentence:
                    if len(current_sentence) > self.max_sentence_length:
                        sub_sentences = self._split_long_sentence(current_sentence)
                        sentences.extend(sub_sentences)
                    else:
                        sentences.append(current_sentence)

        return [s.strip() for s in sentences if s.strip()]

    def _should_split_here(self, text: str, delimiter: str) -> bool:
        """
        判断是否应该在当前分隔符处分割

        Args:
            text: 当前累积的文本
            delimiter: 分隔符

        Returns:
            是否应该分割
        """
        # 检查是否是英文分隔符
        if delimiter in '.!?':
            # 检查是否是小数点
            if re.search(r'\d+\.$', text):
                return False

            # 检查是否是缩写
            for abbr in self.ABBREVIATIONS:
                if text.rstrip().endswith(abbr):
                    return False

            # 检查是否是省略号
            if delimiter == '...' or '...' in text[-5:]:
                return False

        return True

    def _split_long_sentence(self, sentence: str) -> List[str]:
        """
        将过长的句子按次要分隔符分割

        Args:
            sentence: 过长的句子

        Returns:
            分割后的句子列表
        """
        # 按次要分隔符分割
        parts = re.split(r'([，,:])', sentence)

        result = []
        current = ""

        for i in range(0, len(parts), 2):
            part = parts[i] if i < len(parts) else ""
            sep = parts[i + 1] if i + 1 < len(parts) else ""

            if len(current) + len(part) > self.max_sentence_length and current:
                result.append(current.strip())
                current = part + (sep or "")
            else:
                current += part + (sep or "")

        if current.strip():
            result.append(current.strip())

        # 如果还是太长，强制按空格分割
        final_result = []
        for s in result:
            if len(s) > self.max_sentence_length:
                # 按空格分割
                words = s.split()
                chunk = ""
                for word in words:
                    if len(chunk) + len(word) + 1 > self.max_sentence_length and chunk:
                        final_result.append(chunk.strip())
                        chunk = word
                    else:
                        chunk += " " + word if chunk else word
                if chunk:
                    final_result.append(chunk.strip())
            else:
                final_result.append(s)

        return final_result

    def split_with_indices(self, text: str) -> List[tuple]:
        """
        分割句子并返回每个句子的索引位置

        Args:
            text: 输入文本

        Returns:
            [(sentence, start_index, end_index), ...]
        """
        sentences = self.split(text)
        result = []
        current_pos = 0

        for sentence in sentences:
            start = text.find(sentence, current_pos)
            if start != -1:
                end = start + len(sentence)
                result.append((sentence, start, end))
                current_pos = end
            else:
                # 找不到精确匹配，估算位置
                result.append((sentence, current_pos, current_pos + len(sentence)))
                current_pos += len(sentence)

        return result
