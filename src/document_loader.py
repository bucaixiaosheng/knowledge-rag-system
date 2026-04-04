"""
文档加载模块：支持 PDF/HTML/Markdown/纯文本/URL
"""
import hashlib
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional
import fitz  # PyMuPDF
from bs4 import BeautifulSoup
import markdown
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class DocumentLoader:
    """统一文档加载器"""

    SUPPORTED_EXTENSIONS = {".pdf", ".html", ".htm", ".md", ".txt", ".mdx"}

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })

    def load_file(self, file_path: str) -> dict:
        """
        加载本地文件
        返回: {doc_id, title, content, doc_type, source, metadata}
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        ext = path.suffix.lower()
        if ext not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(f"不支持的文件格式: {ext}")

        # 生成文档ID
        with open(path, "rb") as f:
            doc_id = hashlib.sha256(f.read()).hexdigest()[:16]

        content = ""
        doc_type = ext.lstrip(".")

        if ext == ".pdf":
            content = self._load_pdf(path)
            doc_type = "pdf"
        elif ext in (".html", ".htm"):
            content = self._load_html(path.read_text(encoding="utf-8"))
            doc_type = "html"
        elif ext in (".md", ".mdx"):
            content = self._load_markdown(path.read_text(encoding="utf-8"))
            doc_type = "markdown"
        elif ext == ".txt":
            content = path.read_text(encoding="utf-8")
            doc_type = "text"

        return {
            "doc_id": doc_id,
            "title": path.stem,
            "content": content,
            "doc_type": doc_type,
            "source": str(path),
            "created_at": datetime.utcnow().isoformat(),
            "metadata": {
                "file_size": path.stat().st_size,
                "file_name": path.name,
            }
        }

    def load_url(self, url: str) -> dict:
        """加载网页URL"""
        resp = self.session.get(url, timeout=30)
        resp.raise_for_status()

        content = self._load_html(resp.text)
        title = BeautifulSoup(resp.text, "html.parser").title
        title_text = title.string.strip() if title and title.string else url

        doc_id = hashlib.sha256(url.encode()).hexdigest()[:16]

        return {
            "doc_id": doc_id,
            "title": title_text,
            "content": content,
            "doc_type": "html",
            "source": url,
            "created_at": datetime.utcnow().isoformat(),
            "metadata": {
                "url": url,
                "fetched_at": datetime.utcnow().isoformat(),
            }
        }

    def load_directory(self, dir_path: str, recursive: bool = True) -> list[dict]:
        """批量加载目录下所有支持格式的文件"""
        docs = []
        path = Path(dir_path)
        pattern = "**/*" if recursive else "*"

        for file in sorted(path.glob(pattern)):
            if file.suffix.lower() in self.SUPPORTED_EXTENSIONS and file.is_file():
                try:
                    doc = self.load_file(str(file))
                    docs.append(doc)
                    logger.info(f"加载文件: {file.name} -> {doc['doc_id']}")
                except Exception as e:
                    logger.error(f"加载失败: {file.name}: {e}")

        return docs

    def _load_pdf(self, path: Path) -> str:
        """PDF转文本"""
        text_parts = []
        with fitz.open(path) as doc:
            for page_num, page in enumerate(doc):
                text = page.get_text("text")
                text_parts.append(text)
        return "\n".join(text_parts)

    def _load_html(self, html_content: str) -> str:
        """HTML转纯文本，保留结构"""
        soup = BeautifulSoup(html_content, "html.parser")
        # 移除脚本和样式
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        return soup.get_text(separator="\n", strip=True)

    def _load_markdown(self, md_content: str) -> str:
        """Markdown转纯文本"""
        html = markdown.markdown(md_content)
        return self._load_html(html)
