import logging
import os
from datetime import datetime

import aiohttp
import discord
from discord.ext import commands, tasks

TOKEN = os.environ.get("DISCORD_TOKEN")
GOOGLE_GCODE = os.environ.get("GOOGLE_GCODE")
GOOGLE_SECRET_KEY = os.environ.get("GOOGLE_SECRET_KEY")
TOPGG_TOKEN = os.environ.get("TOPGG_TOKEN")
FEEDBACK_WEBHOOK_URL = os.environ.get("FEEDBACK_WEBHOOK_URL")

console_out = logging.StreamHandler()

logging.basicConfig(handlers=[console_out],
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
        description="Бот для отображения статуса серверов WOT\n"
                    "Автор: [Shandy](https://github.com/Shandeika)\n"
                    "Репозиторий: [GitHub](https://github.com/Shandeika/wot-status-bot)\n"
                    "Сервер поддержки: [Shandy`s server](https://discord.gg/2BEfEAm)\n"
                    "Источник данных: https://wgstatus.com")
    embed.add_field(name=f"Количество серверов", value=len(ctx.client.guilds), inline=False)
    embed.add_field(name="Мониторинг бота",
                    value="https://top.gg/bot/857360003512795167")
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
    await send_analytics(user_id=ctx.user.id, action_name=f"{ctx.command.name}_{server if server else 'all'}")
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
        url = "https://api.wgstatus.com/api/data/wot"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                response.raise_for_status()
                data = await response.json()
                if "results" in data:
                    wot_data = data["results"][0]
                else:
                    embed.add_field(name="Ошибка API", value="Неверный ответ API")
                    logging.error("Invalid API response: 'results' key not found.")
                    return await ctx.response.send_message(embed=embed, ephemeral=True)
    except aiohttp.ClientError as e:
        embed.add_field(name="Ошибка API", value="Сервер не смог ответить")
        logging.exception(e)
        return await ctx.response.send_message(embed=embed, ephemeral=True)
    except (ValueError, KeyError) as e:
        embed.add_field(name="Ошибка API", value=f"Неверный ответ API")
        logging.exception(e)
        return await ctx.response.send_message(embed=embed, ephemeral=True)

    if server is None:
        embed.description += "\n\n⚠ Для более подробной информации об отдельном сервере укажите параметр `server` при " \
                             "выполнении команды"
        for i, item in enumerate(wot_data):
            if 1 <= i <= 8:
                data = item.get('data')
                title = (
                    f"{data.get('title')} {':flag_' + data.get('flag') + ':'}"
                    if data.get('flag') is not None
                    else data.get('title')
                )
                description = await format_server_description(data)
                embed.add_field(name=title, value=description, inline=True)
    elif isinstance(server, int):
        data = wot_data[server].get('data')
        title = (
            f"{data.get('title')} {':flag_' + data.get('flag') + ':'}"
            if data.get('flag') is not None
            else data.get('title')
        )
        embed.add_field(name=title, value=await format_server_description(data), inline=False)
        servers = list()
        for server in data.get('servers'):
            server_title = f"Название: `{server.get('name')}`"
            server_online = (
                f"{status_emoji.get(server.get('status'))} Онлайн: `{server.get('online')}`"
                if server.get('online') is not None
                else f"{status_emoji.get(server.get('status'))} {status_word.get(server.get('status'))}"
            )
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

    if not FEEDBACK_WEBHOOK_URL:
        embed = discord.Embed(
            title="Ошибка обратной связи",
            description="Бот не может отправить ваш отзыв, так как не указана ссылка на обратную связь. Свяжитесь с "
                        "администратором",
            color=discord.Color.red()
        )
        return await ctx.response.send_message(embed=embed, ephemeral=True)

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
                webhook = discord.Webhook.from_url(FEEDBACK_WEBHOOK_URL, session=session)
                await webhook.send(embed=feedback_embed)

    modal = Feedback()

    await ctx.response.send_modal(modal)


async def format_server_description(data):
    description = (
        f"Версия: **{data.get('version')}**\n"
        f"Последнее обновление:\n<t:{data.get('version_updated_at')}>\n"
        f"Общий онлайн: `{data.get('online') if data.get('online') is not None else 'Недоступно'}`"
    )
    return description


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
        async with session.post(
                f'https://www.google-analytics.com/'
                f'mp/collect?measurement_id={GOOGLE_GCODE}&api_secret={GOOGLE_SECRET_KEY}',
                json=params) as response:
            if 200 <= response.status < 300:  # any codes 2**
                logging.info(f"Analytics sent for user {user_id}: {action_name}")
            else:
                logging.error(
                    f"Failed to send analytics for user {user_id}: {action_name}, HTTP status {response.status}")


class IncorrectResponse(Exception):
    pass


@tasks.loop(minutes=5)
async def push_monitoring_data():
    # top.gg monitoring
    if TOPGG_TOKEN:
        async with aiohttp.ClientSession(headers={'Authorization': TOPGG_TOKEN}) as session:
            async with session.post(f"https://top.gg/api/bots/{bot.user.id}/stats",
                                    data={"server_count": len(bot.guilds), "shard_count": 1}) as response:
                if response.status == 200:
                    logging.info(f"Monitoring top.gg push success. {response.status}, {len(bot.guilds)}")
                else:
                    logging.error(f"Monitoring top.gg push failed. {response.status}, {len(bot.guilds)}")


bot.run(TOKEN)
