import logging
import os
from datetime import datetime

import aiohttp
import discord
from discord.ext import commands, tasks, pages

from wgstatus import WGStatusAPI, Cluster

TOKEN = os.environ.get("DISCORD_TOKEN")
GOOGLE_GCODE = os.environ.get("GOOGLE_GCODE")
GOOGLE_SECRET_KEY = os.environ.get("GOOGLE_SECRET_KEY")
TOPGG_TOKEN = os.environ.get("TOPGG_TOKEN")
FEEDBACK_WEBHOOK_URL = os.environ.get("FEEDBACK_WEBHOOK_URL")

console_out = logging.StreamHandler()

logging.basicConfig(
    handlers=[console_out],
    format="[%(asctime)s | %(levelname)s]: %(message)s",
    datefmt="%m.%d.%Y %H:%M:%S",
    level=logging.INFO,
)

bot = commands.Bot(command_prefix="wotsb.", intents=discord.Intents.default())


@bot.event
async def on_ready():
    logging.info(f"Авторизован под: {bot.user}")
    watching = discord.Activity(
        name="за серверами",
        type=discord.ActivityType.watching,
        timestamps={"start": datetime.now()},
    )
    await bot.change_presence(activity=watching)
    push_monitoring_data.start()


@bot.application_command(name="info", description="Информация о боте")
async def info(ctx: discord.ApplicationContext):
    await send_analytics(user_id=ctx.user.id, action_name=ctx.command.name)
    embed = discord.Embed(
        title="World Of Tanks Status",
        description="Бот для отображения статуса серверов WOT\n"
        "Автор: [Shandy](https://github.com/Shandeika)\n"
        "Репозиторий: [GitHub](https://github.com/Shandeika/wot-status-bot)\n"
        "Сервер поддержки: [Shandy`s server](https://discord.gg/2BEfEAm)\n"
        "Источник данных: https://wgstatus.com",
    )
    embed.add_field(
        name=f"Количество серверов", value=str(len(ctx.bot.guilds)), inline=False
    )
    embed.add_field(
        name="Мониторинг бота", value="https://top.gg/bot/857360003512795167"
    )
    await ctx.response.send_message(embed=embed)


@bot.application_command(name="status", description="Статус серверов World of Tanks")
async def status(ctx: discord.ApplicationContext):
    await send_analytics(user_id=ctx.user.id, action_name=f"{ctx.command.name}")
    paginator_pages = []
    wgs = await WGStatusAPI.create()
    main_page = await generate_main_status_page(wgs)
    paginator_pages.append(
        pages.PageGroup(
            pages=[main_page],
            label="Все сервера",
            emoji="🏠",
            description="Все сервера WOT",
            default=True,
            show_disabled=False,
        )
    )
    for cluster in wgs.clusters:
        embed = await generate_cluster_status_page(cluster)
        emoji = cluster.flag_to_emoji()
        page = pages.PageGroup(
            pages=[embed],
            label=cluster.title,
            use_default_buttons=False,
            show_disabled=False,
        )
        if emoji:
            emoji = discord.PartialEmoji.from_str(emoji)
            page.emoji = emoji
        paginator_pages.append(page)
    paginator = pages.Paginator(
        pages=paginator_pages,
        disable_on_timeout=True,
        show_menu=True,
        menu_placeholder="Выберите нужный сервер",
        show_indicator=False,
        use_default_buttons=False,
    )
    await paginator.respond(ctx.interaction, ephemeral=True)


