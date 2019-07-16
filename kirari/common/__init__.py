from discord.ext import commands

from kirari.constants import kirari_prefix

def process(txt):
    idx = txt.find(' ')
    if (idx < 0):
        return ""
    return txt[idx + 1:]

def process_mention(txt):
    txt = str(txt)
    # Remove all stuff till first digit
    pos = [c for c in txt if c.isdigit()]
    return int("".join(pos))


async def bot_error_handler(ctx, exception):
    if isinstance(exception, commands.MissingRequiredArgument):
        await ctx.send("You're missing some argument. Check `k;help`")
    else:
        raise exception
