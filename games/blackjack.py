from .game_config import *
import asyncio
import time
import discord
import random
from functions.db_game import DB
from discord.ui import Button, View, button
from discord import ButtonStyle

game_records = {}
turn_count = 30
hit_count = 20

class BJ_View(View):
    @button(label="要牌", style=ButtonStyle.green, emoji="✋")
    async def hit_callback(self, button: discord.Button, interaction: discord.Interaction):
        channel_id = str(interaction.channel.id)

        if game_records.get(channel_id):
            turn = game_records[channel_id]["turn"]
            if game_records[channel_id]["step"] != 2 or game_records[channel_id]["players"][turn]["user_id"] != interaction.user.id:
                await interaction.response.send_message(f"不是你的回合", delete_after=1)
                # delete_from_processing(message)
                return
            else:
                cards, points = show_cards(game_records[channel_id]["players"][turn]["cards"])
                if (len(game_records[channel_id]['players'][turn]["cards"]) < 5 or points < 21) and not game_records[channel_id]['players'][turn]["stand"]:
                    game_records[channel_id]['players'][turn]["cards"].append(hit_a_card(game_records[channel_id]['cards']))
                    game_records[channel_id]['hit'] = True
                else:
                    await interaction.response.send_message("不允許的指令", delete_after=1)
        else:
            await interaction.response.send_message(f"請先使用指令 `bj!start` 或 `/bj_start` 開始一場21點遊戲", delete_after=1)

    @button(label="加倍", style=ButtonStyle.primary, emoji="🪙")
    async def double_callback(self, button: discord.Button, interaction: discord.Interaction):
        channel_id = str(interaction.channel.id)

        if game_records.get(channel_id):
            turn = game_records[channel_id]["turn"]
            if game_records[channel_id]["step"] != 2 or game_records[channel_id]["players"][turn]["user_id"] != interaction.user.id:
                await interaction.response.send_message(f"不是你的回合", delete_after=1)
                # delete_from_processing(message)
                return
            else:
                cards, points = show_cards(game_records[channel_id]["players"][turn]["cards"])
                if len(game_records[channel_id]['players'][turn]["cards"]) == 2 and points < 21 and not game_records[channel_id]['players'][turn]["stand"]:
                    game_records[channel_id]['start_time'] = int(time.time())
                    game_records[channel_id]['players'][turn]["stand"] = True
                    db = DB()
                    success, balance = db.bet(interaction.user.id, game_records[channel_id]['players'][turn]["bet_amount"])
                    if success:
                        await interaction.response.send_message(f"你加倍了, 你剩下 {balance} :coin:")
                        game_records[channel_id]['players'][turn]["bet_amount"] *= 2
                    else:
                        await interaction.response.send_message(f"你的籌碼不夠，你剩下 {balance} :coin:")
                        db.close()
                        # delete_from_processing(message)
                        return
                    db.close()

                    game_records[channel_id]['players'][turn]["cards"].append(hit_a_card(game_records[channel_id]['cards']))
                    game_records[channel_id]['hit'] = True
                else:
                    await interaction.response.send_message("不允許的指令", delete_after=1)
        else:
            await interaction.response.send_message(f"請先使用指令 `bj!start` 或 `/bj_start` 開始一場21點遊戲", delete_after=1)

    @button(label="Stand", style=ButtonStyle.red, emoji="🛑")
    async def stand_callback(self, button: discord.Button, interaction: discord.Interaction):
        channel_id = str(interaction.channel.id)

        if game_records.get(channel_id):
            turn = game_records[channel_id]["turn"]
            if game_records[channel_id]["step"] != 2 or game_records[channel_id]["players"][turn]["user_id"] != interaction.user.id:
                await interaction.response.send_message(f"不是你的回合", delete_after=1)
                # delete_from_processing(message)
                return
            else:
                cards, points = show_cards(game_records[channel_id]["players"][turn]["cards"])
                if (len(game_records[channel_id]['players'][turn]["cards"]) < 5 or points < 21):
                    game_records[channel_id]['hit'] = True
                    game_records[channel_id]['start_time'] = int(time.time()) - hit_count + 5
                    game_records[channel_id]['players'][turn]["stand"] = True
                else:
                    await interaction.response.send_message("不允許的指令", delete_after=1)
        else:
            await interaction.response.send_message(f"請先使用指令 `bj!start` 或 `/bj_start` 開始一場21點遊戲", delete_after=1)

