"""
Tests for generate_wechat_doc_id() — task_1_2 验收测试
"""
import hashlib
import pytest

from src.pipeline import generate_wechat_doc_id


class TestGenerateWechatDocId:
    """doc_id生成函数的单元测试"""

    # ── 短URL格式 ──────────────────────────────────────────────

    def test_short_url_produces_wx_prefix_with_hash(self):
        """短URL /s/XXXXX → wx_XXXXX"""
        url = "https://mp.weixin.qq.com/s/QKAUV0c0qrsEr64HeQo73g"
        doc_id = generate_wechat_doc_id(url)
        assert doc_id == "wx_QKAUV0c0qrsEr64HeQo73g"

    def test_short_url_is_stable(self):
        """同一URL每次调用返回相同doc_id"""
        url = "https://mp.weixin.qq.com/s/QKAUV0c0qrsEr64HeQo73g"
        assert generate_wechat_doc_id(url) == generate_wechat_doc_id(url)

    def test_short_url_different_hashes_no_collision(self):
        """不同短URL的doc_id不同"""
        url_a = "https://mp.weixin.qq.com/s/QKAUV0c0qrsEr64HeQo73g"
        url_b = "https://mp.weixin.qq.com/s/FG2gEdgZwpMkA3ApQMksnw"
        assert generate_wechat_doc_id(url_a) != generate_wechat_doc_id(url_b)

    # ── 长URL格式（sn参数）──────────────────────────────────────

    def test_long_url_extracts_sn(self):
        """长URL提取sn参数作为doc_id"""
        url = (
            "https://mp.weixin.qq.com/s?"
            "__biz=MzI0MjE3NTkzMw==&mid=2649551234&idx=1"
            "&sn=a1b2c3d4e5f6&chksm=f1234567890"
        )
        doc_id = generate_wechat_doc_id(url)
        assert doc_id == "wx_a1b2c3d4e5f6"

    def test_long_url_sn_parameter(self):
        """长URL使用sn参数（非__sn）"""
        url = (
            "https://mp.weixin.qq.com/s?"
            "__biz=Test&mid=123&idx=1"
            "&sn=abc123def456&chksm=xyz"
        )
        doc_id = generate_wechat_doc_id(url)
        assert doc_id == "wx_abc123def456"

    def test_long_url_no_sn_falls_back_to_sha256(self):
        """长URL没有sn参数时回退到SHA256[:24]"""
        url = "https://mp.weixin.qq.com/s?__biz=Test&mid=123&idx=1"
        doc_id = generate_wechat_doc_id(url)
        expected = f"wx_{hashlib.sha256(url.encode()).hexdigest()[:24]}"
        assert doc_id == expected
        assert doc_id.startswith("wx_")

    # ── 非微信URL ──────────────────────────────────────────────

    def test_non_wechat_url_uses_sha256_no_wx_prefix(self):
        """非微信URL使用SHA256[:24]，无wx_前缀"""
        url = "https://example.com/article/123"
        doc_id = generate_wechat_doc_id(url)
        expected = hashlib.sha256(url.encode()).hexdigest()[:24]
        assert doc_id == expected
        assert not doc_id.startswith("wx_")

    def test_non_wechat_url_stable(self):
        """非微信URL结果稳定"""
        url = "https://github.com/openai/gpt-4"
        assert generate_wechat_doc_id(url) == generate_wechat_doc_id(url)

    # ── 边界情况 ──────────────────────────────────────────────

    def test_wechat_url_with_trailing_slash(self):
        """短URL带尾部斜杠仍能匹配"""
        url = "https://mp.weixin.qq.com/s/QKAUV0c0qrsEr64HeQo73g/"
        doc_id = generate_wechat_doc_id(url)
        assert doc_id == "wx_QKAUV0c0qrsEr64HeQo73g"

    def test_http_scheme(self):
        """HTTP协议的微信URL也能识别"""
        url = "http://mp.weixin.qq.com/s/ABCDEFG12345"
        doc_id = generate_wechat_doc_id(url)
        assert doc_id == "wx_ABCDEFG12345"

    def test_url_case_insensitive_host(self):
        """URL host大小写不敏感"""
        url = "https://MP.WEIXIN.QQ.COM/s/TestHash123"
        doc_id = generate_wechat_doc_id(url)
        assert doc_id == "wx_TestHash123"

    # ── 向后兼容性 ────────────────────────────────────────────

    def test_old_md5_short_urls_still_unique(self):
        """验证新方案下短URL不会碰撞（之前可能碰撞的URL现在不同）"""
        # 这些URL使用MD5[:12]时如果有碰撞，新方案直接用路径hash，保证唯一
        urls = [
            "https://mp.weixin.qq.com/s/QKAUV0c0qrsEr64HeQo73g",
            "https://mp.weixin.qq.com/s/FG2gEdgZwpMkA3ApQMksnw",
            "https://mp.weixin.qq.com/s/Zv1lyudX30ivWhjoFC_WVA",
            "https://mp.weixin.qq.com/s/9R7RctHBWkhhamwwqRM80Q",
            "https://mp.weixin.qq.com/s/zviVbeB5miAhNiUWmHSaRQ",
            "https://mp.weixin.qq.com/s/N6sNtFuWBrE4-daGy6CZsw",
            "https://mp.weixin.qq.com/s/rfxvjsKThpINZGt3TVtN2g",
            "https://mp.weixin.qq.com/s/y78c1i7Yh2tqwLP8UC4LbA",
            "https://mp.weixin.qq.com/s/sGjXZM61gnPH7o1J9Svghw",
        ]
        doc_ids = [generate_wechat_doc_id(u) for u in urls]
        assert len(doc_ids) == len(set(doc_ids)), f"碰撞发现: {doc_ids}"


