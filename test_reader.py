import json, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
import httpx
from reader import read_article, validate_url

class Tests(unittest.TestCase):
    def test_url_policy(self):
        for u in ["file:///etc/passwd","http://example.com","https://127.0.0.1","https://x:y@example.com","https://example.com:444"]:
            with self.assertRaises(ValueError): validate_url(u)
    def test_markdown_archive(self):
        md="# 研究\n\n|方法|证据|\n|---|---|\n|比较|17|"
        def handler(req): return httpx.Response(200,json={"data":{"title":"研究","url":"https://example.com","content":md}})
        with tempfile.TemporaryDirectory() as d, httpx.Client(transport=httpx.MockTransport(handler)) as c:
            a=read_article("https://example.com",client=c,archive_dir=Path(d)); b=read_article("https://example.com",client=c,archive_dir=Path(d))
            self.assertEqual(a["saved_file"],b["saved_file"]); self.assertTrue(Path(a["saved_file"]).read_text().endswith(md))
    def test_failures(self):
        for payload in [{"data":{"content":""}},{"data":{"content":"x","warning":"CAPTCHA required"}}]:
            with httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(200,json=payload))) as c:
                with self.assertRaises(ValueError): read_article("https://example.com",client=c)
if __name__ == "__main__": unittest.main()
