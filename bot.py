import configparser
import logging
from datetime import datetime

import aiohttp
from dis_snek import listen, Intents, ActivityType, Task, IntervalTrigger, ShortText, ParagraphText, ModalContext, \
    EmbedAuthor, EmbedFooter
from dis_snek.client import Snake
from dis_snek.models import Activity, slash_command, Embed, InteractionContext, slash_option, OptionTypes, \
    SlashCommandChoice, Modal, Webhook

config = configparser.ConfigParser()
config.read("config.ini", encoding='utf-8')

file_log = logging.FileHandler('Log.log', encoding='utf-8')
console_out = logging.StreamHandler()

logging.basicConfig(handlers=(file_log, console_out),
                    format='[%(asctime)s | %(levelname)s]: %(message)s',
                    datefmt='%m.%d.%Y %H:%M:%S',
                    level=logging.INFO)

bot = Snake(intents=Intents.DEFAULT, sync_interactions=True)


@listen()
async def on_startup():
    print(f"Авторизован под: {bot.user}")
    await bot.change_presence(activity=Activity(type=ActivityType.WATCHING, name="за серверами"))
    push_monitoring_data.start()


@slash_command(
    name="info",
    description="Информация о боте"
)
async def info(ctx: InteractionContext):
    await send_analytics(user_id=ctx.author.id,
                         action_name=ctx.invoke_target)
    embed = Embed(
        title="World Of Tanks Status",
        description="Бот создан для отображения статуса серверов WOT\n"
                    "Автор: [Shandy](https://github.com/Shandeika)\n"
                    "Репозиторий: [GitHub](https://github.com/Shandeika/wot-status-bot)\n"
                    "Сервер поддержки: [Shandy`s server](https://discord.gg/2BEfEAm)\n"
                    "Источник данных: https://wgstatus.com")
    embed.add_field(name=f"Количество серверов", value=len(ctx.bot.guilds), inline=False)
    embed.add_field(name="Мониторинг бота",
                    value="https://bots.server-discord.com/857360003512795167\n"
                          "https://top.gg/bot/857360003512795167\n"
                          "https://boticord.top/bot/857360003512795167\n")
    await ctx.send(embeds=embed)


@slash_command(
    name="status",
    description="Статус серверов World of Tanks"
)
@slash_option(
    name="server",
    description="Сервер, о котором нужно получить информацию",
    required=False,
    opt_type=OptionTypes.INTEGER,
    choices=[
        SlashCommandChoice(name="WoT RUBY", value=1),
        SlashCommandChoice(name="WoT EU", value=2),
        SlashCommandChoice(name="WoT RUBY Public Test", value=3),
        SlashCommandChoice(name="WoT Common Test Global", value=4),
        SlashCommandChoice(name="WoT NA(USA)", value=5),
        SlashCommandChoice(name="WoT ASIA", value=6),
        SlashCommandChoice(name="WOT360 CN", value=7),
        SlashCommandChoice(name="WoT Sandbox", value=8),
        SlashCommandChoice(name="WoT ST RUBY", value=9),
        SlashCommandChoice(name="WoT ST", value=10),
    ]
)
async def status(ctx: InteractionContext, server: int = None):
    await send_analytics(user_id=ctx.author.id,
                         action_name=f"{ctx.invoke_target}_{server if server else 'all'}")
    status_emoji = {
        "online": "<:online:741779665026547813>",
        "offline": "<:offline:741779665017897047>"
    }
    status_word = {
        "online": "Онлайн",
        "offline": "Выключен"
    }
    embed = Embed(title="Статус серверов World Of Tanks",
                  description="Все данные взяты из открытых источников, автор не несет ответственности за правильность данных.")
    embed.set_footer(text="При поддержке https://wgstatus.com/")
    try:
        results: list = await get_wot_data()
    except IncorrectResponse:
        embed.add_field(name="Ошибка API", value="Сервер не смог ответить")
        return await ctx.send(embeds=embed, ephemeral=True)
    if server is None:
        embed.description += "\n\n⚠ Для более подробной информации об отдельном сервере укажите параметр `server` при выполнении команды"
        for i, item in enumerate(results):
            if i < 1 or i > 10:
                continue
            data: dict = results[i].get('data')
            title = f"{data.get('title')} {':flag_' + data.get('flag') + ':' if data.get('flag') is not None else ''}\n"  # Название сервера и его флаг
            description = f"Версия: **{data.get('version')}**\nПоследнее обновление:\n<t:{data.get('version_updated_at')}>\nОбщий онлайн: `{data.get('online') if data.get('online') is not None else 'Недоступно'}`"  # Данные о онлайне и версии
            embed.add_field(name=title, value=description, inline=True)
    elif isinstance(server, int):
        data: dict = results[server].get('data')
        title = f"{data.get('title')} {':flag_' + data.get('flag') + ':' if data.get('flag') is not None else ''}"
        embed.add_field(name=title,
                        value=f"Версия: **{data.get('version')}**\nПоследнее обновление: <t:{data.get('version_updated_at')}>\nОбщий онлайн: `{data.get('online')}`")
        servers = list()
        for server in data.get('servers'):
            server_title = f"Название: `{server.get('name')}`"
            server_online = f"{status_emoji.get(server.get('status'))} Онлайн: `{server.get('online')}`" if server.get('online') is not None else f"{status_emoji.get(server.get('status'))} {status_word.get(server.get('status'))}"
            servers.append([server_title, server_online])
        for server in servers:
            embed.add_field(name=server[0], value=server[1], inline=True)
    await ctx.send(embeds=embed, ephemeral=True)


