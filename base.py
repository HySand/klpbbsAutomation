import os
import logging
import cloudscraper
import http.cookiejar
from bs4 import BeautifulSoup

class KLPBBSBot:
    def __init__(self, headers):
        self.base_url = "https://klpbbs.com"
        self.headers = headers
        self.session = cloudscraper.create_scraper(
            browser={"browser": "chrome", "platform": "windows", "mobile": False}
        )
        self.session.cookies = http.cookiejar.LWPCookieJar()

    def login(self, username, password):
        post_url = f"{self.base_url}/member.php?mod=logging&action=login&loginsubmit=yes"
        post_data = {"username": username, "password": password}
        res = self.session.post(post_url, data=post_data, headers=self.headers)
        if res.status_code == 200:
            logging.info(f"用户 {username} 登录成功")
            self.headers["Cookie"] = "; ".join([f"{c.name}={c.value}" for c in self.session.cookies])
            return True
        logging.info(f"用户 {username} 登录成功")
        return False

    def get_formhash(self):
        """解析页面获取 Discuz 必需的表单校验码"""
        res = self.session.get(self.base_url, headers=self.headers)
        soup = BeautifulSoup(res.text, "html.parser")
        logout_link = soup.find("a", href=True, string="退出登录")
        if logout_link:
            import re
            match = re.search(r'formhash=([a-z0-9]+)', logout_link['href'])
            if match: return match.group(1)
        return None