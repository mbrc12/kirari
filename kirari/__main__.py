import os
import sys
import logging

import discord
from discord.ext import commands

from kirari.custom_formatter import CustomFormatter
import kirari.roulette as roulette
import kirari.admin as admin
from kirari.common import bot_error_handler
from kirari.constants import *

logger = logging.getLogger(__name__)


def main():

    discord_key = ""

    # Set the environment variable below to the discord key
    try:
        discord_key = os.environ[kirari_key_env]
    except KeyError:
        logger.error("KIRARI_KEY environment variable is not set. Exiting..")
        sys.exit()

    bot = commands.Bot(command_prefix=kirari_prefix)

    for exported_command in admin.exports:
        bot.add_command(exported_command)

    for exported_command in roulette.exports:
        bot.add_command(exported_command)

    @bot.check
    async def no_DM(ctx):
        return ctx.guild is not None

    bot.add_listener(bot_error_handler, name='on_command_error')

    bot.run(discord_key)


if __name__ == "__main__":
    main()
