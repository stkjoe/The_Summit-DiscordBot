import discord
from discord.utils import get
import sqlalchemy
from datetime import datetime, timedelta
import os
import requests
import json

with open('secret.txt') as json_file:
    data = json.load(json_file)
    TOKEN = data['TOKEN']
    ROLE_ID = data['ID']['ROLE']
    SITE = data['SITE']
    DB = data['DB']

    
roles = [x.lower() for x in list(ROLE_ID.keys())]
channel_cooldown = {}
COOLDOWN = 30

db = sqlalchemy.create_engine(
    sqlalchemy.engine.url.URL(
        drivername=DB['DRIVER_NAME'],
        username=DB['USER_NAME'],
        password=DB['PASSWORD'],
        database=DB['DATABASE'],
        query={"unix_socket": "/cloudsql/{}".format(DB['CONNECTION_NAME'])},
    )
)

with db.connect() as conn:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS teams ("
        "team_id SMALLINT AUTO_INCREMENT PRIMARY KEY, "
        "team_name VARCHAR(30) NOT NULL, "
        "team_tag VARCHAR(3) NOT NULL, "
        ""
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS users ("
        "discord_id BIGINT, "
        "osu_id INT NOT NULL, "
        "team_id SMALLINT, "
        "FOREIGN KEY (team_id) REFERENCES teams(team_id)"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS roles ("
        "participant BOOLEAN DEFAULT false, "
        "captain BOOLEAN DEFAULT false, "
        "song_selector BOOLEAN DEFAULT false, "
        "commentator BOOLEAN DEFAULT false, "
        "judge BOOLEAN DEFAULT false, "
        "chat_moderator BOOLEAN DEFAULT false, "
        "website_maintainer BOOLEAN DEFAULT false, "
        "graphics_designer BOOLEAN DEFAULT false, "
        "staff BOOLEAN DEFAULT false, "
        "organizer BOOLEAN DEFAULT false, "
        "discord_id BIGINT, "
        "FOREIGN KEY (discord_id) REFERENCES users(discord_id) ON DELETE CASCADE"
    )

class Client(discord.Client):

    def on_cooldown(self, message, command):
        try:
            last_time = channel_cooldown[message.channel.id][command]
        except KeyError:
            try:
                channel_cooldown[message.channel.id][command] = datetime.now()
            except KeyError:
                channel_cooldown[message.channel.id] = {}
                channel_cooldown[message.channel.id][command] = datetime.now()
            return False
        last_time_since = (datetime.now() - last_time).total_seconds()
        if last_time_since <= COOLDOWN:
            channel_cooldown[message.channel.id][command] = datetime.now()
            return last_time_since
        return False

    def build_embed(self, title="", description="", color=0xffffff, thumbnail=""):
        embed = discord.Embed(
            title=title,
            description=description,
            color=color
        )
        if thumbnail:
            embed.set_thumbnail(url=thumbnail)
        return embed

    async def send_embed(self, message, content, command):
        seconds = self.on_cooldown(message, command)
        if seconds:
            resp = discord.Embed(
                title="Command is on cooldown!",
                description="{} seconds remain".format(int(30 - seconds)),
                color=0xff0000
            )
            temp = await message.channel.send(embed=resp, delete_after=3)
        else:
            await message.channel.send(embed=content)

    async def add_role(self, member, role_id):
        role = get(member.guild.roles, id=role_id)
        await message.author.add_roles(role)

    async def on_member_join(self, member):
        with db.connect() as conn:
            user_roles = conn.execute("SELECT {} FROM roles WHERE discord_id={}".format(", ".join(roles), member.id)).fetchone()
            for role in roles:
                if user_roles[role]:
                    await add_role(member, ROLE_ID[role.upper()])

    async def on_message(self, message):
        if message.author.bot:
            # Ignore own messages
            return
        if message.content.startswith("!"):
            text_message = message.content.lower()
            if text_message.startswith("!help"):
                resp = self.build_embed(
                    title="Help",
                    description="\n".join(
                        [
                            "**General**",
                            "``!live``: Check if the contest Twitch stream is live",
                            "``!site`` / ``!website``: Displays the contest Website link",
                            "``!twitch``: Displays the contest Twitch link",
                            "``!youtube``: Displays the contest YouTube link",
                            "``!twitter``: Displays the contest Twitter link"
                        ]
                    ),
                    color=0xffffff,
                )
                await self.send_embed(message, resp, "help")
            elif text_message.startswith("!live"):
                twitch_html = requests.get("https://api.twitch.tv/kraken/streams/{}?client_id={}".format(SITE['TWITCH'].split("twitch.tv/")[1], TOKEN['TWITCH']))
                twitch = json.loads(twitch_html.content)
                try:
                    twitch["stream"]
                    resp = self.build_embed(
                        title="The Summit ORG is LIVE",
                        description=SITE['TWITCH'],
                        color=0x6441a5,
                        thumbnail="https://i.imgur.com/7QEx1ny.png"
                    )
                except KeyError:
                    resp = self.build_embed(
                        title="The Summit ORG is NOT Live"
                    )
                await self.send_embed(message, resp, "live")
            elif text_message.startswith("!site") or text_message.startswith("!website"):
                resp = self.build_embed(
                    title="The Summit Website",
                    description=SITE['WEBSITE'],
                    thumbnail="" #TODO: change image to official one
                )
                await self.send_embed(message, resp, "site")
            elif text_message.startswith("!twitch"):
                resp = self.build_embed(
                    title="Twitch Channel",
                    description=SITE['TWITCH'],
                    color=0x6441a5,
                    thumbnail="https://i.imgur.com/7QEx1ny.png"
                )
                await self.send_embed(message, resp, "twitch")
            elif text_message.startswith("!youtube"):
                resp = self.build_embed(
                    title="YouTube Channel",
                    description=SITE['YOUTUBE'], #TODO: add youtube domain
                    color=0xc4302b,
                    thumbnail="https://i.imgur.com/eyLvJEo.png"
                )
                await self.send_embed(message, resp, "youtube")
            elif text_message.startswith("!twitter"):
                resp = self.build_embed(
                    title="Twitter Profile",
                    description=SITE['TWITTER'],
                    color=0xc4302b,
                    thumbnail="https://i.imgur.com/eyLvJEo.png" #TODO: change to twitter logo
                )
                await self.send_embed(message, resp, "twitter")

client = Client()
client.run(TOKEN['DISCORD'])