import os
from typing import Dict, List
import yaml
import docx
import PyPDF2
import pandas as pd
import requests
from pathlib import Path
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import logging

# 配置日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()

class FileProcessor:
    def __init__(self, rules_path: str = "cursorrules.yaml"):
        # 配置 requests 的重试机制
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # 加载配置文件
        with open(rules_path, 'r', encoding='utf-8') as f:
            self.rules = yaml.safe_load(f)
        
        # 验证支持的文件类型
        self.supported_types = set(self.rules['file_types'])

    def validate_file(self, file_path: str) -> bool:
        """验证文件类型和安全性"""
        # 处理文件扩展名，确保正确处理中文文件名
        file_ext = os.path.splitext(file_path)[1][1:].lower()
        if file_ext not in self.supported_types:
            raise ValueError(f"不支持的文件类型: {file_ext}")
        
        # 实现基本的安全检查
        file_size = os.path.getsize(file_path)
        if file_size > 10 * 1024 * 1024:  # 10MB 限制
            raise ValueError("文件大小超过限制")
        
        return True

    def extract_text(self, file_path: str) -> str:
        """根据文件类型提取文本"""
        file_ext = Path(file_path).suffix[1:].lower()
        
        if file_ext == 'docx':
            return self._process_docx(file_path)
        elif file_ext == 'pdf':
            return self._process_pdf(file_path)
        elif file_ext == 'xlsx':
            return self._process_xlsx(file_path)
        elif file_ext == 'txt':
            return self._process_txt(file_path)
        
        raise ValueError(f"无法处理的文件类型: {file_ext}")

    def _process_docx(self, file_path: str) -> str:
        """处理Word文档"""
        doc = docx.Document(file_path)
        return '\n'.join([paragraph.text for paragraph in doc.paragraphs])

    def _process_pdf(self, file_path: str) -> str:
        """处理PDF文件"""
        text = []
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                text.append(page.extract_text())
        return '\n'.join(text)

    def _process_xlsx(self, file_path: str) -> str:
        """处理Excel文件"""
        df = pd.read_excel(file_path)
        return df.to_string()

    def _process_txt(self, file_path: str) -> str:
        """处理文本文件"""
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()

    def translate_text(self, text: str, source_lang: str, target_lang: str) -> str:
        """调用翻译API"""
        try:
            translation_config = self.rules['translation_rules']
            
            api_key = os.getenv('OPENAI_API_KEY')
            logger.debug(f"API Key length: {len(api_key) if api_key else 'None'}")
            
            headers = {
                'Authorization': f"Bearer {api_key}",
                'Content-Type': 'application/json'
            }
            
            payload = {
                "model": "gpt-3.5-turbo",
                "messages": [
                    {
                        "role": "system",
                        "content": f"You are a translator. Translate the following text from {source_lang} to {target_lang}."
                    },
                    {
                        "role": "user",
                        "content": text
                    }
                ],
                "temperature": 0.7
            }

            logger.debug(f"Sending request to: {os.getenv('TRANSLATION_API_ENDPOINT')}")
            logger.debug(f"Request payload: {payload}")

            try:
                response = self.session.post(
                    os.getenv('TRANSLATION_API_ENDPOINT'),
                    headers=headers,
                    json=payload,
                    timeout=30
                )
                logger.debug(f"Response status code: {response.status_code}")
                logger.debug(f"Response content: {response.text[:200]}...")  # 只显示前200个字符
                
                response.raise_for_status()
            except requests.exceptions.RequestException as e:
                logger.error(f"API请求失败: {str(e)}")
                raise Exception(f"API请求失败: {str(e)}")

            if response.status_code != 200:
                raise Exception(f"翻译请求失败: {response.status_code}")

            return response.json()['choices'][0]['message']['content']
        except Exception as e:
            raise Exception(f"翻译过程出错: {str(e)}") 
