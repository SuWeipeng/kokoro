import re

class NumberReplacer:
    # 数字映射表
    num_to_word_ones = {
        '0': 'zero', '1': 'one', '2': 'two', '3': 'three', '4': 'four',
        '5': 'five', '6': 'six', '7': 'seven', '8': 'eight', '9': 'nine'
    }
    num_to_word_teens = {str(k): v for k, v in enumerate([
        'ten', 'eleven', 'twelve', 'thirteen', 'fourteen',
        'fifteen', 'sixteen', 'seventeen', 'eighteen', 'nineteen'
    ], 10)}
    num_to_word_tens = {str(k): v for k, v in enumerate([
        'twenty', 'thirty', 'forty', 'fifty',
        'sixty', 'seventy', 'eighty', 'ninety'
    ], 2)}

    def __init__(self):
        pass

    # 辅助方法
    def _two_digit(self, n):
        if n < 10:
            return self.num_to_word_ones[str(n)]
        elif 10 <= n < 20:
            return self.num_to_word_teens[str(n)]
        else:
            ten_digit = n // 10
            one_digit = n % 10
            word = self.num_to_word_tens[str(ten_digit)]
            if one_digit != 0:
                word += ' ' + self.num_to_word_ones[str(one_digit)]

            return word

    def _three_digit(self, n):
        return ' '.join(filter(None, [
            f"{self.num_to_word_ones[str(n//100)]} hundred" if n//100 else None,
            self._two_digit(n%100) if n%100 else None
        ]))

    def _two_digit_word(self, n_str):
        """专门用于处理两位数字的单词转换"""
        n = int(n_str)
        if n < 10:
            return self.num_to_word_ones[str(n)]
        elif 10 <= n < 20:
            return self.num_to_word_teens[n_str]
        else:
            ten = n_str[0]
            one = n_str[1]
            word = self.num_to_word_tens[ten]
            if one != '0':
                word += ' ' + self.num_to_word_ones[one]
            return word

    def number_to_words(self, num_str):
        try:
            num = float(num_str)
        except ValueError:
            return num_str

        is_negative = num < 0
        if is_negative:
            num = abs(num)

        int_part, dec_part = str(num).split('.')
        int_words = self._int_number_to_words(int(int_part))

        result = ("negative " if is_negative else "") + int_words

        if dec_part != '0':
            result += " point " + " ".join(self.num_to_word_ones[d] for d in dec_part)

        return result.strip()

    def _int_number_to_words(self, n):
        if n == 0:
            return self.num_to_word_ones['0']

        words = []
        for unit, name in [(1_000_000, 'million'), (1_000, 'thousand')]:
            if n // unit:
                words.append(f"{self._three_digit(n//unit)} {name}")
                n %= unit

        if n:
            words.append(self._three_digit(n))

        return " ".join(words)

    def replace_phone_numbers_with_words(self, text):
        def replace_digits(match):
            digits = ''.join(filter(str.isdigit, match.group(0)))
            if not digits:
                return match.group(0)
            words = ' '.join(self.num_to_word_ones[d] for d in digits)
            return words

        # 支持格式如：
        # 123-456-7890
        # (010) 1234 5678
        # +86 138 1234 5678
        phone_pattern = r'(?<![$€£¥¢])(?:(?:\+\d{1,3}[ -])|(?:\(\d{2,4}\)[ -]?)|(?:\d{3,4}[ -]))\d{3,8}'

        return re.sub(phone_pattern, replace_digits, text)

    def replace_ip_addresses_with_words(self, text):
        """
        匹配并替换文本中的 IP 地址为单词形式
        支持 IPv4 格式：xxx.xxx.xxx.xxx (0-255.0-255.0-255.0-255)
        """
        def replace_ip(match):
            ip = match.group(0)
            parts = ip.split('.')
            
            # 验证是否为有效的 IPv4 地址
            try:
                for part in parts:
                    if not (0 <= int(part) <= 255):
                        return ip  # 如果不是有效 IP，返回原文
            except ValueError:
                return ip
            
            # 将每个部分转换为单词
            word_parts = []
            for part in parts:
                # 处理前导零的情况
                if part.startswith('0') and len(part) > 1:
                    # 如果有前导零，逐位读出
                    word_parts.append(' '.join(self.num_to_word_ones[d] for d in part))
                else:
                    word_parts.append(self.number_to_words(part))
            
            return ' dot '.join(word_parts)
        
        # IPv4 地址的正则表达式
        # 匹配 0-255.0-255.0-255.0-255 格式
        ipv4_pattern = r'\b(?:(?:25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])\.){3}(?:25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])\b'
        
        return re.sub(ipv4_pattern, replace_ip, text)

    def find_ip_addresses(self, text):
        """
        查找文本中的所有 IP 地址并返回列表
        """
        ipv4_pattern = r'\b(?:(?:25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])\.){3}(?:25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])\b'
        return re.findall(ipv4_pattern, text)

    def is_valid_ip(self, ip_string):
        """
        验证字符串是否为有效的 IPv4 地址
        """
        parts = ip_string.split('.')
        if len(parts) != 4:
            return False
        
        try:
            for part in parts:
                if not (0 <= int(part) <= 255):
                    return False
                # 检查前导零（除了 "0" 本身）
                if len(part) > 1 and part.startswith('0'):
                    return False
            return True
        except ValueError:
            return False

    def format_year(self, year_str):
        if len(year_str) != 4:
            return self.number_to_words(year_str)
        year_num = int(year_str)
        if 1000 <= year_num <= 1999:
            first_two = year_str[:2]
            last_two = year_str[2:]

            # 特殊处理如 1900 -> nineteen hundred
            if last_two == '00':
                return f"{self._two_digit_word(first_two)} hundred"
            else:
                if int(last_two) < 10:
                    return f"{self._two_digit_word(first_two)} oh {self._two_digit_word(last_two)}"
                else:
                    return f"{self._two_digit_word(first_two)} {self._two_digit_word(last_two)}"
        elif 2000 <= year_num <= 2099:
            if year_num == 2000:
                return "two thousand"
            else:
                return f"two thousand {self.number_to_words(year_str[2:])}"
        else:
            return self.replace_each_digit_with_words(year_str)

    def _replace_money_with_words(self, match):
        sign = match.group(1)  # 负号或空
        currency_symbol = match.group(2).strip('$')  # 货币符号
        amount_str = match.group(3)  # 数字部分

        try:
            amount_value = float(amount_str)
        except ValueError:
            return match.group(0)

        # 添加负号
        if sign:
            amount_value = -amount_value
            amount_str = str(amount_value)
        else:
            amount_str = str(amount_value)

        amount_words = self.number_to_words(amount_str)

        if amount_str.endswith('.0'):
            amount_words = amount_words.replace(' point zero', '')

        currency = {
            '$': 'dollar', 'USD': 'dollar', '€': 'euro',
            'EUR': 'euro', '£': 'pound', 'GBP': 'pound',
            '¥': 'yen', 'CNY': 'yuan'
        }.get(currency_symbol, 'dollar')

        plural_suffix = 's' if abs(amount_value) != 1 else ''

        if amount_value < 0:
            abs_amount_words = amount_words.replace('minus ', '').strip()
            return f"a loss of {abs_amount_words} {currency}{plural_suffix}"
        else:
            return f"{amount_words} {currency}{plural_suffix}"

    def remove_thousand_separators(self, num_str):
        """
        只有当逗号为合法的千分位格式时才移除
        示例：
            - '1,000' → '1000'
            - '-12,345.67' → '-12345.67'
            - '1,00,000'（印度格式） → '100000'
            - 其他情况（如句中逗号）不处理
        """
        # 匹配合法的千分位数字格式
        thousand_pattern = r'^(-)?\d{1,3}(,\d{3})*(\.\d+)?$'

        if re.match(thousand_pattern, num_str):
            return num_str.replace(',', '')
        else:
            return num_str

    def clean_numbers_in_text(self, text):
        """
        遍历文本中的所有数字（支持负数、小数、千分位格式），清理合法的千分位逗号。
        """

        def clean_match(match):
            num_str = match.group(0)
            return self.remove_thousand_separators(num_str)

        # 匹配所有可能带千分位逗号的数字
        return re.sub(r'-?\d{1,3}(?:,\d{3})*(?:\.\d+)?', clean_match, text)

    def replace_list_number_with_words(self, text):
        # 匹配带标点的编号格式（支持 . , ) ] } 等）
        def replace(match):
            num_str = match.group(1)
            suffix = match.group(2)
            words = self.number_to_words(num_str)
            return f"{words}{suffix}"

        # 支持格式如：1., 2), 3], 4}, 5 
        return re.sub(r'(\d+)([.\)\]\}\s]+)', replace, text)

    def replace_numbers_with_words(self, text, year_mode=False):
        def replace_match(match):
            result = None
            num_str = match.group(0)

            is_negative = num_str.startswith('-')
            if is_negative:
                num_str = num_str[1:]

            if year_mode and num_str.isdigit() and 1000 <= int(num_str) <= 9999:
                result = self.format_year(num_str)
            else:
                result = ("negative " if is_negative else "") + self.number_to_words(num_str)
            return result

        # 替换货币符号
        text = re.sub(
            r'(?<![\w.,:])\s*(-?)\s*([\$€£¥USD EUR GBP CNY])\s*(\d+(?:\.\d+)?)(?=\b|[\s,.;:?!]|$)',
            self._replace_money_with_words,
            text
        )

        # 更精确的数字匹配正则（支持负数和小数）
        text = re.sub(
            r'(?<![\d.])-?\d+(?:\.\d+)?(?!\d)',
            replace_match,
            text
        )

        return ' '.join(text.split())

    def replace_single_digits_with_words(self, text):
        return re.sub(r'\b\d\b', lambda m: self.num_to_word_ones[m.group(0)], text)

    def replace_each_digit_with_words(self, text):
        return re.sub(r'\d', lambda m: self.num_to_word_ones[m.group(0)] + ' ', text).rstrip()