async def game_task(channel, m):
    # db = DB()
    channel_id = str(channel.id)
    if channel_id in game_records:
        await channel.send("遊戲開始了！請等待下一場遊戲")
        return
    game_records[channel_id] = {"players": [], "turn": -1, "hit":False, "dealer": {"cards": []}, "message": m, "start_time": int(time.time()), "step": 0, "record": {}, "cards": [i for i in range(52)]}

    while True:
        if game_records[channel_id]["step"] == 0:
            await step(game_records[channel_id])
        elif game_records[channel_id]["step"] == 1:
            game_records[channel_id]["dealer"]["cards"].append(hit_a_card(game_records[channel_id]["cards"]))
            await step1(game_records[channel_id])
        elif game_records[channel_id]["step"] == 2:
            await step2(game_records[channel_id])
        elif game_records[channel_id]["step"] == 3:
            await step3(game_records[channel_id])
        elif game_records[channel_id]["step"] == 4:
            await step4(game_records[channel_id])


        if game_records[channel_id]["step"] == 5:
            game_records.pop(channel_id)
            break
        # db.save_game(channel_id, game_records[channel_id])
        # print(game_records[channel_id]["step"])
        await asyncio.sleep(async_delay)

async def step(record):
    time_left = turn_count - (int(time.time()) - record['start_time'])
    time_left = 0 if time_left < 0 else time_left
    embed = discord.Embed()
    embed.type = "rich"
    embed.set_author(name="遊戲開始！ 使用 `bj!join` 或 `/bj_join` 加入遊戲 ")
    embed.set_footer(text=f"遊戲將在 {time_left} 秒後開始")
    embed.colour = discord.Colour.orange() 

    dealer_cards, dealer_points = show_cards(record["dealer"]["cards"])

    embed.add_field(name="莊家", value=f"手牌: {dealer_cards}", inline=False)

    for item in record["players"]:
        embed.add_field(name=item["user_name"], value=f"籌碼: {item['bet_amount']} :coin:\n手牌: ", inline=False)

    if time_left <= 0:
        record["step"] += 1

    # record["embed"] = embed
    # await record["message"].edit(embed=embed, view=BJ_View())
    await record["message"].edit(embed=embed)

