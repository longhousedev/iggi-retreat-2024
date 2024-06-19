import copy
from json import JSONDecodeError

import discord
import os
import dotenv
import random
import datetime
import json

#import Gemini
import GPT
import api

dotenv.load_dotenv()
token = str(os.getenv('DISCORD_TOKEN'))

bot = discord.Bot(intents=discord.Intents.all())
llm = GPT.GPT()

fixed_prompts = json.load(open('fixed_prompts.json', 'r'))

starter_prompts = {}
chat_history = {}
game_dict = {}
channel_ids = {}

access_dict = {
    "villager": {"public"},
    "werewolf": {"public", "werewolves"},
    "moderator": {"public", "werewolves"},
}


global config
with open("config.json", "r") as f:
    config = json.load(f)


def distribute_role(role: str, amount: int, pool: list) -> list[str]:
    names = []
    for i in range(amount):
        if role == "moderator" and not config["allow_human_moderator"]:
            ai_pool = copy.deepcopy(pool)
            for name in pool:
                if not game_dict[name]["is_ai"]:
                    ai_pool.remove(name)
            name = random.choice(ai_pool)
            pool.remove(name)
            names.append(name)
            game_dict[name]["role"] = role

        else:
            name = random.choice(pool)
            pool.remove(name)
            names.append(name)
            game_dict[name]["role"] = role

    return names


# Send a prompt to llm
async def prompt_llm(ctx: discord.ApplicationContext, llm: any, prompt: str, player_name: str = None) -> None:

    valid_response = False
    count = 0
    error = ""
    while not valid_response and count < config['max_llm_api_tries']:
        if len(error) > 0:
            #prompt += " you are getting this JSONDecodeError: " + error + " can you respond only in json with this fix?"
            prompt += ""
            error = ""
        response = llm.send_prompt(prompt)
        count += 1

        try:
            response_json: dict = json.loads(response)
            for channel_name in response_json:

                # Lowercase
                for key in response_json:
                    response_json[key] = response_json[key].lower()

                # DEBUG
                if channel_name.lower() not in channel_ids:
                    print(channel_name.lower() + " not in " + str(channel_ids))
                channel_name = channel_name.lower()
                if channel_name in channel_ids:
                    cid = channel_ids[channel_name]
                    channel = ctx.guild.get_channel(cid)
                    player_response = response_json[channel_name]
                    # Make sure that sender of message is known
                    if player_name is not None:
                        message = player_name + " says:\n" + player_response

                    else:
                        message = response

                    await channel.send(message)
                    valid_response = True
                    if "$$GAMEOVER$$" in message:
                        pass
        except JSONDecodeError as e:
            error = str(e)

async def llm_thing(ctx: discord.ApplicationContext, user: str):
    game_dict[id]


@bot.slash_command(name="nuke", description="Cleans the server up")
async def nuke(ctx: discord.ApplicationContext):
    for channel in ctx.guild.channels:
        if channel.name != "General":
            await channel.delete()

# Adds the user to the game
@bot.slash_command(name="addme", description="Add yourself to the game")
async def addme(ctx: discord.ApplicationContext):
    game_dict[ctx.author.name] = {
        "name": ctx.author.name,
        "role": "villager",
        "is_ai": False,
        "id": ctx.author.id,
    }
    await ctx.respond(ctx.user.name + ": " + str(ctx.user.id) + " has been added to the game!")