@slash_command(
    name="feedback",
    description="Отправить отзыв/предложение для разработчика"
)
async def feedback(ctx: InteractionContext):
    await send_analytics(user_id=ctx.author.id,
                         action_name=ctx.invoke_target)
    modal = Modal(
        title="Отправить отзыв/предложение для разработчика",
        components=[
            ShortText(label="Тема", custom_id="theme", required=True, placeholder="Тема отзыва/предложения"),
            ParagraphText(label="Отзыв/предложение", custom_id="feedback", required=True,
                          placeholder="Текст отзыва/предложения"),
        ]
    )
    await ctx.send_modal(modal=modal)
    modal_ctx: ModalContext = await ctx.bot.wait_for_modal(modal)
    await modal_ctx.send(embed=Embed(title="Отправлено", description="Спасибо за ваше предложение/отзыв!"),
                         ephemeral=True)
    await Webhook.from_url(config["Config"]["feedback_webhook_url"], bot).send(
        embed=Embed(title=modal_ctx.responses.get("theme"), description=modal_ctx.responses.get("feedback"),
                    author=EmbedAuthor(name=ctx.author.username, icon_url=ctx.author.avatar.url), timestamp=datetime.now(),
                    footer=EmbedFooter(text=f"USER_ID={ctx.author.id} GUILD_ID={ctx.guild.id} GUILD_NAME={ctx.guild.name}")))


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


@Task.create(IntervalTrigger(minutes=1))
async def push_monitoring_data():
    if config["Config"]["sdc_token"]:
        # SDC monitoring
        async with aiohttp.ClientSession(headers={'Authorization': f'SDC {config["Config"]["sdc_token"]}'}) as session:
            async with session.post(f"https://api.server-discord.com/v2/bots/{bot.user.id}/stats",
                                    data={'shards': 1, 'servers': len(bot.guilds)}) as response:
                if response.status == 200:
                    logging.info(f"Monitoring SDC push success. {response.status}, {len(bot.guilds)}")
                else:
                    logging.error(f"Monitoring SDC push failed. {response.status}, {len(bot.guilds)}")
    if config["Config"]["top_gg_token"]:
        # top.gg monitoring
        async with aiohttp.ClientSession(headers={'Authorization': config["Config"]["top_gg_token"]}) as session:
            async with session.post(f"https://top.gg/api/bots/{bot.user.id}/stats",
                                    data={"server_count": len(bot.guilds), "shard_count": 1}) as response:
                if response.status == 200:
                    logging.info(f"Monitoring top.gg push success. {response.status}, {len(bot.guilds)}")
                else:
                    logging.error(f"Monitoring top.gg push failed. {response.status}, {len(bot.guilds)}")
    if config["Config"]["boticord_token"]:
        # boticord monitoring
        async with aiohttp.ClientSession(headers={'Authorization': config["Config"]["boticord_token"], "Content-Type": "application/json"}) as session:
            async with session.post(f"https://api.boticord.top/v1/stats",
                                    json={"servers": len(bot.guilds)}) as response:
                if response.status == 200:
                    logging.info(f"Monitoring boticord push success. {response.status}, {len(bot.guilds)}")
                else:
                    logging.error(f"Monitoring boticord push failed. {response.status}, {len(bot.guilds)}")


bot.start(config["Config"]["token"])
