import configparser
import logging
from datetime import datetime

import aiohttp
import discord
from discord.ext import commands, tasks

config = configparser.ConfigParser()
config.read("config.ini", encoding='utf-8')

file_log = logging.FileHandler('Log.log', encoding='utf-8')
console_out = logging.StreamHandler()

logging.basicConfig(handlers=(file_log, console_out),
                    format='[%(asctime)s | %(levelname)s]: %(message)s',
                    datefmt='%m.%d.%Y %H:%M:%S',
                    level=logging.INFO)

bot = commands.Bot(command_prefix="wotsb.", intents=discord.Intents.default())


@bot.event
async def on_ready():
    logging.info(f"Авторизован под: {bot.user}")
    watching = discord.Activity(
        name="за серверами",
        type=discord.ActivityType.watching,
        timestamps={"start": datetime.now()}
    )
    await bot.change_presence(activity=watching)
    push_monitoring_data.start()


@bot.tree.command(
    name="info",
    description="Информация о боте"
)
async def info(ctx: discord.Interaction):
    await send_analytics(user_id=ctx.user.id,
                         action_name=ctx.command.name)
    embed = discord.Embed(
        title="World Of Tanks Status",
        description="Бот создан для отображения статуса серверов WOT\n"
                    "Автор: [Shandy](https://github.com/Shandeika)\n"
                    "Репозиторий: [GitHub](https://github.com/Shandeika/wot-status-bot)\n"
                    "Сервер поддержки: [Shandy`s server](https://discord.gg/2BEfEAm)\n"
                    "Источник данных: https://wgstatus.com")
    embed.add_field(name=f"Количество серверов", value=len(ctx.client.guilds), inline=False)
    embed.add_field(name="Мониторинг бота",
                    value="https://bots.server-discord.com/857360003512795167\n"
                          "https://top.gg/bot/857360003512795167\n"
                          "https://boticord.top/bot/857360003512795167\n")
    await ctx.response.send_message(embed=embed)