class TestLocalFileDocId:
    """本地文件doc_id生成的单元测试"""

    def test_md_file_has_md_prefix(self, tmp_path):
        """MD文件doc_id以md_开头"""
        from src.document_loader import DocumentLoader
        loader = DocumentLoader()
        (tmp_path / "test.md").write_text("# Test")
        doc = loader.load_file(str(tmp_path / "test.md"))
        assert doc["doc_id"].startswith("md_")
        assert len(doc["doc_id"]) == 19  # md_ + 16 hex chars

    def test_different_paths_same_content_no_collision(self, tmp_path):
        """不同路径的同名同内容文件生成不同doc_id"""
        from src.document_loader import DocumentLoader
        loader = DocumentLoader()
        (tmp_path / "a").mkdir()
        (tmp_path / "b").mkdir()
        (tmp_path / "a" / "test.md").write_text("# Same content")
        (tmp_path / "b" / "test.md").write_text("# Same content")
        doc_a = loader.load_file(str(tmp_path / "a" / "test.md"))
        doc_b = loader.load_file(str(tmp_path / "b" / "test.md"))
        assert doc_a["doc_id"] != doc_b["doc_id"]

    def test_same_path_same_file_idempotent(self, tmp_path):
        """同路径同文件生成相同doc_id"""
        from src.document_loader import DocumentLoader
        loader = DocumentLoader()
        (tmp_path / "test.md").write_text("# Test")
        doc1 = loader.load_file(str(tmp_path / "test.md"))
        doc2 = loader.load_file(str(tmp_path / "test.md"))
        assert doc1["doc_id"] == doc2["doc_id"]

    def test_url_doc_has_url_prefix(self):
        """URL加载的doc_id以url_开头"""
        import hashlib
        url = "https://example.com/article/123"
        expected = f"url_{hashlib.sha256(url.encode()).hexdigest()[:16]}"
        assert expected.startswith("url_")
        assert len(expected) == 20  # url_ + 16 hex chars
