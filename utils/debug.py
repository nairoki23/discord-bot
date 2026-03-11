import aiohttp
from discord import Webhook
from dotenv import dotenv_values
config = dotenv_values(".env")

URL=config["DEBUG_WEBHOOK"]
async def send(**kwargs):
    """
    引数をすべて webhook.send() にそのまま流し込む1回きり送信関数
    """
    async with aiohttp.ClientSession() as session:
        webhook = Webhook.from_url(URL, session=session)
        await webhook.send(**kwargs)

async def print(text):
    async with aiohttp.ClientSession() as session:
        webhook = Webhook.from_url(URL, session=session)
        await webhook.send(content=text)