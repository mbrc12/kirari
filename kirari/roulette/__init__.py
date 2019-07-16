import logging
import sys
import asyncio
import time
from secrets import randbelow

import discord
from discord.ext import commands

import kirari.db as db
from kirari.common import *
from kirari.constants import *
from kirari.admin import is_user, is_admin, error

logger = logging.getLogger(__name__)

def get_time():
    sec = time.time()
    return int(sec)

def is_game_on():
    return db.common_read("game_on")

# At same bet_value, the expected winnings should be zero
# at same bet_size
def get_delta(win, bet_size, bet_value):
    probability = bet_size / roulette_size
    delta = 0

    if win:
        delta = int(round((1 - probability) * bet_value))
    else:
        delta = int(round(-probability * bet_value))
    
    return delta


async def parse_bet(ctx, bet_str):
    bets = bet_str.split(',')
    bet = set([])
    try: 
        for phrase in bets:
            if phrase.find('~') >= 0:
                a, b = phrase.split('~')
                if a == "":
                    a = "1"
                if b == "":
                    b = str(roulette_size)
                a = int(a)
                b = int(b)
                for val in range(1, roulette_size + 1):
                    if a <= val and val <= b:
                        bet.add(val)

            elif phrase.find('m') >= 0:
                m, r = phrase.split('m')
                m = int(m)
                if r == "": 
                    r = "0"
                r = int(r)
                for val in range(1, roulette_size + 1):
                    if val % m == r:
                        bet.add(val)
            else:
                value = 0
                value = int(phrase)
                if 1 <= value and value <= roulette_size:
                    bet.add(value)

    except Exception:
        await error(ctx, "Wrong bet format. Please check `k;help bet`.")
        return set([]), -1  # Empty bet

    return bet, 0


@commands.command(brief = "Make a bet")
async def bet(ctx, bet_str, bet_value):

    """bet <bet-string> <bet-amount> makes a bet on the positions in
       in bet-string, at an amount of bet-amount. <bet-string> format
       is as follows:
        
       bet must in the format <bet-phrase>,<bet-phrase>,... (a comma-separated
       list of bet-phrases). Each bet-phrase is of three possible types:

       * A single number, say 6
       * A range, like 2~20, or ~20 (which means 1~20)
       * An arithmetic progression, like 3m1 (which means all numbers
        of the form 3k + 1), or 2m (which means all even numbers).

       Finally, all bet values that do not lie in the roulette range (1..36)
       are excluded from the bet make.
        
       Example:
       ~5,6m1,35 bets on the following values:
       1, 2, 3, 4, 5, 35 and all numbers of the form 6k + 1, like 7, 13 etc.
    """

    uid = ctx.author.id

    if not is_user(uid):
        await error(ctx, "You are not registered and cannot bet.")
        return

    if not is_game_on():
        await error(ctx, "No game is currently under progress.")
        return

    try:
        bet_value = int(bet_value)
    except Exception:
        await error(ctx, "The value of your bet must be integer")
        return
    
    current_cash = db.db_read(uid, "cf_score") + db.db_read(uid, "kirari_score")
    
    if bet_value > current_cash:
        await error(ctx, "You cannot bet more than what you have!")
        return

    bet, flag = await parse_bet(ctx, bet_str)
    
    if flag < 0:
        return

    db.db_write(uid, "bet", bet)
    db.db_write(uid, "bet_value", bet_value)

    member_name = db.db_read(uid, "name")
    
    iabs = lambda x : x if x >= 0 else -x
    
    positive_potential = iabs(get_delta(True, len(bet), bet_value))
    negative_potential = iabs(get_delta(False, len(bet), bet_value))

    response = """
    Bet by **%s**:\nYou have bet on the following %d position(s): ```%s```The value of your current bet is **%d%s** (+%d, -%d).
    """ % ( member_name,
            len(bet),
            "<you have bet on nothing>" if len(bet) == 0 else " ".join(map(str, sorted(list(bet)))), 
            bet_value,
            coin_symbol,
            positive_potential,
            negative_potential)

    await ctx.send(response)
     

@commands.command(brief = "Begin a new game")
async def begin(ctx):
    """Begins a new game of roulette"""

    uid = ctx.author.id

    if not is_user(uid):
        await error(ctx, "You are not a registered user.")
        return

    if is_game_on():
        await error(ctx, "A game is already in progress.")
        return

    last_game_time = db.common_read("game_begin_time")
    current_time = get_time()

    if (current_time - last_game_time < gap_between_games_in_minutes * 60):
        await error(ctx, "Please wait some time before starting another game.")
        return

    db.common_write("game_on", True)
    db.common_write("game_begin_time", current_time)

    uids = db.common_read("user_list")

    for uid in uids:
        db.db_write(uid, "bet", set([]))
        db.db_write(uid, "bet_value", 0)

    response = "Game started. Everyone's bet is currently 0. You have %d seconds to bet." % roulette_duration

    db.common_write("betting_on", True)
    await ctx.send(response)

    for steps in range(roulette_duration // step_size):
        await asyncio.sleep(step_size)
        await ctx.send("%d seconds left to bet." % (roulette_duration - (steps + 1) * step_size))
    
    db.common_write("betting_on", False)
    await ctx.send("Time up. No more bets accepted.")
    
    candidates = [randbelow(roulette_size) + 1 for i in range(candidate_size)]
    
    await ctx.send("Candidates to win:\n`%s`" % (" ".join(map(str, sorted(candidates)))))
    
    await asyncio.sleep(candidate_break)

    winner_idx = randbelow(candidate_size)
    # Generate result of roulette spin
    result = candidates[winner_idx]
    
    await ctx.send("The winning number is: **%d**" % result)

    current_server_value = db.db_read(server_uid, "score")
    server_delta = 0

    summary = """```"""

    for uid in uids:
        bet = db.db_read(uid, "bet")
        bet_value = db.db_read(uid, "bet_value")

        delta = get_delta(result in bet, len(bet), bet_value)

        kirari_coins = db.db_read(uid, "kirari_score")
        server_delta -= delta
        kirari_coins += delta;

        member_name = db.db_read(uid, "name")

        summary += "%s: \t [%s%d%s]\n" % (
                member_name, 
                '+' if delta >= 0 else '-',
                delta if delta >= 0 else -delta,
                coin_symbol
                )

        db.db_write(uid, "kirari_score", kirari_coins)
    
    summary += """```\nKirari's delta: `%s%d%s`\n""" % (
            '+' if server_delta >= 0 else '-',
            delta if delta >= 0 else -delta,
            coin_symbol
            )
    db.common_write("game_on", False)
    db.db_write(server_uid, "score", current_server_value + server_delta)

    await ctx.send("**Final Scores for this round:**" + summary)


@commands.command(brief = "Shows the ranklist")
async def ranklist(ctx):

    """
    Shows the ranklist of all users, and the profit made 
    by Kirari till now.
    """

    user_list = db.common_read("user_list")

    users = []

    for uid in user_list:
        cf_coins = db.db_read(uid, "cf_score")
        kirari_coins = db.db_read(uid, "kirari_score")
        member_name = db.db_read(uid, "name")

        total_score = cf_coins + kirari_coins
    
        users.append((total_score, member_name))

    response = """
    The ranklist is:```"""

    server_value = db.db_read(server_uid, "score")

    for (score, member_name) in users:
        response += "%s: \t [%d%s]\n" % (member_name, score, coin_symbol)

    response += """``` Kirari has: `%d%s`""" % (server_value, coin_symbol)

    await ctx.send(response)

exports = [
        begin,
        bet,
        ranklist
        ]
