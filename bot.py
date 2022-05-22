import configparser
import logging

import requests
from dis_snek import listen, Intents, ActivityType
from dis_snek.client import Snake
from dis_snek.models import Activity, slash_command, Embed, InteractionContext, slash_option, OptionTypes, SlashCommandChoice

config = configparser.ConfigParser()
config.read("config.ini", encoding='utf-8')

file_log = logging.FileHandler('Log.log', encoding='utf-8')
console_out = logging.StreamHandler()

logging.basicConfig(handlers=(file_log, console_out),
                    format='[%(asctime)s | %(levelname)s]: %(message)s',
                    datefmt='%m.%d.%Y %H:%M:%S',
                    level=logging.DEBUG)

bot = Snake(intents=Intents.DEFAULT, sync_interactions=True)


@listen()
async def on_ready():
    print(f"Авторизован под: {bot.user}")
    await bot.change_presence(activity=Activity(type=ActivityType.WATCHING, name="за серверами"))


@slash_command(
    name="info",
    description="Информация о боте"
)
async def info(ctx: InteractionContext):
    embed = Embed(
        title="World Of Tanks Status",
        description="Бот создан для отображения статуса серверов WOT\n"
                    "Автор: [Shandy](https://github.com/Shandeika)\n"
                    "Репозиторий: [GitHub](https://github.com/Shandeika/WOTStatusBot)\n"
                    "Сервер поддержки: [Shandy`s server](https://discord.gg/2BEfEAm)\n"
                    "Источник данных: https://wgstatus.com")
    embed.add_field(name=f"Количество серверов", value=len(ctx.bot.guilds), inline=False)
    embed.add_field(name="Мониторинг бота", value="https://bots.server-discord.com/857360003512795167")
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
        SlashCommandChoice(name="WoT RU", value=1),
        SlashCommandChoice(name="WoT Common Test", value=2),
        SlashCommandChoice(name="WoT Sandbox", value=3),
        SlashCommandChoice(name="WoT EU", value=4),
        SlashCommandChoice(name="WoT NA(USA)", value=5),
        SlashCommandChoice(name="WoT ASIA", value=6),
        SlashCommandChoice(name="WOT360 CN", value=7),
        SlashCommandChoice(name="WoT ST", value=8)
    ]
)
async def status(ctx: InteractionContext, server: int = None):
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
    request = requests.get("https://api.wgstatus.com/api/data/wot")
    results: list = request.json()["results"][0]
    if request.status_code != 200:
        embed.add_field(name="Ошибка API", value=f"Код ответа сервера: {request.status_code}")
        return await ctx.send(embeds=embed, ephemeral=True)
    elif server is None:
        embed.description += "\n\n⚠ Для более подробной информации об отдельном сервере укажите параметр `server` при выполнении команды"
        for i, item in enumerate(results):
            if i < 1 or i > 8:
                continue
            data: dict = results[i].get('data')
            title = f"{data.get('title')} {':flag_' + data.get('flag') + ':' if data.get('flag') is not None else ''}\n"  # Название сервера и его флаг
            description = f"Версия: **{data.get('version')}**\nПоследнее обновление:\n<t:{data.get('version_updated_at')}>\nОбщий онлайн: `{data.get('online')}`"  # Данные о онлайне и версии
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


bot.start(config["Config"]["token"])