class SpecialSymbolProcessor:
    """特殊符号处理器，处理数学符号、单位符号、货币符号等"""

    def __init__(self, language: str = 'auto'):
        """
        初始化特殊符号处理器

        Args:
            language: 'zh' (中文), 'en' (英文), 'auto' (自动检测)
        """
        self.language = language

    def detect_language(self, text: str) -> str:
        """
        自动检测文本语言

        Args:
            text: 输入文本

        Returns:
            'zh' 或 'en'
        """
        if not text:
            return 'en'

        chinese_count = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        total_chars = len(text)

        if total_chars > 0 and chinese_count / total_chars > 0.3:
            return 'zh'
        return 'en'

    def process(self, text: str) -> str:
        """
        处理文本中的所有特殊符号

        Args:
            text: 输入文本

        Returns:
            处理后的文本
        """
        if not text:
            return text

        # 自动检测语言
        lang = self.language if self.language != 'auto' else self.detect_language(text)

        # 按顺序处理
        text = self.process_currency_extended(text, lang)
        text = self.process_math_symbols(text, lang)
        text = self.process_unit_symbols(text, lang)

        return text

    def process_math_symbols(self, text: str, language: str = None) -> str:
        """
        数学符号转换
        ± → 正负号 / plus minus
        × → 乘以 / times
        ÷ → 除以 / divided by
        = → 等于 / equals
        ≠ → 不等于 / not equal to
        < → 小于 / less than
        > → 大于 / greater than
        ≤ → 小于等于 / less than or equal to
        ≥ → 大于等于 / greater than or equal to
        """
        if language is None:
            language = self.language if self.language != 'auto' else self.detect_language(text)

        # 数学符号映射
        if language == 'zh':
            mappings = [
                (r'(\d+)\s*×\s*(\d+)', r'\1乘以\2'),
                (r'(\d+)\s*÷\s*(\d+)', r'\1除以\2'),
                (r'±\s*(\d+)', r'正负\1'),
                (r'(\d+)\s*±', r'\1正负'),
                (r'≠', '不等于'),
                (r'≤', '小于等于'),
                (r'≥', '大于等于'),
                (r'(?<!\w)=(?!\w)', '等于'),
                (r'<', '小于'),
                (r'>', '大于'),
            ]
        else:  # English
            mappings = [
                (r'(\d+)\s*×\s*(\d+)', r'\1 times \2'),
                (r'(\d+)\s*÷\s*(\d+)', r'\1 divided by \2'),
                (r'±\s*(\d+)', r'plus minus \1'),
                (r'(\d+)\s*±', r'\1 plus minus'),
                (r'≠', 'not equal to'),
                (r'≤', 'less than or equal to'),
                (r'≥', 'greater than or equal to'),
                (r'(?<!\w)=(?!\w)', 'equals'),
                (r'<', 'less than'),
                (r'>', 'greater than'),
            ]

        for pattern, replacement in mappings:
            text = re.sub(pattern, replacement, text)

        return text

    def process_unit_symbols(self, text: str, language: str = None) -> str:
        """
        单位符号转换
        % → 百分之 / percent
        ° → 度 / degrees
        ℃ → 摄氏度 / degrees Celsius
        ℉ → 华氏度 / degrees Fahrenheit
        """
        if language is None:
            language = self.language if self.language != 'auto' else self.detect_language(text)

        # 单位符号映射
        if language == 'zh':
            mappings = [
                (r'(\d+)%', r'百分之\1'),
                (r'(\d+)\s*°', r'\1度'),
                (r'(\d+)℃', r'\1摄氏度'),
                (r'(\d+)°C', r'\1摄氏度'),
                (r'(\d+)°c', r'\1摄氏度'),
                (r'(\d+)℉', r'\1华氏度'),
                (r'(\d+)°F', r'\1华氏度'),
            ]
        else:  # English
            mappings = [
                (r'(\d+)%', r'\1 percent'),
                (r'(\d+)\s*°', r'\1 degrees'),
                (r'(\d+)℃', r'\1 degrees Celsius'),
                (r'(\d+)°C', r'\1 degrees Celsius'),
                (r'(\d+)°c', r'\1 degrees Celsius'),
                (r'(\d+)℉', r'\1 degrees Fahrenheit'),
                (r'(\d+)°F', r'\1 degrees Fahrenheit'),
            ]

        for pattern, replacement in mappings:
            text = re.sub(pattern, replacement, text)

        return text

    def process_currency_extended(self, text: str, language: str = None) -> str:
        """
        扩展货币符号处理
        新增: ₽卢布, ₹卢比, ₩韩元, ₿比特币
        """
        if language is None:
            language = self.language if self.language != 'auto' else self.detect_language(text)

        # 货币符号映射
        if language == 'zh':
            mappings = [
                (r'₽\s*(\d+(?:\.\d+)?)', r'\1卢布'),
                (r'(\d+(?:\.\d+)?)\s*₽', r'\1卢布'),
                (r'₹\s*(\d+(?:\.\d+)?)', r'\1卢比'),
                (r'(\d+(?:\.\d+)?)\s*₹', r'\1卢比'),
                (r'₩\s*(\d+(?:\.\d+)?)', r'\1韩元'),
                (r'(\d+(?:\.\d+)?)\s*₩', r'\1韩元'),
                (r'₿\s*(\d+(?:\.\d+)?)', r'\1比特币'),
                (r'(\d+(?:\.\d+)?)\s*₿', r'\1比特币'),
            ]
        else:  # English
            mappings = [
                (r'₽\s*(\d+(?:\.\d+)?)', r'\1 rubles'),
                (r'(\d+(?:\.\d+)?)\s*₽', r'\1 rubles'),
                (r'₹\s*(\d+(?:\.\d+)?)', r'\1 rupees'),
                (r'(\d+(?:\.\d+)?)\s*₹', r'\1 rupees'),
                (r'₩\s*(\d+(?:\.\d+)?)', r'\1 won'),
                (r'(\d+(?:\.\d+)?)\s*₩', r'\1 won'),
                (r'₿\s*(\d+(?:\.\d+)?)', r'\1 bitcoins'),
                (r'(\d+(?:\.\d+)?)\s*₿', r'\1 bitcoins'),
            ]

        for pattern, replacement in mappings:
            text = re.sub(pattern, replacement, text)

        return text