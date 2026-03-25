import logging
import re
import time
from datetime import date, timedelta

import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

from requests import RequestException


def fetch_from_checkerproxy(min_count: int = 100, max_lookback_days: int = 7) -> list[str]:
    day = date.today()
    for _ in range(max_lookback_days):
        day = day - timedelta(days=1)
        proxy_url = f'https://api.checkerproxy.net/v1/landing/archive/{day.strftime("%Y-%m-%d")}'
        print(f'getting proxies from {proxy_url} ...')
        try:
            response = requests.get(proxy_url, timeout=15)
            response.raise_for_status()
        except RequestException as err:
            print(f'checkerproxy unavailable: {err}')
            continue

        data = response.json()
        proxies_obj = data['data']['proxyList']
        if isinstance(proxies_obj, list):
            total_proxies = proxies_obj
        elif isinstance(proxies_obj, dict):
            total_proxies = [proxy for proxy in proxies_obj.values() if proxy]
        else:
            raise TypeError(f'Unexpected type of $.data.proxyList: {type(proxies_obj)}')

        if len(total_proxies) >= min_count:
            print(f'successfully get {len(total_proxies)} proxies from checkerproxy')
            return total_proxies
        print(f'only have {len(total_proxies)} proxies from checkerproxy')
    return []


def fetch_from_proxyscrape() -> list[str]:
    proxy_url = ('https://api.proxyscrape.com/v2/?request=getproxies&protocol=http'
                 '&timeout=2000&country=all')
    print(f'getting proxies from {proxy_url} ...')
    response = requests.get(proxy_url, timeout=15)
    response.raise_for_status()
    proxies = [line.strip() for line in response.text.splitlines() if line.strip()]
    print(f'successfully get {len(proxies)} proxies from proxyscrape')
    return proxies


def fetch_from_proxylistdownload() -> list[str]:
    proxy_url = 'https://www.proxy-list.download/api/v1/get?type=http'
    print(f'getting proxies from {proxy_url} ...')
    response = requests.get(proxy_url, timeout=15)
    response.raise_for_status()
    proxies = [line.strip() for line in response.text.splitlines() if line.strip()]
    print(f'successfully get {len(proxies)} proxies from proxy-list.download')
    return proxies


def fetch_from_geonode(limit: int = 300) -> list[str]:
    proxy_url = 'https://proxylist.geonode.com/api/proxy-list'
    params = {
        'limit': limit,
        'page': 1,
        'sort_by': 'lastChecked',
        'sort_type': 'desc',
        'protocols': 'http',
    }
    print(f'getting proxies from {proxy_url} ...')
    response = requests.get(proxy_url, params=params, timeout=15)
    response.raise_for_status()
    data = response.json().get('data', [])
    proxies = [f"{item['ip']}:{item['port']}" for item in data if item.get('ip') and item.get('port')]
    print(f'successfully get {len(proxies)} proxies from geonode')
    return proxies


def fetch_plaintext_proxy_list(url: str, label: str) -> list[str]:
    print(f'getting proxies from {url} ...')
    response = requests.get(url, timeout=15)
    response.raise_for_status()
    proxies = [line.strip() for line in response.text.splitlines() if line.strip() and ':' in line]
    print(f'successfully get {len(proxies)} proxies from {label}')
    return proxies


def fetch_from_speedx() -> list[str]:
    return fetch_plaintext_proxy_list(
        'https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt',
        'TheSpeedX GitHub list')


def fetch_from_monosans() -> list[str]:
    return fetch_plaintext_proxy_list(
        'https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt',
        'monosans GitHub list')


def get_total_proxies() -> list[str]:
    fetchers = [
        ('checkerproxy', fetch_from_checkerproxy),
        ('proxyscrape', fetch_from_proxyscrape),
        ('proxy-list.download', fetch_from_proxylistdownload),
        ('geonode', fetch_from_geonode),
        ('speedx', fetch_from_speedx),
        ('monosans', fetch_from_monosans),
    ]
    all_proxies: set[str] = set()
    for name, fetcher in fetchers:
        try:
            proxies = fetcher()
        except RequestException as err:
            print(f'{name} source failed: {err}')
            continue
        except Exception as err:
            print(f'{name} source error: {err}')
            continue
        for proxy in proxies:
            all_proxies.add(proxy)
        if len(all_proxies) >= 500:
            break
    if all_proxies:
        print(f'collected {len(all_proxies)} proxies from available sources')
        return list(all_proxies)
    raise RuntimeError('failed to fetch proxies from all sources')


