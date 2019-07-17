import logging
import sys

import discord
from discord.ext import commands

import kirari.db as db
from kirari.common import *
import kirari.codeforces as cf
from kirari.constants import *

logger = logging.getLogger(__name__)


@commands.command(brief="Introduce myself")
async def intro(ctx):
    await ctx.send("It doesn't matter, if it isn't about gambling.")


@commands.command()
async def echo(ctx):
    await ctx.send(process(ctx.message.content))


@commands.command(brief="Show the list of all admins")
async def admins(ctx):
    """
    Show the list of all admins
    """

    admin_list = db.common_read("admin_list")

    if admin_list == []:
        await ctx.send("No one is an admin.")
        return

    response = "The following members are admins:```\n"

    for admin_id in admin_list:
        admin_member_name = db.db_read(admin_id, "name")
        response += "%s\n" % admin_member_name

    response += "```\n"
    await ctx.send(response)


async def get_id(ctx, what):
    converter = commands.MemberConverter()
    member = await converter.convert(ctx, what)
    return member.id


@commands.command(brief='Get userID of someone')
async def id(ctx, user):
    uid = await get_id(ctx, user)
    await ctx.send("Converted: `%s`" % uid)


@commands.command()
async def my_id(ctx):
    await ctx.send(
        f"Your ({ctx.author.name}'s) discord ID is : `{ctx.author.id}`")


def is_admin(uid):
    admin_list = db.common_read("admin_list")
    return uid in admin_list


def is_user(uid):
    user_list = db.common_read("user_list")
    return uid in user_list


@commands.command(brief="Check whether you are an admin")
async def am_i_admin(ctx):
    """
    Checks whether you are an admin.
    """

    uid = ctx.author.id
    await ctx.send("You are%s an admin." % ("" if is_admin(uid) else " not"))


async def error(ctx, msg):
    await ctx.send("**ERROR:** %s" % msg)


async def refuse(ctx):
    await error(ctx,
                "You do not have the necessary permissions for this action.")


async def admin_check(ctx):
    if not is_admin(ctx.author.id):
        await refuse(ctx)
        return False
    else:
        return True


@commands.command(brief="Register a new user")
async def register(ctx, user, cf_id):
    """
    register <@mention the user> <cf-username> registers a new user 
    to Kirari under Codeforces username <cf-username>. The commanding
    user must be admin.
    """

    if not await admin_check(ctx):
        return
    
    if is_game_on():
        await error(ctx, "A game is running. Please try later.")
        return

    uid = process_mention(user)
    try:
        uid = int(uid)
    except Exception:
        await error(ctx, "Invalid user.")
        return

    if is_user(uid):
        await error(
            ctx,
            "%s already exists in the database. If you want to update CF username, please use `k%cf_update`."
            % db.db_read(uid, "name"))
        return

    if not cf.user_exists(cf_id):
        await error(ctx, "%s is not a valid Codeforces username" % cf_id)
        return

    converter = commands.MemberConverter()
    member = await converter.convert(ctx, str(uid))

    member_name = member.name

    cf_coins = cf.user_coins(cf_id)

    db.db_write(uid, "name", member_name)
    db.db_write(uid, "cf_id", cf_id)
    db.db_write(uid, "cf_score", cf_coins)
    db.db_write(uid, "kirari_score", 0)

    user_list = db.common_read("user_list")
    user_list.append(uid)
    db.common_write("user_list", user_list)

    response = "New user %s registered:\n ```ID: %s\nCodeforces: %s\nCash: %s\n```"
    await ctx.send(response %
                   (member_name, str(uid), cf_id, coinfmt(int(cf_coins))))


@commands.command(brief="Show how much cash you have.")
async def cash(ctx):
    """
    Show how much cash you have.
    """

    uid = ctx.author.id

    if not is_user(uid):
        await error(ctx, "You are not a registered user.")
        return

    cf_coins = int(db.db_read(uid, "cf_score"))
    kirari_coins = int(db.db_read(uid, "kirari_score"))

    response = "Cash for user : **%s**```Coins from CF: %s\nCoins from Kirari: %s\nTotal: %s\n```"
    await ctx.send(response %
                   (ctx.author.name, coinfmt(cf_coins), coinfmt(kirari_coins), 
                       coinfmt(cf_coins + kirari_coins)))


@commands.command(brief="Register a new admin.")
async def register_admin(ctx, user):
    """
    register_admin <@mention the user> registers that user
    to be an admin. Commanding user must be admin.
    """

    if not await admin_check(ctx):
        return
    
    if is_game_on():
        await error(ctx, "A game is running. Please try later.")
        return


    uid = process_mention(user)

    if not is_user(uid):
        await error(ctx, "Proposed user %d is not a registered user." % uid)
        return

    if is_admin(uid):
        await error(ctx, "Proposed user %d is already an admin." % uid)

    admin_list = db.common_read("admin_list")

    admin_list.append(uid)

    db.common_write("admin_list", admin_list)

    member_name = db.db_read(uid, "name")

    await ctx.send("Proposed user %s (%d) is now an admin." % (member_name, uid)
                   )