async def step1(record):
    embed = discord.Embed()
    embed.type = "rich"
    embed.colour = discord.Colour.orange() 
    n_players = len(record["players"])

    dealer_cards, dealer_points = show_cards(record["dealer"]["cards"])
    record['start_time'] = int(time.time()-50)
    content = f"莊家拿到 {dealer_cards}"
    embed.set_author(name="現在是莊家的回合")
    embed.set_footer(text=f"21點遊戲進行中")
    embed.add_field(name=":point_right: 莊家", value=f"手牌: {dealer_cards}", inline=False)

    if n_players == 0:
        record["step"] = 5
        return
        
    for i, item in enumerate(record["players"]):
        embed.add_field(name=item["user_name"], value=f"chips: {item['bet_amount']} :coin:\ncards: ", inline=False)

    await record["message"].delete()
    # await record["message"].edit(embed=embed, content=content)
    record["message"] = await record["message"].channel.send(embed=embed, content=content, view=BJ_View())

    embed.set_field_at(0, name="莊家", value=f"手牌: {dealer_cards}", inline=False)
    for _ in range(2):
        for i in range(n_players):
            await asyncio.sleep(1)
            record["players"][i]["cards"].append(hit_a_card(record["cards"]))
            
            # delete the point finger
            if i == 0:
                ix = n_players - 1
                cards, points = show_cards(record["players"][ix]["cards"])
                embed.set_field_at(ix+1, name=f"{record['players'][ix]['user_name']}", value=f"籌碼: {record['players'][ix]['bet_amount']} :coin:\n手牌: {cards}", inline=False)
            else:
                ix = i - 1
                cards, points = show_cards(record["players"][ix]["cards"])
                embed.set_field_at(ix+1, name=f"{record['players'][ix]['user_name']}", value=f"籌碼: {record['players'][ix]['bet_amount']} :coin:\n手牌: {cards}", inline=False)
            
            cards, points = show_cards(record["players"][i]["cards"])
            embed.set_field_at(i+1, name=f":point_right: {record['players'][i]['user_name']}", value=f"籌碼: {record['players'][i]['bet_amount']} :coin:\n手牌: {cards}", inline=False)
            embed.set_author(name=f"It's {record['players'][i]['user_name']} 的回合")
            content = f"<@!{record['players'][i]['user_id']}> 拿到 {cards}"
            await record["message"].edit(embed=embed, content=content)

    await asyncio.sleep(1)
    embed.set_field_at(n_players, name=f"{record['players'][n_players - 1]['user_name']}", value=f"籌碼: {record['players'][n_players - 1]['bet_amount']} :coin:\n手牌: {cards}", inline=False)
    await record["message"].edit(embed=embed, content=None)
    record["message"].embeds[0] = embed

    record["step"] += 1