class KLPBBSTasks:
    def __init__(self, bot):
        self.bot = bot

    def daily_sign_in(self):
        """签到逻辑"""
        res = self.bot.session.get(self.bot.base_url, headers=self.bot.headers)
        soup = BeautifulSoup(res.text, "html.parser")
        a_tag = soup.find("a", class_="midaben_signpanel JD_sign")
        if a_tag:
            sign_url = f"{self.bot.base_url}/{a_tag['href']}"
            self.bot.session.get(sign_url, headers=self.bot.headers)
            logging.info("签到请求已发送")
        else:
            logging.info("今日可能已签到")

    def reply_thread(self, tid, formhash, message="欢迎大家来玩"):
        logging.info(f"准备在帖子内发送回复: {message}")

        reply_url = f"{self.bot.base_url}/forum.php?mod=post&action=reply&tid={tid}&replysubmit=yes&infloat=yes&handlekey=fastpost&inajax=1"

        post_data = {
            "formhash": formhash,
            "usesig": "1",
            "subject": "",
            "message": message,
            "posttime": int(time.time()),
        }

        try:
            response = self.bot.session.post(reply_url, data=post_data, headers=self.bot.headers)

            if "回复发布成功" in response.text or "succeed" in response.text:
                logging.info("✅ 回复发送成功！")
                return True
            elif "非常抱歉，您两次发表间隔少于" in response.text:
                logging.warning("❌ 触发灌水保护，发送间隔太短。")
            else:
                logging.error(f"❌ 回复失败，返回内容: {response.text[:150]}")
        except Exception as e:
            logging.error(f"回复请求异常: {e}")

        return False

    def buy_magic(self, formhash, mid = "bump"):
        if not formhash:
            logging.warning("未获取到 formhash，跳过购买道具")
            return
        url = f"{self.bot.base_url}/home.php?mod=magic&action=shop&infloat=yes&inajax=1"
        data = {
            "formhash": formhash,
            "handlekey": "magics",
            "operation": "buy",
            "mid": mid,
            "magicnum": 1,
            "operatesubmit": "yes"
        }
        res = self.bot.session.post(url, data=data, headers=self.bot.headers)
        if res.status_code == 200:
            logging.info(f"道具 {mid} 购买成功")
        else:
            logging.warning("购买失败")

    def bump_thread(self, tid, formhash):
        if not formhash:
            logging.warning("未获取到 formhash，跳过顶贴")
            return
        url = f"{self.bot.base_url}/home.php?mod=magic&action=mybox&infloat=yes&inajax=1"
        data = {
            "formhash": formhash,
            "handlekey": "a_bump",
            "operation": "use",
            "magicid": "10",
            "tid": tid,
            "usesubmit": "yes",
            "idtype": "tid",
            "id": tid
        }
        res = self.bot.session.post(url, data=data, headers=self.bot.headers)
        if res.status_code == 200:
            logging.info(f"帖子 {tid} 顶贴成功")
        else:
            logging.warning("顶贴失败，检查是否有提升卡或冷却中")

    def should_bump(self, tid, forum_id=56):
        url = f"{self.bot.base_url}/forum-{forum_id}-1.html"
        try:
            res = self.bot.session.get(url, headers=self.bot.headers, timeout=10)
            thread_ids = re.findall(r'id="normalthread_(\d+)"', res.text)

            if str(tid) in thread_ids:
                position = thread_ids.index(str(tid)) + 1
                logging.info(f"📍 帖子 {tid} 当前位于第 {position} 位")
                return position > 8
            else:
                logging.info(f"❌ 帖子 {tid} 不在第一页")
                return True

        except Exception as e:
            logging.error(f"访问板块页面出错: {e}")
            return True

    def _auth_request(self, action="apply"):
        """
        使用主账号 Session 执行操作 (接取或领奖)
        这里不走代理，直接使用 self.bot.session
        """
        url = f"{self.bot.base_url}/home.php?mod=task&do={action}&id=1"
        try:
            res = self.bot.session.get(url, headers=self.bot.headers, timeout=15)
            if action == "apply":
                success = "任务申请成功" in res.text
                if not success:
                    logging.info("[主账号] 任务接取未直接成功，正在检查是否有未完成的任务...")
                    success = self._check_doing_tasks()
                logging.info(f"[主账号] 任务接取结果: {success}")
                return success
            if action == "draw":
                success = "请注意查收" in res.text
                logging.info(f"[主账号] 奖励领取结果: {success}")
                return success
        except Exception as e:
            logging.error(f"[主账号] 操作 {action} 异常: {e}")
        return False

    def _check_doing_tasks(self):
        """
        检查“进行中的任务”列表
        """
        doing_url = f"{self.bot.base_url}/home.php?mod=task&item=doing"
        try:
            res = self.bot.session.get(doing_url, headers=self.bot.headers, timeout=15)
            if 'id=1"' in res.text or "do=draw&id=1" in res.text:
                logging.info("[主账号] 发现任务 ID 1 已在进行中列表中")
                return True
            # if "立即申请" not in res.text and "进行中的任务" in res.text:
            #     return True

    except Exception as e:
        logging.error(f"[主账号] 检查进行中任务异常: {e}")
    
    return False

    def _proxy_click(self, proxy_url):
        proxies = {"http": proxy_url, "https": proxy_url}
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36 Edg/116.0.1938.81",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Referer": "https://klpbbs.com/"
        }
        try:
            res = requests.get(self.promo_url, proxies=proxies, headers=headers, timeout=10, verify=False)
            return res.status_code == 200
        except:
            return False

    def run_full_promotion(self, promo_url, step_size=12):
        self.promo_url = promo_url

        if not self._auth_request("apply"):
            logging.warning("任务接取失败")
            return

        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        proxy_list = get_total_proxies()
        if not proxy_list:
            logging.error("无法获取代理池，退出推广任务。")
            return

        logging.info(f"🚀 开始刷流，代理总数: {len(proxy_list)}")

        hits = 0
        current_step_hits = 0

        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = {executor.submit(self._proxy_click, p): p for p in proxy_list}

            for future in as_completed(futures):
                try:
                    if future.result():
                        hits += 1
                        current_step_hits += 1
                        logging.info(f"✅ 成功命中累计: {hits} (当前阶段: {current_step_hits}/{step_size})")

                    if current_step_hits >= step_size:
                        logging.info(f"达到阶段目标 {step_size} 次，进入同步等待期...")
                        time.sleep(15)

                        if self._auth_request("draw"):
                            logging.info("🎯 领奖成功！任务闭环完成。")
                            for f in futures:
                                f.cancel()
                            return
                        else:
                            logging.warning("❌ 领奖失败（可能点击未达标），继续刷流...")
                            current_step_hits = 0

                except Exception as e:
                    logging.debug(f"线程执行异常: {e}")

        logging.error("⚠️ 代理池已耗尽，未能完成领奖。")

