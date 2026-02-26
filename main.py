import os
import logging
from datetime import datetime
from base import KLPBBSBot
from tasks import KLPBBSTasks

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] [%(asctime)s] %(message)s")


def should_use_reply_instead_of_bump(record_file="last_reply_date.txt"):
    today = datetime.day

    if not os.path.exists(record_file):
        return True

    with open(record_file, "r") as f:
        last_date = f.read().strip()

    return last_date != today


def update_reply_record(record_file="last_reply_date.txt"):
    today = datetime.day
    with open(record_file, "w") as f:
        f.write(today)

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


        if True:
            f_hash = bot.get_formhash()
            if should_use_reply_instead_of_bump():
                logging.info(1)
                #tasks.reply_thread(target_tid, f_hash)
                update_reply_record()
            else:
                logging.info(2)
                #tasks.bump_thread(target_tid, f_hash)


if __name__ == "__main__":
    main()