async def step2(record):
    embed = discord.Embed()
    embed.type = "rich"
    embed.colour = discord.Colour.orange() 

    for i, p in enumerate(record["players"]):
        record['turn'] = i
        cards, points = show_cards(p["cards"])

        record["message"].embeds[0].set_field_at(i+1, name=f":point_right: {record['players'][i]['user_name']}", value=f"籌碼: {record['players'][i]['bet_amount']} :coin:\n手牌: {cards}", inline=False)
        await record["message"].edit(embed=record["message"].embeds[0], content=f"{p['user_name']} 的回合")
        msg = f"<@!{p['user_id']}> 的回合 停牌 / 要牌 / 加倍\n你的籌碼: {record['players'][i]['bet_amount']} :coin:. 你的手牌: {cards}\n剩餘 {hit_count} 秒"
        # m = await record["message"].channel.send(f"<@!{p['user_id']}>'s turn. bj!stand / bj!hit / bj!double\nYour chips: {record['players'][i]['bet_amount']} :coin:. Your card(s): {cards}\nYou left {hit_count} second(s).")
        # record["message2"] = m

        record['start_time'] = int(time.time())
        mem = 0
        while True:
            if record["players"][i]["stand"]:
                time_left = 5 - (int(time.time()) - record['start_time'])
            else:
                time_left = hit_count - (int(time.time()) - record['start_time'])
            time_left2 = time_left
            time_left = 0 if time_left < 0 else time_left

            if mem != time_left:
                mem = time_left if time_left > 0 else 0
                cards, points = show_cards(p["cards"])
                if record["hit"]:
                    record['start_time'] = int(time.time())
                    record["hit"] = False
                    # await record["message2"].delete()
                    # record["message2"] = None
                    time_left = hit_count

                if points > 21:
                    msg = f"<@!{record['players'][i]['user_id']}> 的回合結束\n你的籌碼: {record['players'][i]['bet_amount']} :coin: 你的手牌: {cards}\n你爆牌了 :bomb::bomb::bomb:.\n{time_left} 秒後輪到下一位玩家"
                    record["players"][i]["result"] = "busted"
                    record["players"][i]["stand"] = True
                elif len(record["players"][i]["cards"]) == 2 and points == 21:
                    msg = f"<@!{record['players'][i]['user_id']}> 的回合結束\n你的籌碼: {record['players'][i]['bet_amount']} :coin:. 你的手牌: {cards}\n你拿到黑傑克 :money_with_wings::money_with_wings::money_with_wings:\n{time_left} 秒後輪到下一位玩家"
                    record["players"][i]["result"] = "bj"
                    record["players"][i]["stand"] = True
                elif len(record["players"][i]["cards"]) == 5:
                    msg = f"<@!{record['players'][i]['user_id']}> 的回合結束\n你的籌碼: {record['players'][i]['bet_amount']} :coin:. 你的手牌: {cards}\n你過五關了 :flower_playing_cards::flower_playing_cards::flower_playing_cards:\n{time_left} 秒後輪到下一位玩家"
                    record["players"][i]["result"] = "five"
                    record["players"][i]["stand"] = True
                elif points == 21:
                    record["players"][i]["result"] = "21"
                    msg = f"<@!{record['players'][i]['user_id']}> 的回合結束\n你的籌碼: {record['players'][i]['bet_amount']} :coin:. 你的手牌: {cards}\n你拿到21點\n{time_left} 秒後輪到下一位玩家"
                    record["players"][i]["stand"] = True
                else:
                    if len(p["cards"]) == 2:
                        msg = f"<@!{record['players'][i]['user_id']}> 的回合\n你的籌碼: {record['players'][i]['bet_amount']} :coin:. 你的手牌: {cards}\n你剩下 {time_left} 秒"
                    else:
                        msg = f"<@!{record['players'][i]['user_id']}> 的回合\n你的籌碼: {record['players'][i]['bet_amount']} :coin:. 你的手牌: {cards}\n你剩下 {time_left} 秒"

                await record["message"].edit(content=msg)
                
                # if record["message2"]:
                #     await record["message2"].edit(content=msg)
                # else:
                #     record['start_time'] = int(time.time())
                #     record["message2"] = await record["message"].channel.send(msg)
                    
                
                record["message"].embeds[0].set_field_at(i+1, name=f":point_right: {record['players'][i]['user_name']}", value=f"籌碼: {record['players'][i]['bet_amount']} :coin:\n手牌: {cards}", inline=False)
                # await record["message"].edit(embed=record["message"].embeds[0], content=f"{record['players'][i]['user_name']}'s turn.")
                await record["message"].edit(embed=record["message"].embeds[0])

            await asyncio.sleep(0.8)
            if time_left2 < 1.6:
                record["message"].embeds[0].set_field_at(i+1, name=f"{record['players'][i]['user_name']}", value=f"籌碼: {record['players'][i]['bet_amount']} :coin:\n手牌: {cards}", inline=False)
                # await record["message"].edit(embed=record["message"].embeds[0], content=f"{record['players'][i]['user_name']}'s turn.")
                await record["message"].edit(embed=record["message"].embeds[0])
                break
    record["step"] += 1

async def step3(record):
    cards, points = show_cards(record["dealer"]["cards"])
    embed = record["message"].embeds[0]
    channel = record["message"].channel
    embed.set_field_at(0, name=f":point_right: 莊家", value=f"手牌: {cards}", inline=False)
    embed.set_author(name=f"現在是莊家的回合")
    await record["message"].edit(embed=embed, content="莊家的回合")
    # record["message2"] = None

    while points < 17 and len(record["dealer"]["cards"]) < 5:
        await asyncio.sleep(1.5)
        record["dealer"]["cards"].append(hit_a_card(record["cards"]))
        cards, points = show_cards(record["dealer"]["cards"])
        embed.set_field_at(0, name=f":point_right: 莊家", value=f"手牌: {cards}", inline=False)
        await record["message"].edit(embed=embed, content="莊家的回合")

        # if record["message2"]:
        #     await record["message2"].edit(content=f"Dealer's turn. Dealer's cards: {cards}")
        # else:
        #     record["message2"] = await channel.send(f"Dealer's turn. Dealer's cards: {cards}")

    embed.set_field_at(0, name=f"莊家", value=f"手牌: {cards}", inline=False)
    await record["message"].edit(embed=embed, content="莊家的回合")

    record["step"] += 1

