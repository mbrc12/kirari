import time

from discord.ext import commands

from kirari.constants import kirari_prefix, coin_symbol
import kirari.db as db

def get_time():
    sec = time.time()
    return int(sec)


def is_game_on():
    return db.common_read("game_on")


def is_betting_on():
    return db.common_read("betting_on")


def process_mention(txt):
    txt = str(txt)
    # Remove all stuff till first digit
    pos = [c for c in txt if c.isdigit()]
    return int("".join(pos))

def coinfmt(amt):
    return "{0}{2}{1}".format('-' if amt < 0 else '', coin_symbol, 
            -amt if amt < 0 else amt)

async def bot_error_handler(ctx, exception):
    if isinstance(exception, commands.MissingRequiredArgument):
        await ctx.send("You're missing some argument. Check `k;help`")
    else:
        raise exception