@bot.tree.command(
    name="status",
    description="Статус серверов World of Tanks"
)
@discord.app_commands.choices(
    server=[
        discord.app_commands.Choice(name="WoT RU", value=1),
        discord.app_commands.Choice(name="WoT Common Test", value=2),
        discord.app_commands.Choice(name="WoT Sandbox", value=3),
        discord.app_commands.Choice(name="WoT EU", value=4),
        discord.app_commands.Choice(name="WoT NA(USA)", value=5),
        discord.app_commands.Choice(name="WoT ASIA", value=6),
        discord.app_commands.Choice(name="WOT360 CN", value=7),
        discord.app_commands.Choice(name="WoT ST", value=8)
    ]
)
@discord.app_commands.describe(
    server='Сервер, о котором нужно получить информацию'
)
async def status(ctx: discord.Interaction, server: int = None):
    await send_analytics(user_id=ctx.user.id,
                         action_name=f"{ctx.command.name}_{server if server else 'all'}")
    status_emoji = {
        "online": "<:online:741779665026547813>",
        "offline": "<:offline:741779665017897047>"
    }
    status_word = {
        "online": "Онлайн",
        "offline": "Выключен"
    }
    embed = discord.Embed(title="Статус серверов World Of Tanks",
                          description="Все данные взяты из открытых источников, автор не несет ответственности за "
                                      "правильность данных.")
    embed.set_footer(text="При поддержке https://wgstatus.com/")
    try:
        results: list = await get_wot_data()
    except IncorrectResponse:
        embed.add_field(name="Ошибка API", value="Сервер не смог ответить")
        return await ctx.response.send_message(embed=embed, ephemeral=True)
    if server is None:
        embed.description += "\n\n⚠ Для более подробной информации об отдельном сервере укажите параметр `server` при " \
                             "выполнении команды"
        for i, item in enumerate(results):
            if i < 1 or i > 8:
                continue
            data: dict = results[i].get('data')
            title = f"{data.get('title')} {':flag_' + data.get('flag') + ':' if data.get('flag') is not None else ''}\n"  # Название сервера и его флаг
            description = f"Версия: **{data.get('version')}**\nПоследнее обновление:\n<t:{data.get('version_updated_at')}>\nОбщий онлайн: `{data.get('online') if data.get('online') is not None else 'Недоступно'}`"  # Данные о онлайне и версии
            embed.add_field(name=title, value=description, inline=True)
    elif isinstance(server, int):
        data: dict = results[server].get('data')
        title = f"{data.get('title')} {':flag_' + data.get('flag') + ':' if data.get('flag') is not None else ''}"
        embed.add_field(name=title,
                        value=f"Версия: **{data.get('version')}**\nПоследнее обновление: <t:{data.get('version_updated_at')}>\nОбщий онлайн: `{data.get('online')}`", inline=False)
        servers = list()
        for server in data.get('servers'):
            server_title = f"Название: `{server.get('name')}`"
            server_online = f"{status_emoji.get(server.get('status'))} Онлайн: `{server.get('online')}`" if server.get(
                'online') is not None else f"{status_emoji.get(server.get('status'))} {status_word.get(server.get('status'))}"
            servers.append([server_title, server_online])
        for server in servers:
            embed.add_field(name=server[0], value=server[1], inline=True)
    await ctx.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(
    name="feedback",
    description="Отправить отзыв/предложение для разработчика"
)
async def feedback(ctx: discord.Interaction):
    await send_analytics(user_id=ctx.user.id,
                         action_name=ctx.command.name)

    class Feedback(discord.ui.Modal, title="Отправить отзыв/предложение для разработчика"):
        theme = discord.ui.TextInput(
            label="Тема",
            style=discord.TextStyle.short,
            required=True,
            placeholder="Тема отзыва/предложения",
            custom_id="theme"
        )
        feedback = discord.ui.TextInput(
            label="Отзыв/предложение",
            style=discord.TextStyle.long,
            required=True,
            placeholder="Текст отзыва/предложения",
            custom_id="feedback"
        )

        async def on_submit(self, interaction: discord.Interaction, /) -> None:
            feedback_embed = discord.Embed(title=self.theme, description=self.feedback, timestamp=datetime.now(), )
            feedback_embed.set_footer(
                text=f"USER_ID={interaction.user.id} GUILD_ID={interaction.guild.id} GUILD_NAME={interaction.guild.name}")
            feedback_embed.set_author(name=interaction.user.name, icon_url=interaction.user.avatar.url)
            user_embed = discord.Embed(title="Отправлено", description="Спасибо за ваше предложение/отзыв!")
            await interaction.response.send_message(embed=user_embed, ephemeral=True)
            async with aiohttp.ClientSession() as session:
                webhook = discord.Webhook.from_url(config["Config"]["feedback_webhook_url"], session=session)
                await webhook.send(embed=feedback_embed)

    modal = Feedback()

    await ctx.response.send_modal(modal)


async def get_wot_data():
    async with aiohttp.ClientSession() as session:
        async with session.get("https://api.wgstatus.com/api/data/wot") as response:
            if response.status != 200:
                raise IncorrectResponse
            data = await response.json()
            return data["results"][0]


async def send_analytics(user_id, action_name):
    """
    Send record to Google Analytics
    """
    params = {
        'client_id': str(user_id),
        'user_id': str(user_id),
        'events': [{
            'name': action_name,
            'params': {
                'engagement_time_msec': '1',
            }
        }],
    }
    async with aiohttp.ClientSession() as session:
        await session.post(
            f'https://www.google-analytics.com/'
            f'mp/collect?measurement_id={config["Config"]["google_gcode"]}&api_secret={config["Config"]["google_secret_key"]}',
            json=params)


class IncorrectResponse(Exception):
    pass


@tasks.loop(minutes=5)
async def push_monitoring_data():
    # top.gg monitoring
    async with aiohttp.ClientSession(headers={'Authorization': config["Config"]["top_gg_token"]}) as session:
        async with session.post(f"https://top.gg/api/bots/{bot.user.id}/stats",
                                data={"server_count": len(bot.guilds), "shard_count": 1}) as response:
            if response.status == 200:
                logging.info(f"Monitoring top.gg push success. {response.status}, {len(bot.guilds)}")
            else:
                logging.error(f"Monitoring top.gg push failed. {response.status}, {len(bot.guilds)}")


bot.run(config["Config"]["token"])