async def step4(record):
    await asyncio.sleep(1)
    embed = record["message"].embeds[0]
    embed.set_author(name=f"遊戲結果")
    embed.colour = discord.Colour.green()
    embed.set_footer(text="遊戲已結束")

    cards, points = show_cards(record["dealer"]["cards"])
    dealer_result = show_result(record["dealer"]["cards"], points)
    embed.set_field_at(0, name=f"莊家", value=f"手牌: {cards}\n結果: {dealer_result}", inline=False)

    temp = {}
    for i, p in enumerate(record["players"]):
        cards, points = show_cards(p["cards"])
        result = show_result(p["cards"], points)

        if result == "Black Jack":
            if dealer_result == "Black Jack":
                balance = 0
            else:
                balance = p["bet_amount"] * 1.5
        elif result == "Five-card":
            if dealer_result == "Five-card":
                balance = 0
            elif dealer_result == "Black Jack":
                balance = p["bet_amount"] * -1.5
            else:
                # balance = p["bet_amount"] * 1.25
                balance = p["bet_amount"] * 3
        elif result == "Busted":
            if dealer_result == "Black Jack":
                balance = p["bet_amount"] * -1.5
            else:
                balance = p["bet_amount"] * -1
        else:
            if dealer_result == "Black Jack":
                balance = p["bet_amount"] * -1.5
            elif dealer_result == "Five-card":
                balance = p["bet_amount"] * -1
            elif dealer_result == "Busted":
                balance = p["bet_amount"]
            else:
                if int(result) == int(dealer_result):
                    balance = 0
                elif int(result) > int(dealer_result):
                    balance = p["bet_amount"]
                else:
                    balance = p["bet_amount"] * -1
        balance = int(balance) + p["bet_amount"]

        id = str(p["user_id"])
        if temp.get(id):
            temp[id]["balance"] += balance
            temp[id]["profit"] += balance - p["bet_amount"]
        else:
            temp[id] = {}
            temp[id]["balance"] = balance
            temp[id]["profit"] = balance - p["bet_amount"]
            temp[id]["user_name"] = p["user_name"]


        embed.set_field_at(i+1, name=p["user_name"], value=f"籌碼: {record['players'][i]['bet_amount']} :coin:\n手牌: {cards}\n結果: {result}\n金額: {balance - p['bet_amount']} :coin:", inline=False)

    # await record["message"].edit(embed=embed, content="Result")
    all_balance = ""
    db = DB()
    for item in temp:
        if temp[item]["profit"] >= 0:
            b = db.get_balance(item, int(temp[item]['balance']))
            all_balance += f"<@!{item}> 贏了 {temp[item]['profit']} :coin:, 現在有 {b} :coin:\n"
        else:
            b = db.get_balance(item, int(temp[item]['balance']))
            all_balance += f"<@!{item}> 輸了 {temp[item]['profit']*-1} :coin:, 現在有 {b} :coin:\n"    
    db.close()
    await record["message"].edit(view=None)
    await record["message"].channel.send(embed=embed, content=f"結果:\n{all_balance}")

    record["step"] += 1

def show_cards(cards: list):
    now_cards = ""
    points = 0
    a_count = 0
    for card in cards:
        now_cards += f"|:{deck_of_card[card]['suit']}:{deck_of_card[card]['number']}| "
        points += deck_of_card[card]['point']
        if deck_of_card[card]['point'] == 11:
            a_count += 1
    for _ in range(a_count):
        points = points - 10 if points > 21 else points
    return now_cards, points
        
def show_result(cards:list, points:int):
    if len(cards) == 2 and points == 21:
        return "Black Jack"
    elif len(cards) == 5 and points <= 21:
        return "Five-card"
    elif points > 21:
        return "Busted"
    else:
        return str(points) 

def hit_a_card(cards: list):
    rand_num = random.randint(0, len(cards)-1)
    hit = cards.pop(rand_num)
    # card = f"|:{deck_of_card[hit]['suit']}:{deck_of_card[hit]['number']}| "
    return hit