@bot.slash_command(name="startgame", description="Start the game")
async def startgame(ctx: discord.ApplicationContext):
    # Create a category for gameplay
    game_category = await ctx.guild.create_category("Gameplay")
    channel_ids["gameplay"] = game_category.id

    # Check if valid number of players
    no_players = len(game_dict)
    if no_players <= config["max_players"]:

        # Add AI players to the game
        names: list = config["ai_names"]
        ai_to_add = config["max_players"] - no_players
        for i in range(ai_to_add):
            character_name = random.choice(names)
            names.remove(character_name)
            game_dict[character_name] = {"role": "villager", "name": character_name, "is_ai": True}

        # Work out roles
        werewolf_overwrite = {ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False, send_messages=False)}
        public_overwrite = {ctx.guild.default_role: discord.PermissionOverwrite(read_messages=True, send_messages=False)}

        special_role_pool = list(game_dict.keys())
        random.shuffle(special_role_pool)

        moderators = distribute_role("moderator", config["no_moderators"], special_role_pool)
        werewolves = distribute_role("werewolf", config["no_werewolves"], special_role_pool)
        villagers = copy.deepcopy(special_role_pool)
        characters_in_play = werewolves + villagers

        # Make sure discord players can only see channels they should see
        for name in moderators + werewolves:
            if not game_dict[name]["is_ai"]:
                id = game_dict[name]["id"]
                werewolf_overwrite[ctx.guild.get_member(id)] = discord.PermissionOverwrite(read_messages=True)

        print(game_dict)

        # Create channels
        category_id = channel_ids["gameplay"]

        werewolf_chat = await ctx.guild.create_text_channel("Werewolves", category=ctx.guild.get_channel(category_id),
                                                            overwrites=werewolf_overwrite)
        public_chat = await ctx.guild.create_text_channel("Public", category=ctx.guild.get_channel(category_id),
                                                          overwrites=public_overwrite)

        channel_ids["werewolves"] = werewolf_chat.id
        channel_ids["public"] = public_chat.id

        for player_id in game_dict:
            player = game_dict[player_id]

            # Player is an AI give them their initial prompt
            if player["is_ai"]:

                if player["role"] == "moderator":

                    prompt_list: list = config["initial_moderator_prompt"]
                    prompt = ""
                    for line in prompt_list:
                        prompt += line

                    prompt = prompt.replace("$NAMES", str(game_dict))
                    prompt = prompt.replace("$USER", player["name"])
                    prompt = prompt.replace("$ROLE", player["role"])
                    prompt = prompt.replace("$NO_PLAYERS", str(len(characters_in_play)))
                    prompt = prompt.replace("$NO_WEREWOLVES", str(config["no_werewolves"]) + " werewolf ")
                    prompt = prompt.replace("$NO_VILLAGERS", str(len(characters_in_play) - config["no_werewolves"]))

                elif player["role"] == "villager" or player["role"] == "werewolf":

                    prompt_list: list = config["initial_villager_prompt"]
                    prompt = ""
                    for line in prompt_list:
                        prompt += line

                    prompt = prompt.replace("$NAMES", str(characters_in_play))
                    prompt = prompt.replace("$USER", player["name"])
                    prompt = prompt.replace("$ROLE", player["role"])
                    prompt = prompt.replace("$NO_PLAYERS", str(len(characters_in_play)))
                    prompt = prompt.replace("$NO_WEREWOLVES", str(config["no_werewolves"]) + " werewolf ")
                    prompt = prompt.replace("$MODERATOR", str(moderators))

                    if player["role"] == "villager":
                        channels_text = config["public_channel_description"]
                        prompt = prompt.replace("$CHANNELS", channels_text)

                    elif player["role"] == "werewolf":
                        channels_text = config["public_channel_description"] + " " + config["werewolf_chanel_description"]
                        prompt = prompt.replace("$CHANNELS", channels_text)

                starter_prompts[player_id] = prompt

            # Make sure discord players know which role they are
            else:
                await ctx.guild.get_member(player["id"]).send("You are a " + player["role"] + " in the game!")

        # Gameplay loop
        while True:

            # Make sure turn order is randomised WITH moderator(s) starting
            random.shuffle(characters_in_play)
            turn_order: list = moderators + characters_in_play

            for player_id in turn_order:

                # Handle AI players
                if game_dict[player_id]["is_ai"]:
                    # Get chatroom history
                    for channel_name in channel_ids:
                        cid = channel_ids[channel_name]
                        channel = ctx.guild.get_channel(cid)

                        chat_history[channel_name] = []
                        history_list = chat_history[channel_name]
                        # Make sure that the channel is actually used for text
                        if channel.category_id == channel_ids["gameplay"]:
                            async for message in ctx.guild.get_channel(channel_ids[channel_name]).history(limit=None):
                                history_list.append(message.system_content)

                    # Give the player their chat history
                    prompt = starter_prompts[player_id]

                    for i in reversed(chat_history["public"]):
                        prompt += "\n {[public channel] : " + i  + " }"

                    if game_dict[player_id]["role"] == "werewolf" or game_dict[player_id]["role"] == "moderator":
                        for i in reversed(chat_history["werewolves"]):
                            prompt +=  "\n {[werewolves channel] : " + i  + " }"

                    await prompt_llm(ctx, llm, prompt, game_dict[player_id]["name"])

                #Handle discord players
                else:

                    available_channels = access_dict[game_dict[player_id]["role"]]
                    for channel_name in available_channels:
                        cid = channel_ids[channel_name]
                        channel = ctx.guild.get_channel(cid)
                        overwrite = channel.overwrites
                        pid = game_dict[player_id]["id"]
                        await channel.set_permissions(ctx.guild.get_member(pid), read_messages=True, send_messages=True)
                        discord_player = ctx.guild.get_member(pid)
                        mention_string = discord_player.mention
                        instructions = "It is your turn " + mention_string + "! Please respond in this " + channel_name + " channel. " + "Write ... if you do not wish to say anything here at this time."
                        intro = game_dict[player_id]["name"] + " says:"
                        sent_message = await channel.send(instructions)
                        await channel.send(intro)
                        wait = await bot.wait_for("message", check=lambda m: m.author == discord_player and m.channel == channel)
                        overwrite[pid] = discord.PermissionOverwrite(read_messages=True, send_messages=False)
                        await channel.set_permissions(ctx.guild.get_member(pid), read_messages=True, send_messages=False)
                        await sent_message.delete()




        # await werewolf_chat.send("You are the werewolves, eat your prey before they find out your true identity!")
        # await public_chat.send("Welcome to LLM werewolf!")

        # await prompt_llm(ctx, llm, fixed_prompts["moderator_start"])


@bot.slash_command(name="endgame", description="Ends the game")
async def endgame(ctx: discord.ApplicationContext):
    for id in channel_ids.values():
        await ctx.guild.get_channel(id).delete()


@bot.slash_command(name="chatgpt", description="Send a message to the llm")
async def chatgpt(ctx: discord.ApplicationContext):
    #APIT function here
    await ctx.respond("TODO!")


# @bot.slash_command(name="say", description="bot will repeat")
# async def say(ctx: discord.ApplicationContext):
#     await ctx.respond(ctx.message.content)

bot.run(token)
