import os
import logging
from datetime import datetime
from base import KLPBBSBot
from tasks import KLPBBSTasks

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] [%(asctime)s] %(message)s")


def main():
    username = os.environ.get("USERNAME")
    password = os.environ.get("PASSWORD")
    promo_url = os.environ.get("PROMO_URL")
    target_tid = os.environ.get("TARGET_TID")
    header = {
        "origin": "https://klpbbs.com",
        "Referer": "https://klpbbs.com/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36 Edg/116.0.1938.81"
    }

    bot = KLPBBSBot(header)
    if bot.login(username, password):
        tasks = KLPBBSTasks(bot)
        if datetime.now().hour == 16:
            tasks.daily_sign_in()

        tasks.run_full_promotion(promo_url)

        if datetime.now().hour == 0:
            f_hash = bot.get_formhash()
            tasks.reply_thread(target_tid, f_hash)
        if datetime.now().hour == 6 or datetime.now().hour == 12:
            f_hash = bot.get_formhash()
            tasks.bump_thread(target_tid, f_hash)


if __name__ == "__main__":
    main()