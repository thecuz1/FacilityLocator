import discord
import os
import logging
from discord.ext import commands

handler = logging.FileHandler(
    filename='discord.log', encoding='utf-8', mode='w')

extensions = ['extensions.modify', 'extensions.query',
              'extensions.misc', 'extensions.sqlite']


class Bot(commands.Bot):
    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})')
        print(f'Discordpy version {discord.__version__}')
        print('---------')

    async def setup_hook(self):
        for extension in extensions:
            await self.load_extension(extension)


intents = discord.Intents.default()
intents.message_content = True

bot = Bot('>', intents=intents)
bot.run(os.environ.get('FACILITYLOCATOR_API_TOKEN'), log_handler=handler)