@bot.application_command(
    name="feedback", description="Отправить отзыв/предложение для разработчика"
)
async def feedback(ctx: discord.ApplicationContext):
    await send_analytics(user_id=ctx.user.id, action_name=ctx.command.name)

    if not FEEDBACK_WEBHOOK_URL:
        embed = discord.Embed(
            title="Ошибка обратной связи",
            description="Бот не может отправить ваш отзыв, так как не указана ссылка на обратную связь. Свяжитесь с "
            "администратором",
            color=discord.Color.red(),
        )
        return await ctx.response.send_message(embed=embed, ephemeral=True)

    class Feedback(discord.ui.Modal):
        def __init__(self):
            super().__init__(title="Отправить отзыв/предложение для разработчика")

        theme = discord.ui.InputText(
            label="Тема",
            style=discord.InputTextStyle.short,
            required=True,
            placeholder="Тема отзыва/предложения",
            custom_id="theme",
        )
        feedback = discord.ui.InputText(
            label="Отзыв/предложение",
            style=discord.InputTextStyle.long,
            required=True,
            placeholder="Текст отзыва/предложения",
            custom_id="feedback",
        )

        async def callback(self, interaction: discord.Interaction) -> None:
            feedback_embed = discord.Embed(
                title=self.theme,
                description=self.feedback,
                timestamp=datetime.now(),
            )
            feedback_embed.set_footer(
                text=f"USER_ID={interaction.user.id} GUILD_ID={interaction.guild.id} GUILD_NAME={interaction.guild.name}"
            )
            feedback_embed.set_author(
                name=interaction.user.name, icon_url=interaction.user.avatar.url
            )
            user_embed = discord.Embed(
                title="Отправлено", description="Спасибо за ваше предложение/отзыв!"
            )
            await interaction.response.send_message(embed=user_embed, ephemeral=True)
            async with aiohttp.ClientSession() as session:
                webhook = discord.Webhook.from_url(
                    FEEDBACK_WEBHOOK_URL, session=session
                )
                await webhook.send(embed=feedback_embed)

    modal = Feedback()

    await ctx.response.send_modal(modal)


async def generate_cluster_status_page(cluster: Cluster) -> discord.Embed:
    embed = discord.Embed(
        title=f"{cluster.title} {cluster.flag}",
        description=(
            f"Версия: **{cluster.version}**\n"
            f"Последнее обновление:\n<t:{int(cluster.version_updated_at.timestamp())}>\n"
            f"Общий онлайн: `{cluster.online}`"
        ),
        colour=discord.Colour.blue(),
    )
    for server in cluster.servers:
        if server.online != "Недоступно":
            description = f"{server.status_emoji} {server.status_word}: {server.online}"
        else:
            description = f"{server.status_emoji} {server.status_word}"
        embed.add_field(name=f"Сервер `{server.name}`", value=description, inline=True)
    embed.set_footer(text="При поддержке https://wgstatus.com/")
    return embed


async def generate_main_status_page(wgs: WGStatusAPI) -> discord.Embed:
    clusters = wgs.clusters
    embed = discord.Embed(title="World of Tanks Status", colour=discord.Colour.blue())
    for cluster in clusters:
        embed.add_field(
            name=f"{cluster.title} {cluster.flag}",
            value=(
                f"Версия: **{cluster.version}**\n"
                f"Последнее обновление:\n<t:{int(cluster.version_updated_at.timestamp())}>\n"
                f"Общий онлайн: `{cluster.online}`"
            ),
            inline=True,
        )

    embed.set_footer(text="При поддержке https://wgstatus.com/")
    return embed


async def send_analytics(user_id, action_name):
    if not GOOGLE_GCODE or not GOOGLE_SECRET_KEY:
        return
    """
    Send record to Google Analytics
    """
    params = {
        "client_id": str(user_id),
        "user_id": str(user_id),
        "events": [
            {
                "name": action_name,
                "params": {
                    "engagement_time_msec": "1",
                },
            }
        ],
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"https://www.google-analytics.com/"
            f"mp/collect?measurement_id={GOOGLE_GCODE}&api_secret={GOOGLE_SECRET_KEY}",
            json=params,
        ) as response:
            if 200 <= response.status < 300:  # any codes 2**
                logging.info(f"Analytics sent for user {user_id}: {action_name}")
            else:
                logging.error(
                    f"Failed to send analytics for user {user_id}: {action_name}, HTTP status {response.status}"
                )


class IncorrectResponse(Exception):
    pass


@tasks.loop(minutes=5)
async def push_monitoring_data():
    # top.gg monitoring
    if TOPGG_TOKEN:
        async with aiohttp.ClientSession(
            headers={"Authorization": TOPGG_TOKEN}
        ) as session:
            async with session.post(
                f"https://top.gg/api/bots/{bot.user.id}/stats",
                data={"server_count": len(bot.guilds), "shard_count": 1},
            ) as response:
                if response.status == 200:
                    logging.info(
                        f"Monitoring top.gg push success. {response.status}, {len(bot.guilds)}"
                    )
                else:
                    logging.error(
                        f"Monitoring top.gg push failed. {response.status}, {len(bot.guilds)}"
                    )


bot.run(TOKEN)
