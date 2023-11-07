import asyncio
import logging

from aiogram.fsm.storage.memory import MemoryStorage

from aiogram import Bot, Dispatcher, F, types
from aiogram.fsm.storage.redis import RedisStorage

import config
import handlers.new_user as new_user
import handlers.generate_look as generate_look
import handlers.user_in_menu as user_in_menu
import handlers.save_look as save_look

storage=RedisStorage.from_url(config.redis_url)
#r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
bt = Bot(token=config.token)
d = Dispatcher(storage=storage)


async def main():
    logging.basicConfig(level=logging.INFO)
    
    #bot = Bot(token=config.token)
    bot = bt
    dp = d
    #dp = Dispatcher(storage=RedisStorage(r))

    dp.include_router(new_user.router)
    dp.include_router(generate_look.router)
    dp.include_router(user_in_menu.router)
    dp.include_router(save_look.router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
 