@commands.command(brief="Update the Codeforces username for a user")
async def cf_update(ctx, user, cf_id):
    """
    cf_update <@mention the user> <cf-username> changes the Codeforces
    username of this user to <cf-username>. Commanding user must be admin.
    """

    if not await admin_check(ctx):
        return
    
    if is_game_on():
        await error(ctx, "A game is running. Please try later.")
        return

    uid = process_mention(user)

    if not is_user(uid):
        await error(ctx, "The user %d is not a registered user." % uid)
        return

    if not cf.user_exists(cf_id):
        await error(ctx, "%s is not a valid Codeforces username" % cf_id)
        return

    cf_coins = cf.user_coins(cf_id)

    db.db_write(uid, "cf_id", cf_id)
    db.db_write(uid, "cf_score", cf_coins)

    member_name = db.db_read(uid, "name")

    response = "Codeforces ID changed for %s to %s. This changes their Codeforces coins to %s."

    await ctx.send(response %
                   (member_name, cf_id, coinfmt(cf_coins)))


@commands.command(brief="Refresh the Codeforces scores/coins for each user")
async def cf_refresh(ctx):
    """
    Refresh the Codeforces scores/coins of all users. Commanding user
    must be admin.
    """

    if not await admin_check(ctx):
        return
    
    if is_game_on():
        await error(ctx, "A game is running. Please try later.")
        return

    uids = db.common_read("user_list")

    response = "Refreshed Codeforces Coins: ```"

    for uid in uids:
        logger.error(uid)
        cf_id = db.db_read(uid, "cf_id")
        cf_coins = cf.user_coins(cf_id)
        member_name = db.db_read(uid, "name")
        db.db_write(uid, "cf_score", cf_coins)

        current_str = "%s (CF: %s) : %s\n" % (member_name, cf_id, coinfmt(cf_coins))

        response += current_str

    response += "```\n"

    await ctx.send(response)

@commands.command(brief = "Transfer money to someone.")
async def loan(ctx, to, amt):

    """
    k;loan <to> <amt> will ask Kirari to send <to> an amount of <amt> from your cash.
    <amt> must be positive, and you should have that amount.
    """
    
    if is_game_on():
        await error(ctx, "A game is running. Please try later.")
        return

    try:
        amt = int(amt)
    except Exception:
        await error(ctx, "Amount must be integer.")
        return

    if amt < 0:
        await error(ctx, "Amount cannot be negative.")
        return

    sender_id = ctx.author.id

    if not is_user(sender_id):
        await error(ctx, "You're not a registered user.")
        return

    total = db.db_read(sender_id, "kirari_score") + db.db_read(sender_id, "cf_score")

    if amt > total:
        await error(ctx, "Cannot give more than what you have")
        return

    try:
        to_id = await get_id(ctx, to)
    
        if not is_user(to_id):
            await error(ctx, "Recipient is not registered.")
            return

        current_to_score = db.db_read(to_id, "kirari_score")
        db.db_write(to_id, "kirari_score", current_to_score + amt)

        current_sender_score = db.db_read(sender_id, "kirari_score")
        db.db_write(sender_id, "kirari_score", current_sender_score - amt)
    
        to_name = db.db_read(to_id, "name")
        sender_name = db.db_read(sender_id, "name")

        await ctx.send("%s successfully transferred %s to %s." % (
            sender_name,
            coinfmt(amt),
            to_name))

        return

    except Exception:
        await error(ctx, "Some error occurred.")
        return

@commands.command(brief = "Load database from a url")
async def load_db(ctx, url):
    """
    load_db <url> : Loads database from url and replaces current database
    """
    
    if not await admin_check(ctx):
        return
    
    print(url)

    flag = db.get_json(url)
    if not flag:
        await error(ctx, "URL not found or data malformed.")
        return
    
    await ctx.send("Database successfully loaded from %s." % url)

@commands.command(brief = "Dump database")
async def dump_db(ctx):
    """
    dump_db <url> : Dumps database to a file in Discord chat.
    """

    if not await admin_check(ctx):
        return

    db.put_json()

    await ctx.send(file = 
            discord.File(
                fp = open(json_path, 'rb'),
                filename = "Kirari_database.json"
                ))
                    

exports = [
    id, intro, echo, admins, my_id, am_i_admin, register, cash, register_admin,
    cf_update, cf_refresh, loan, load_db, dump_db
]
