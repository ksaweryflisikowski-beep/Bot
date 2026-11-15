import asyncio
import io
import json
import os
import random
import re
import time
from typing import Literal
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from typing import Optional
import chat_exporter
import discord
import pytz
from discord import app_commands, ui
from discord.types import embed
from discord.ui import Button, View
from discord.ext import commands, tasks

STREFA_CZASOWA = pytz.timezone('Europe/Warsaw')

warns_count = {}
blacklisted_users = {}

# KONFIGURACJA BOTA
TOKEN = "MTU3MTQ1NTQ2MDczNTg0NDM2Mg.GRLkJ5.5MhZzPJXBBKWbgUAyXB8HOLNy48fmtYAPlqNS0" # Token bota
GUILD_ID = 1571456408979771433 # ID serwera
VERIFIED_ROLE_ID = 1571457105167122564 # ID roli zweryfikowany
ROLA_ADMIN_ID = 1571457153959460924 # ID roli administracji
KATEGORIA_PODAN_ID = 1571456410061906012 # ID kategorii do podan
ID_ROLI_REKRUTACYJNEJ = 1571457153959460924 # Rola ktora widzi podania i moze klikac przyciski
ID_ROLI_PO_AKCEPTACJI = 1571457153959460924 # Rola dla ktorej odkrywa się kanał po akceptacji podania
ZMIANA_ROLA_ID = 1571457153959460924 # ID roli zmiany
LOGI_BLACKLISTA_ID = 1571456410061906014 # ID kanalu blacklista
LOGI_TICKET_ID = 123456789012345 # ID kanalu do logow ticketa
ZARZAD_ROLA_ID = 1571457153959460924 # ID roli zarzad
ID_REPUTACJA_ROLE = 1571457153959460924 # ID roli ktora moze zarzadzac reputacja administratorow
LOG_AWANSEDEGRADY_ID = 1571456410061906014 # ID kanalu logow awansow i degradow
LOGI_ADMIN_ID = 1571456410061906014 # ID logow admina
ID_KANALU_URLOPOW = 1571456410061906014 # ID kanalu urlopow
ID_KANALU_SPRAWDZ_URLOP = 1571456410061906014 # ID kanalu sprawdzania urlopow
WELCOME_CHANNEL_ID = 1571456410061906014 # ID kanalu powitan
CHANNEL_ID = 1571456410061906014 # ID kanału gdzie ma wysyłać się embed od zespołu
RECRUITMENT_CHANNEL_ID = 1571456410061906014 # ID kanału rekrutacji

# KONFIGURACJA TICKETÓW
TICKET_BANNER = "https://cdn.discordapp.com/attachments/1530659348139737218/1531265091767636028/777Code-Embedy.png?ex=6a68953f&is=6a6743bf&hm=267db0486f6c4ddf63f1f4c74811a0e27aab95cb21f9e71039f9937c7794f14f&" # URL baneru ticketow
TICKET_LOGO = "https://cdn.discordapp.com/attachments/1530659348139737218/1531265348286943302/777code_-_logo_new.png?ex=6a68957c&is=6a6743fc&hm=9b4feb80af61b16c85f5b74396f3ffc86c28f5103c91e4076b5daaf833b5429d&" # URL loga ticketow

TICKET_CATEGORIES = {
    "pomoc": 1571456410061906012, # ID kategorii pomoc
    "cheater": 1571456410061906012, # ID kategorii cheater
    "blad": 1571456410061906012, # ID kategorii blad
    "backup": 1571456410061906012, # ID kategorii backup
    "unban": 1571456410061906012, # ID kategorii unban
    "zarzad": 1571456410061906012, # ID kategorii zarzad
    "platnosc": 1571456410061906012 # ID kategorii platnosc
}

# ROLE UPRAWNIONE DO AKCEPTOWANIA I ODRZUCANIA URLOPOW:
DOZWOLONE_ROLE_IDS = [
    1571457153959460924,  # ID roli opiekun administracji
    1571457153959460924,  # ID roli headadmin
]

# HIERARCHIA RANG ADMINISTRACYJNYCH OD NAJNIZSZEJ DO NAJWYZSZEJ
HIERARCHIA_RANG_ID = [
    123456789012345, # ID roli testhelper
    123456789012345, # ID roli helper
    123456789012345, # ID roli support
    123456789012345, # ID roli juniormod
    123456789012345, # ID roli mod
    123456789012345, # ID roli junioradmin
    123456789012345, # ID roli administrator
    123456789012345 # ID roli headadmin
]

# ID ról do wyświetlenia na embedzie od zaspołu
ROLE_IDS = [
    1571457153959460924, # CEO
    123456789012345, # Admin
    123456789012345, # JuniorAdmin
    123456789012345,  # Moderator
    123456789012345,  # Support
]

# SLOWNIKI
admin_plusy = {}
admin_minusy = {}
DATA_FILE = "admin_data.json"
DATA_FILE = "message_data.json"
DATA_FILE = "propozycje.json"

intents = discord.Intents.default()
intents.presences = True
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# FUNKCJA DO FORMATOWANIA CZASU
def pobierz_aktualny_czas_pl():
    now = datetime.datetime.now(STREFA_CZASOWA)
    dni_tygodnia = ["poniedziałek", "wtorek", "środa", "czwartek", "piątek", "sobota", "niedziela"]
    miesiace = ["stycznia", "lutego", "marca", "kwietnia", "maja", "czerwca", "lipca", "sierpnia", "września",
                "października", "listopada", "grudnia"]

    data_format = f"{dni_tygodnia[now.weekday()]}, {now.day} {miesiace[now.month - 1]} {now.year}"
    godzina_format = now.strftime('%H:%M')
    return data_format, godzina_format

# --- SYSTEM ZAPISU I ODCZYTU Z PLIKU ---
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Błąd podczas ładowania pliku z danymi: {e}")
            return {}
    return {}

def save_data(data):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Błąd podczas zapisu danych: {e}")

suggestions_data = load_data()

# FUNKCJE ZAPISU I ODCZYTU Z PLIKU JSON
def load_data():
    global admin_plusy, admin_minusy
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                admin_plusy = {int(k): v for k, v in data.get("plusy", {}).items()}
                admin_minusy = {int(k): v for k, v in data.get("minusy", {}).items()}
            print("✅ Pomyślnie wczytano bazę punktów z pliku.")
        except Exception as e:
            print(f"❌ Błąd podczas wczytywania pliku danych: {e}")
            admin_plusy = {}
            admin_minusy = {}
    else:
        admin_plusy = {}
        admin_minusy = {}

def save_data():
    try:
        data = {
            "plusy": {str(k): v for k, v in admin_plusy.items()},
            "minusy": {str(k): v for k, v in admin_minusy.items()}
        }
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"❌ Błąd podczas zapisywania danych do pliku: {e}")

GIVEAWAYS_FILE = "giveaways.json"


def load_giveaways():
    if os.path.exists(GIVEAWAYS_FILE):
        try:
            with open(GIVEAWAYS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Błąd ładowania konkursów: {e}")
            return {}
    return {}


def save_giveaways(data):
    with open(GIVEAWAYS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


active_giveaways = load_giveaways()

emoji_konkursik = "<:konkurs:1531609744152858744>"
emoji_konkurs = "<:dailyikon:1516833104378204160>"
emoji_nie = "<:nie:1516848396684497109>"
emoji_uczestnicy = "<:gracze_online:1516833191120343041>"


class GiveawayJoinView(ui.View):

    def __init__(self, message_id: int):
        super().__init__(timeout=None)
        self.message_id = str(message_id)

        gw = active_giveaways.get(self.message_id, {})
        participants_count = len(gw.get("participants", []))

        self.list_participants_btn.label = (
            f"Zobacz Uczestników {participants_count}os."
        )

        if gw.get("ended"):
            self.join_btn.disabled = True

    @ui.button(
        label="Dołącz do konkursu",
        style=discord.ButtonStyle.primary,
        emoji=emoji_konkursik,
        custom_id="giveaway_join_btn",
    )
    async def join_btn(
        self, interaction: discord.Interaction, button: ui.Button
    ):
        gw = active_giveaways.get(self.message_id)
        if not gw:
            await interaction.response.send_message(
                f"{emoji_nie} Ten konkurs już nie istnieje.", ephemeral=True
            )
            return

        if gw.get("ended"):
            await interaction.response.send_message(
                f"{emoji_nie} Ten konkurs został już zakończony!", ephemeral=True
            )
            return

        user_id = interaction.user.id
        participants = gw.get("participants", [])

        if user_id in participants:
            participants.remove(user_id)
            await interaction.response.send_message(
                f"{emoji_nie} Opuściłeś konkurs.", ephemeral=True
            )
        else:
            participants.append(user_id)
            await interaction.response.send_message(
                f"{emoji_konkurs} Dołączyłeś do konkursu! Powodzenia!",
                ephemeral=True,
            )

        save_giveaways(active_giveaways)

        self.list_participants_btn.label = (
            f"Zobacz Uczestników {len(participants)}os."
        )
        await interaction.message.edit(view=self)

    @ui.button(
        label="Zobacz Uczestników 0os.",
        style=discord.ButtonStyle.secondary,
        emoji=emoji_uczestnicy,
        custom_id="giveaway_list_btn",
    )
    async def list_participants_btn(
        self, interaction: discord.Interaction, button: ui.Button
    ):
        gw = active_giveaways.get(self.message_id)
        if not gw or not gw.get("participants"):
            await interaction.response.send_message(
                "Nikt jeszcze nie dołączył do konkursu.", ephemeral=True
            )
            return

        participants = gw.get("participants", [])

        formatted_list = [
            f"**{idx}.** <@{u_id}>"
            for idx, u_id in enumerate(participants, 1)
        ]

        full_text = "\n".join(formatted_list)
        if len(full_text) > 1900:
            full_text = full_text[:1900] + "\n...i więcej."

        await interaction.response.send_message(full_text, ephemeral=True)


async def finish_giveaway(msg_id: str):
    gw = active_giveaways.get(str(msg_id))
    if not gw or gw.get("ended"):
        return

    gw["ended"] = True
    save_giveaways(active_giveaways)

    channel = bot.get_channel(gw.get("channel_id"))
    if not channel:
        try:
            channel = await bot.fetch_channel(gw.get("channel_id"))
        except:
            return

    try:
        msg = await channel.fetch_message(int(msg_id))
    except:
        return

    participants = gw.get("participants", [])
    winners_count = gw.get("winners_count", 1)
    prize = gw.get("prize", "nagrodę")

    if not participants:
        await channel.send(
            f"{emoji_konkurs} Konkurs na **{prize}** zakończył się, ale nikt nie wziął w nim udziału!"
        )
    else:
        k = min(len(participants), winners_count)
        winner_ids = random.sample(participants, k)
        gw["winners"] = winner_ids
        save_giveaways(active_giveaways)

        winners_mentions = [f"<@{w_id}>" for w_id in winner_ids]
        await channel.send(
            f"{emoji_konkursik} Gratulacje {', '.join(winners_mentions)}! Wygraliście **{prize}**!"
        )

    if msg.embeds:
        embed = msg.embeds[0]
        embed.title = "KONKURS ZAKOŃCZONY"
        await msg.edit(embed=embed, view=GiveawayJoinView(int(msg_id)))
    else:
        await msg.edit(view=GiveawayJoinView(int(msg_id)))

# FUNKCJA POMOCNICZA DO HIERARCHII
def get_rank_level(member):
    for i in range(len(HIERARCHIA_RANG_ID) - 1, -1, -1):
        if member.get_role(HIERARCHIA_RANG_ID[i]):
            return i
    return -1

# WCZYTANIE LICZNIKA GLOBALNEGO
try:
    with open("counter.json", "r") as f:
        counter = json.load(f)
except FileNotFoundError:
    counter = {"count": 0}


class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.presences = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        update_embed_loop.start()
        self.add_view(TicketActionView())
        self.add_view(VerifyView())
        self.add_view(MainTicketView())
        self.add_view(RekrutacjaView())

        for msg_id, gw in list(active_giveaways.items()):
            if not gw.get("ended"):
                self.add_view(GiveawayJoinView(int(msg_id)))

        if not check_giveaways.is_running():
            check_giveaways.start()

        self.tree.add_command(konkurs)
        self.tree.add_command(reroll)

        print("Zarejestrowano trwałe widoki, pętle i komendy!")

        await self.tree.sync()
        print("Pomyślnie zsynchronizowano komendy slash!")

    async def on_ready(self):
        bot.add_view(VerifyView())
        print(f"Zalogowano jako {self.user}!")

@tasks.loop(seconds=10)
async def check_giveaways():
    now_ts = datetime.now(timezone.utc).timestamp()
    for msg_id, gw in list(active_giveaways.items()):
        if not gw.get("ended") and now_ts >= gw.get("end_time", 0):
            await finish_giveaway(str(msg_id))

# WIDOK URLOP

emoji_konkursik = "<:konkurs:1531609744152858744>"
emoji_konkurs = "<:dailyikon:1516833104378204160>"
emoji_nie = "<:nie:1516848396684497109>"
emoji_tak = "<:tak:1516833709796626442>"
emoji_uwaga = "<:uwagaaa:1531609778944479362>"
emoji_log = "<:tablica:1516833692985720842>"
emoji_steve = "<:ikonka_nicku:1516833248246759574>"
emoji_adm = "<:onlineosobtab:1516833406518820975>"
emoji_brak = "<:dupa:1530658424335896738>"
emoji_lista = "<:informacje:1516833263988117587>"
emoji_czas = "<:nick:1516833363699433492>"
emoji_plus = "<:plus:1530687822942699760>"
emoji_minus = "<:minus:1530687824633004042>"
emoji_stat = "<:staty:1530658283176857690>"
emoji_gora = "<:gora:1530658287236808764>"
emoji_dol = "<:dol:1530658293671006228>"
emoji_zegar = "<:zegar:1516833795410755635>"
emoji_cel = "<:675:1516834910277734583>"
emoji_pad = "<:542:1516835059808862239>"
emoji_sklep = "<:342:1516835085192527953>"
emoji_ogloszenie = "<:ogloszeniebossbar:1516833385597636780>"
emoji_klutka = "<:klodka:1516833301518880779>"
emoji_ziemia = "<:planeta:1516833440979353600>"
emoji_dc = "<:dc:1516833122929475685>"
emoji_ranking = "<:ranking:1516833499221594214>"

class UrlopReasonModal(discord.ui.Modal):
    def __init__(self, action_type: str, main_msg_id: int, review_msg_id: int):
        title_str = "Powód odrzucenia wniosku" if action_type == "odrzuc" else "Uzasadnienie decyzji"
        super().__init__(title=title_str)
        self.action_type = action_type
        self.main_msg_id = main_msg_id
        self.review_msg_id = review_msg_id

        self.reason_input = discord.ui.TextInput(
            label="Wpisz uzasadnienie decyzji:",
            style=discord.TextStyle.paragraph,
            placeholder="Wpisz tutaj powód...",
            required=True,
            min_length=2,
            max_length=500
        )
        self.add_item(self.reason_input)

    async def on_submit(self, interaction: discord.Interaction):
        powod_decyzji = self.reason_input.value
        main_channel = interaction.guild.get_channel(ID_KANALU_URLOPOW)

        embed = interaction.message.embeds[0]
        user_mention = embed.fields[0].value
        user_id = int(re.sub(r"[<@!>]", "", user_mention))
        target_member = interaction.guild.get_member(user_id)

        if self.action_type == "odrzuc":
            embed.color = discord.Color.red()
            embed.set_footer(text=f"Odrzucone przez: {interaction.user.display_name}")
            embed.add_field(name="<:informacje:1516833263988117587> Powód odrzucenia", value=powod_decyzji, inline=False)
            pv_title = "<:nie:1516848396684497109> Twój wniosek o urlop został ODRZUCONY"
            pv_color = discord.Color.red()

        view = discord.ui.View.from_message(interaction.message)
        for child in view.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True

        await interaction.response.edit_message(embed=embed, view=view)

        if main_channel:
            try:
                main_msg = await main_channel.fetch_message(self.main_msg_id)
                await main_msg.edit(embed=embed)
            except Exception as e:
                print(f"Błąd edycji: {e}")

        if target_member:
            try:
                embed_pv = discord.Embed(
                    title=pv_title,
                    description=f"Twój wniosek wysłany na kanale {main_channel.mention} został rozpatrzony przez administratora **{interaction.user.mention}**.",
                    color=pv_color,
                    timestamp=discord.utils.utcnow()
                )
                embed_pv.add_field(name="<:informacje:1516833263988117587> Powód:", value=powod_decyzji, inline=False)
                await target_member.send(embed=embed_pv)
            except discord.Forbidden:
                pass


class UrlopButtons(discord.ui.View):

    def __init__(self, main_msg_id: int = None):
        super().__init__(timeout=None)
        self.main_msg_id = main_msg_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        user_roles = [role.id for role in interaction.user.roles]
        if not any(role_id in user_roles for role_id in DOZWOLONE_ROLE_IDS):
            await interaction.response.send_message("Nie masz uprawnień do zarządzania tym urlopem!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Zaakceptuj", emoji=emoji_tak, style=discord.ButtonStyle.success, custom_id="urlop_akcept")
    async def akceptuj(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green()
        embed.set_footer(text=f"Zaakceptowane przez: {interaction.user.display_name}")

        user_mention = embed.fields[0].value
        user_id = int(re.sub(r"[<@!>]", "", user_mention))
        target_member = interaction.guild.get_member(user_id)

        for child in self.children:
            child.disabled = True

        await interaction.response.edit_message(embed=embed, view=self)

        main_channel = interaction.guild.get_channel(ID_KANALU_URLOPOW)
        if main_channel and self.main_msg_id:
            try:
                main_msg = await main_channel.fetch_message(self.main_msg_id)
                await main_msg.edit(embed=embed)
            except Exception as e:
                print(f"Błąd edycji: {e}")

        if target_member:
            try:
                embed_pv = discord.Embed(
                    title=f"{emoji_tak} Twój wniosek o urlop został ZAAKCEPTOWANY!",
                    description=f"Twój wniosek na kanale {main_channel.mention} został pomyślnie zatwierdzony przez administratora **{interaction.user.mention}**.",
                    color=discord.Color.green(),
                    timestamp=discord.utils.utcnow()
                )
                await target_member.send(embed=embed_pv)
            except discord.Forbidden:
                pass

    @discord.ui.button(label="Odrzuć", emoji=emoji_nie, style=discord.ButtonStyle.danger, custom_id="urlop_odrzuc")
    async def odrzuc(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(UrlopReasonModal("odrzuc", self.main_msg_id, interaction.message.id))



def load_message_id():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
            return data.get("message_id")
    return None

def save_message_id(msg_id):
    with open(DATA_FILE, "w") as f:
        json.dump({"message_id": msg_id}, f)

EMOJI_ONLINE = "<a:ONLINE:1530658296648831178>"
EMOJI_OFFLINE = "<a:OFFLINE:1530658295159722044>"


def create_status_embed(guild: discord.Guild):
    embed = discord.Embed(
        title="Zespół 777CODE.PL",
        color=0x414141,
    )

    description_parts = []

    for role_id in ROLE_IDS:
        role = guild.get_role(role_id)
        if not role:
            continue

        description_parts.append(f"<@&{role.id}>")
        members = role.members

        if not members:
            description_parts.append("> Brak użytkowników w tej randze\n")
        else:
            for member in members:
                if member.status != discord.Status.offline:
                    status_str = f"{EMOJI_ONLINE} **Aktywny/a**"
                else:
                    status_str = f"{EMOJI_OFFLINE} **Nieaktywny/a**"

                description_parts.append(f"> {member.mention} {status_str}")

            description_parts.append("")

    current_timestamp = int(datetime.now().timestamp())
    description_parts.append(f"Ostatnia aktualizacja: <t:{current_timestamp}:R>")
    description_parts.append(f"Chcesz dołączyć do nas? Zobacz kanał <#{RECRUITMENT_CHANNEL_ID}>")

    embed.description = "\n".join(description_parts)
    embed.set_thumbnail(url=URL_LOGO)

    if URL_BANER:
        embed.set_image(url=URL_BANER)

    return embed

@tasks.loop(minutes=5)
async def update_embed_loop():
    guild = bot.get_guild(GUILD_ID)
    if not guild:
        return

    channel = guild.get_channel(CHANNEL_ID)
    if not channel:
        return

    embed = create_status_embed(guild)
    msg_id = load_message_id()

    if msg_id:
        try:
            msg = await channel.fetch_message(msg_id)
            await msg.edit(embed=embed)
            return
        except (discord.NotFound, discord.HTTPException):
            pass

    new_msg = await channel.send(embed=embed)
    save_message_id(new_msg.id)

@update_embed_loop.before_loop
async def before_loop():
    await bot.wait_until_ready()

@bot.event
async def on_ready():
    print(f"Bot {bot.user} działa pomyślnie!")
    if not update_embed_loop.is_running():
        update_embed_loop.start()

# ---------------------- ON_READY ----------------------------
async def send_admin_log(interaction, target, action_name, color, field_title, details):
    log_channel = interaction.guild.get_channel(LOG_AWANSEDEGRADY_ID)
    if not log_channel:
        return

    embed = discord.Embed(title=f"{emoji_log} Log: {action_name}", color=color, timestamp=discord.utils.utcnow())
    embed.set_thumbnail(url=target.display_avatar.url)
    embed.add_field(name=f"{emoji_steve} Użytkownik", value=target.mention, inline=True)
    embed.add_field(name=f"{emoji_adm} Moderator", value=interaction.user.mention, inline=True)
    embed.add_field(name=field_title, value=details, inline=False)
    await log_channel.send(embed=embed)


@bot.event
async def on_ready():
    load_data()
    print(f"✅ Zalogowano jako {bot.user.name} ({bot.user.id})")

    try:
        guild = discord.Object(id=GUILD_ID)
        bot.tree.copy_global_to(guild=guild)
        synced = await bot.tree.sync(guild=guild)
        print(f"✅ Zsynchronizowano {len(synced)} komend typu Slash dla serwera {GUILD_ID}")
    except Exception as e:
        print(f"❌ Błąd synchronizacji komend: {e}")


bot = MyBot()

# ------------------------------------------ SYSTEM BLACKLIST -------------------------------------------------
class BlacklistActionView(ui.View):
    def __init__(self, target_id):
        super().__init__(timeout=None)
        self.target_id = target_id

    @ui.button(label="Kliknij, aby usunąć blacklistę.", style=discord.ButtonStyle.danger, emoji=emoji_brak, custom_id="remove_blacklist")
    async def remove_blacklist(self, interaction: discord.Interaction, button: ui.Button):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message(f"{emoji_nie} Nie masz uprawnień!", ephemeral=True)
        try:
            if self.target_id:
                user = await bot.fetch_user(int(self.target_id))
                await interaction.guild.unban(user, reason="Usunięcie z blacklisty")
                await interaction.response.send_message(f"{emoji_tak} Usunięto z blacklisty i odbanowano <@{self.target_id}>.",
                                                        ephemeral=True)
            else:
                await interaction.response.send_message(f"{emoji_tak} Akcja wykonana (tryb serwisowy).", ephemeral=True)

            await interaction.message.edit(view=None)
        except Exception as e:
            await interaction.response.send_message(f"{emoji_nie} Błąd użytkownik nie ma bana: {e}", ephemeral=True)


@bot.tree.command(name="blacklista", description="Dodaje użytkownika na blacklistę", guild=discord.Object(id=GUILD_ID))
@app_commands.default_permissions(administrator=True)
@app_commands.describe(
    uzytkownik="Użytkownik do zablokowania",
    powod="Podaj powód blacklisty"
)
async def blacklista(interaction: discord.Interaction, uzytkownik: discord.Member, powod: str):
    await interaction.response.defer(ephemeral=True)
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message(f"{emoji_nie} Nie masz uprawnień!", ephemeral=True)

    teraz = discord.utils.utcnow()
    timestamp_str = teraz.strftime("%d.%m.%Y %H:%M")

    embed_pv = discord.Embed(
        title=f"{emoji_brak} Zostałeś wpisany na Blacklistę!",
        description="Zostałeś wpisany na blackliste serwera **777CODE.PL**.",
        color=0x414141
    )
    embed_pv.add_field(name=f"{emoji_adm} Administrator:", value=interaction.user.mention, inline=False)
    embed_pv.add_field(name=f"{emoji_lista} Powód:", value=f"{powod}", inline=False)

    embed_pv.add_field(name="\u200b", value=f"{emoji_uwaga} Jeśli uważasz, że to pomyłka, skontaktuj się z administracją.", inline=False)

    embed_pv.set_thumbnail(url=URL_LOGO)
    embed_pv.set_image(url=URL_BANER)

    try:
        await uzytkownik.send(embed=embed_pv)
    except:
        pass

    try:
        await interaction.guild.ban(uzytkownik, reason=f"Blacklista przez {interaction.user}: {powod}")
    except Exception as e:
        return await interaction.followup.send(f"{emoji_nie} Wysyłanie pv się udało, ale wystąpił błąd przy nadawaniu bana: {e}", ephemeral=True)

    embed_log = discord.Embed(title="777CODE.PL × BLACKLISTA", color=0x414141)
    embed_log.set_thumbnail(url=uzytkownik.display_avatar.url)

    embed_log.add_field(name=f"{emoji_steve} Użytkownik", value=f"{uzytkownik.mention}", inline=False)
    embed_log.add_field(name=f"{emoji_log} ID", value=f"`{uzytkownik.id}`", inline=False)
    embed_log.add_field(name=f"{emoji_lista} Powód", value=f"{powod}", inline=False)

    embed_log.set_thumbnail(url=URL_LOGO)
    embed_log.set_image(url=URL_BANER)

    log_channel = bot.get_channel(LOGI_BLACKLISTA_ID)
    if log_channel:
        await log_channel.send(embed=embed_log, view=BlacklistActionView(uzytkownik.id))

    status_msg = f"{emoji_tak} Dodano {uzytkownik.mention} na blacklistę i zbanowano."

    await interaction.followup.send(status_msg, ephemeral=True)


# ------------------------------------ SEKCJA REKRUTACJI -------------------------------------

BLACKLIST_FILE = "blacklista.json"
CONFIG_FILE = "konfiguracja.json"


def load_blacklist():
    if os.path.exists(BLACKLIST_FILE):
        try:
            with open(BLACKLIST_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {int(k): v for k, v in data.items()}
        except:
            return {}
    return {}


def save_blacklist():
    with open(BLACKLIST_FILE, "w", encoding="utf-8") as f:
        json.dump(blacklisted_users, f, indent=4, ensure_ascii=False)


blacklisted_users = load_blacklist()


def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {"rekrutacja": "ON", "wymagania": "ON"}
    return {"rekrutacja": "ON", "wymagania": "ON"}


def save_config(config_data):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=4, ensure_ascii=False)


bot_config = load_config()


class TestHelperModal(ui.Modal, title="Formularz rekrutacyjny – TestHelper"):
    p1 = ui.TextInput(label="1. Jak masz na imię?", required=True)
    p2 = ui.TextInput(label="2. Nick z minecraft:", required=True)
    p3 = ui.TextInput(label="3. Ile masz lat?", required=True)
    p4 = ui.TextInput(label="4. Wykrywanie cheatów (1-10)", min_length=1, max_length=2, required=True)
    p5 = ui.TextInput(label="5. Jak oceniasz swoją ortografię (1-10)", min_length=1, max_length=2, required=True)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild

        # --- WERYFIKACJA WYMAGAŃ WIEKOWYCH ---
        if bot_config.get("wymagania", "ON") == "ON":
            wiek_match = re.search(r'\d+', self.p3.value)
            if wiek_match:
                wiek = int(wiek_match.group())
                if wiek < 14:
                    embed_odrzucone = discord.Embed(
                        title=f"{emoji_nie} PODANIE ODRZUCONE",
                        color=discord.Color.red(),
                        description="Niestety Twoje podanie zostało automatycznie odrzucone, ponieważ nie spełniasz wymagań wiekowych."
                    )
                    embed_odrzucone.set_footer(text="777CODE.PL - SYSTEM REKRUTACJI")
                    return await interaction.followup.send(embed=embed_odrzucone, ephemeral=True)
            else:
                return await interaction.followup.send(
                    f"{emoji_nie} Podano nieprawidłowy wiek w formularzu! Wpisz poprawną liczbę.", ephemeral=True)
        # --------------------------------------

        category = guild.get_channel(KATEGORIA_PODAN_ID)
        if not category or not isinstance(category, discord.CategoryChannel):
            return await interaction.followup.send(f"{emoji_nie} Błąd systemu: Nie znaleziono poprawnej kategorii dla podań.",
                                                   ephemeral=True)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
            guild.get_role(ID_ROLI_REKRUTACYJNEJ): discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        discord_nick = interaction.user.name.lower()
        channel_name = f"podanie-{discord_nick}"
        ticket_channel = await guild.create_text_channel(name=channel_name, category=category, overwrites=overwrites)

        embed = discord.Embed(title=f"{emoji_log} TWOJE PODANIE", color=0xFFA500)
        embed.description = (
            f"> • **Imię:** {self.p1.value}\n"
            f"> • **Nick minecraft:** {self.p2.value}\n"
            f"> • **Ile masz lat:** {self.p3.value}\n"
            f"> • **Wykrywanie cheatów:** {self.p4.value}\n"
            f"> • **Ortografia:** {self.p5.value}\n\n"
            f"» **Wypełnij poniższe pytania:**\n"
            f"> 1. Czy posiadasz Minecraft Premium?\n"
            f"> 2. Gracz oskarża Cię o niesprawiedliwą kare Jak na to odpowiesz?\n"
            f"> 3. Jakie cechy i umiejętności sprawiają, że nadajesz się na stanowisko administratora? Jakie doświadczenia mogą Ci w tym pomóc?\n"
            f"> 4. Czy przeszedłeś już mutację?\n"
            f"> 5. Czy jesteś lub byłeś administratorem na innym serwerze? Jeśli tak - na jakim?\n"
            f"> 6. Co zrobisz gdy gracz poprosi Cię o backupa?\n"
            f"> 7. Przedstaw proces sprawdzania gracza, w sposób taki, jaki ty byś to zrobił krok po kroku\n"
            f"> 8. Ile czasu tygodniowo będziesz mógł/mogła poświęcić na serwer Minecraft i Discord?\n"

        )
        embed.set_footer(text=f"777CODE.PL - SYSTEM REKRUTACJI")

        await ticket_channel.send(content=f"{interaction.user.mention}", embed=embed,
                                  view=ZarzadzaniePodaniemView(interaction.user.id, self.p2.value))
        await interaction.followup.send(
            f"{emoji_tak} Twoje podanie zostało utworzone! Przejdź do kanału: {ticket_channel.mention}", ephemeral=True)


class RodoWeryfikacjaView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="Akceptuj", style=discord.ButtonStyle.success, emoji=f"{emoji_tak}", custom_id="rodo_accept")
    async def accept_rodo(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(TestHelperModal())

    @ui.button(label="Odrzuć", style=discord.ButtonStyle.danger, emoji=f"{emoji_nie}", custom_id="rodo_deny")
    async def deny_rodo(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message(
            f"{emoji_brak} Nie możesz złożyć podania bez uprzedniej akceptacji zgody na przetwarzanie danych osobowych RODO.",
            ephemeral=True)


class ZarzadzaniePodaniemView(ui.View):
    def __init__(self, applicant_id: int, applicant_nick: str):
        super().__init__(timeout=None)
        self.applicant_id = applicant_id
        self.applicant_nick = applicant_nick

    async def check_permissions(self, interaction: discord.Interaction) -> bool:
        has_recruitment_role = discord.utils.get(interaction.user.roles, id=ID_ROLI_REKRUTACYJNEJ)
        has_accepted_role = discord.utils.get(interaction.user.roles, id=ID_ROLI_PO_AKCEPTACJI)

        if not has_recruitment_role and not has_accepted_role and not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(f"{emoji_nie} Nie możesz klikac tych przyciskow!", ephemeral=True)
            return False
        return True

    @ui.button(label="Akceptuj", style=discord.ButtonStyle.success, emoji=f"{emoji_tak}", custom_id="btn_accept_app")
    async def accept(self, interaction: discord.Interaction, button: ui.Button):
        if not await self.check_permissions(interaction): return

        admin_nick = interaction.user.name.lower()
        await interaction.channel.edit(name=f"zaakceptowane-przez-{admin_nick}")

        role_to_reveal = interaction.guild.get_role(ID_ROLI_PO_AKCEPTACJI)
        if role_to_reveal:
            await interaction.channel.set_permissions(role_to_reveal, read_messages=True, send_messages=True)

        emb = discord.Embed(title=f"{emoji_tak} PODANIE PRZYJĘTE", color=0x00FF83)
        emb.description = (
            "Twoje podanie zostało przyjęte.\n"
            "Czekaj na odpowiedź osoby z rangą oznaczoną powyżej."
        )
        emb.set_footer(text="777CODE.PL - SYSTEM REKRUTACJI")

        role_mention = f"<@&{ID_ROLI_PO_AKCEPTACJI}>" if role_to_reveal else "@Rekruter"
        ping_content = f"<@{self.applicant_id}> {role_mention}"

        await interaction.channel.send(content=ping_content, embed=emb)

        for child in self.children:
            child.disabled = False
        await interaction.response.edit_message(view=self)

    @ui.button(label="Odrzuć", style=discord.ButtonStyle.danger, emoji=f"{emoji_nie}", custom_id="btn_reject_app")
    async def reject(self, interaction: discord.Interaction, button: ui.Button):
        if not await self.check_permissions(interaction): return

        admin_nick = interaction.user.name.lower()
        await interaction.channel.edit(name=f"odrzucone-przez-{admin_nick}")

        emb = discord.Embed(title=f"{emoji_nie} PODANIE ODRZUCONE", color=discord.Color.red())
        emb.description = (
            "Niestety Twoje podanie zostało odrzucone przez administratora.\n"
            "Spróbuj swoich sił nastepnym razem."
        )
        emb.set_footer(text="777CODE.PL - SYSTEM REKRUTACJI")

        await interaction.channel.send(content=f"<@{self.applicant_id}>", embed=emb)

        for child in self.children:
            child.disabled = False
        await interaction.response.edit_message(view=self)

    @ui.button(label="Zamknij", style=discord.ButtonStyle.secondary, emoji=f"{emoji_brak}", custom_id="btn_close_app")
    async def close(self, interaction: discord.Interaction, button: ui.Button):
        if not await self.check_permissions(interaction): return

        await interaction.response.send_message(f"{emoji_czas} Ten kanał zostanie usunięty za 10 sekund...")
        await asyncio.sleep(10)
        await interaction.channel.delete()


class RekrutacjaView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        if bot_config.get("rekrutacja", "ON") == "OFF":
            self.testhelper_button.disabled = True

    @ui.button(
        label="\u2800" * 13 + "Kliknij, aby napisać podanie" + "\u2800" * 13,
        style=discord.ButtonStyle.secondary,
        custom_id="rec_th_v2"
    )
    async def testhelper_button(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id in blacklisted_users:
            return await interaction.response.send_message(f"{emoji_brak} Jesteś na czarnej liście! Nie możesz złożyć podania.",
                                                           ephemeral=True)

        rodo_embed = discord.Embed(title="`Zgoda na przetwarzanie danych osobowych`", color=discord.Color.blue())
        rodo_embed.description = (
            "Wyrażam zgodę na przetwarzanie moich danych osobowych dla potrzeb niezbędnych "
            "do realizacji procesu rekrutacji (zgodnie z ustawą z dnia 10 maja 2018 roku o ochronie "
            "danych osobowych oraz zgodnie z Rozporządzeniem Parlamentu Europejskiego i Rady (UE) "
            "2016/679 z dnia 27 kwietnia 2016 r.)."
        )
        rodo_embed.set_footer(text=f"777CODE.PL • Dziś o {discord.utils.utcnow().strftime('%H:%M')}")

        await interaction.response.send_message(embed=rodo_embed, view=RodoWeryfikacjaView(), ephemeral=True)

# --- KOMENDA /ZARZADZAJ-ADMINISTRACJA

async def send_plus_log(interaction, target, plusy_count, powod, awans_info=""):
    log_channel = interaction.guild.get_channel(LOG_AWANSEDEGRADY_ID)
    if not log_channel:
        return

    embed = discord.Embed(
        title=f"{emoji_plus} PLUS",
        color=discord.Color.green(),
        timestamp=discord.utils.utcnow()
    )
    embed.set_thumbnail(url=target.display_avatar.url)
    embed.add_field(name=f"{emoji_steve} Użytkownik", value=target.mention, inline=True)
    embed.add_field(name=f"{emoji_steve} Moderator", value=interaction.user.mention, inline=True)
    embed.add_field(name=f"{emoji_stat} Stan plusów", value=f"**{plusy_count}/5**", inline=True)
    embed.add_field(name=f"{emoji_lista} Powód", value=powod, inline=False)
    embed.set_image(url=URL_BANER)

    if awans_info:
        embed.add_field(name="System Awansów", value=awans_info, inline=False)

    await log_channel.send(embed=embed)


async def send_minus_log(interaction, target, minusy_count, powod, degrad_info=""):
    log_channel = interaction.guild.get_channel(LOG_AWANSEDEGRADY_ID)
    if not log_channel:
        return

    embed = discord.Embed(
        title=f"{emoji_minus} MINUS",
        color=discord.Color.red(),
        timestamp=discord.utils.utcnow()
    )
    embed.set_thumbnail(url=target.display_avatar.url)
    embed.add_field(name=f"{emoji_steve} Użytkownik", value=target.mention, inline=True)
    embed.add_field(name=f"{emoji_steve} Moderator", value=interaction.user.mention, inline=True)
    embed.add_field(name=f"{emoji_stat} Stan minusów", value=f"**{minusy_count}/3**", inline=True)
    embed.add_field(name=f"{emoji_lista} Powód", value=powod, inline=False)
    embed.set_image(url=URL_BANER)

    if degrad_info:
        embed.add_field(name="System Degradacji", value=degrad_info, inline=False)

    await log_channel.send(embed=embed)

@bot.tree.command(
    name="zarzadzaj-administracja",
    description="Główna komenda do zarządzania strukturą i punktami administracji",
    guild=discord.Object(id=GUILD_ID)
)
@app_commands.default_permissions(administrator=True)
@app_commands.describe(
    akcja="Wybierz operację (awans, degrad, plus, minus, status-pm, reset-punkty, rezygnacja, lota)",
    uzytkownik="Członek administracji, którego dotyczy akcja",
    powod="Powód (wymagany dla: awans, degrad, plus, minus, rezygnacja, lota)",
    z_roli="Ranga odbierana (wymagana tylko dla: awans, degrad)",
    na_role="Ranga nadawana (wymagana tylko dla: awans, degrad)"
)
async def zarzadzaj_administracja(
        interaction: discord.Interaction,
        akcja: Literal["awans", "degrad", "plus", "minus", "status-pm", "reset-punkty", "rezygnacja", "lota"],
        uzytkownik: discord.Member,
        powod: str = None,
        z_roli: discord.Role = None,
        na_role: discord.Role = None
):
    await interaction.response.defer(ephemeral=True)

    if not any(role.id == 1530659708078264452 for role in interaction.user.roles):
        return await interaction.followup.send(f"{emoji_brak} Nie masz uprawnień do używania tej komendy.")

    uid = uzytkownik.id

    # --- AKCJA: STATUS-PM ---
    if akcja == "status-pm":
        plusy = admin_plusy.get(uid, 0)
        minusy = admin_minusy.get(uid, 0)

        aktualna_ranga = "Brak"
        for role_id in reversed(HIERARCHIA_RANG_ID):
            if uzytkownik.get_role(role_id):
                role = interaction.guild.get_role(role_id)
                if role:
                    aktualna_ranga = role.name
                    break

        embed = discord.Embed(title=f"{emoji_stat} Status PM: {uzytkownik.display_name}", color=discord.Color.green(),
                              timestamp=interaction.created_at)
        embed.set_thumbnail(url=uzytkownik.display_avatar.url)

        plusy_bar = "🟢" * plusy + "⚪" * (5 - plusy)
        minusy_bar = "🔴" * minusy + "⚪" * (3 - minusy)

        embed.add_field(name=f"{emoji_log} Ranga w hierarchii", value=f"**{aktualna_ranga}**", inline=False)
        embed.add_field(name=f"{emoji_plus} Plusy", value=f"{plusy_bar} ({plusy}/5)", inline=True)
        embed.add_field(name=f"{emoji_minus} Minusy", value=f"{minusy_bar} ({minusy}/3)", inline=True)

        return await interaction.followup.send(embed=embed)

    # --- AKCJA: RESET-PUNKTY ---
    if akcja == "reset-punkty":
        admin_plusy[uid] = 0
        admin_minusy[uid] = 0
        save_data()

        await send_admin_log(interaction, uzytkownik, "RESET PUNKTÓW", discord.Color.green(), "Akcja",
                             "Wyzerowano wszystkie plusy i minusy")
        return await interaction.followup.send(f"{emoji_tak} Wyzerowano punkty dla {uzytkownik.mention}.")

    if not powod:
        return await interaction.followup.send(f"{emoji_nie} Dla tej akcji musisz podać powód!")

    # --- AKCJA: PLUS ---
    if akcja == "plus":
        if get_rank_level(uzytkownik) >= get_rank_level(
                interaction.user) and not interaction.user.guild_permissions.administrator:
            return await interaction.followup.send(f"{emoji_nie} Nie możesz dawać plusów osobie o równej lub wyższej randze!")

        admin_plusy[uid] = admin_plusy.get(uid, 0) + 1
        aktualne_plusy = admin_plusy[uid]
        awans_info = ""

        if aktualne_plusy >= 5:
            found_idx = -1
            for i, role_id in enumerate(HIERARCHIA_RANG_ID):
                if uzytkownik.get_role(role_id):
                    found_idx = i
                    break

            if found_idx != -1 and found_idx < len(HIERARCHIA_RANG_ID) - 1:
                stara_rola = interaction.guild.get_role(HIERARCHIA_RANG_ID[found_idx])
                nowa_rola = interaction.guild.get_role(HIERARCHIA_RANG_ID[found_idx + 1])
                if nowa_rola:
                    try:
                        await uzytkownik.add_roles(nowa_rola)
                        if stara_rola:
                            await uzytkownik.remove_roles(stara_rola)

                        admin_plusy[uid] = 0
                        admin_minusy[uid] = 0
                        awans_info = f"{emoji_gora} **Automatyczny Awans na {nowa_rola.name}!** (Zresetowano punkty)"
                    except discord.Forbidden:
                        awans_info = f"{emoji_nie} **Bot nie mógł nadać awansu! Za niska pozycja ról bota.**"

        save_data()
        await send_plus_log(interaction, uzytkownik, admin_plusy.get(uid, 0), powod, awans_info)

        res_embed = discord.Embed(
            description=f"{emoji_tak} Dodano plusa dla {uzytkownik.mention} (Stan: **{admin_plusy.get(uid, 0)}/5**)\n{awans_info}",
            color=discord.Color.green()
        )
        return await interaction.followup.send(embed=res_embed)

    # --- AKCJA: MINUS ---
    if akcja == "minus":
        if get_rank_level(uzytkownik) >= get_rank_level(
                interaction.user) and not interaction.user.guild_permissions.administrator:
            return await interaction.followup.send(f"{emoji_nie} Nie możesz dawać minusów osobie o równej lub wyższej randze!")

        admin_minusy[uid] = admin_minusy.get(uid, 0) + 1
        aktualne_minusy = admin_minusy[uid]
        degrad_info = ""

        if aktualne_minusy >= 3:
            found_idx = -1
            for i, role_id in enumerate(HIERARCHIA_RANG_ID):
                if uzytkownik.get_role(role_id):
                    found_idx = i
                    break

            if found_idx > 0:
                stara_rola = interaction.guild.get_role(HIERARCHIA_RANG_ID[found_idx])
                nizsza_rola = interaction.guild.get_role(HIERARCHIA_RANG_ID[found_idx - 1])
                if nizsza_rola:
                    try:
                        await uzytkownik.add_roles(nizsza_rola)
                        if stara_rola:
                            await uzytkownik.remove_roles(stara_rola)

                        admin_plusy[uid] = 0
                        admin_minusy[uid] = 0
                        degrad_info = f"{emoji_dol} **Automatyczna Degradacja na {nizsza_rola.name}!** (Zresetowano punkty)"
                    except discord.Forbidden:
                        degrad_info = f"{emoji_nie} **Bot nie mógł zdegradować! Za niska pozycja ról bota.**"

        save_data()
        await send_minus_log(interaction, uzytkownik, admin_minusy.get(uid, 0), powod, degrad_info)

        res_embed = discord.Embed(
            description=f"{emoji_tak} Dodano minusa dla {uzytkownik.mention} (Stan: **{admin_minusy.get(uid, 0)}/3**)\n{degrad_info}",
            color=discord.Color.red()
        )
        return await interaction.followup.send(embed=res_embed)

    # --- AKCJA: REZYGNACJA / LOTA ---
    if akcja in ["rezygnacja", "lota"]:
        if get_rank_level(uzytkownik) >= get_rank_level(
                interaction.user) and not interaction.user.guild_permissions.administrator:
            return await interaction.followup.send(
                f"{emoji_nie} Nie możesz wykonać tej akcji wobec osoby o równej lub wyższej randze!")

        admin_plusy[uid] = 0
        admin_minusy[uid] = 0
        save_data()

        try:
            role_do_usuniecia = []
            for r_id in HIERARCHIA_RANG_ID:
                role_obj = uzytkownik.get_role(r_id)
                if role_obj:
                    role_do_usuniecia.append(role_obj)

            if role_do_usuniecia:
                await uzytkownik.remove_roles(*role_do_usuniecia)

            teraz = discord.utils.utcnow()
            tytul = f"{emoji_dol} REZYGNACJA" if akcja == "rezygnacja" else f"{emoji_brak} LOTA"
            kolor = discord.Color.greyple() if akcja == "rezygnacja" else discord.Color.dark_red()

            usuniete_wzmianki = ", ".join(
                [r.mention for r in role_do_usuniecia]) if role_do_usuniecia else "Brak ról z hierarchii"

            embed = discord.Embed(title=tytul, color=kolor, timestamp=teraz)
            embed.set_thumbnail(url=uzytkownik.display_avatar.url)
            embed.add_field(name=f"{emoji_steve} **Osoba**", value=uzytkownik.mention, inline=False)
            embed.add_field(name=f"{emoji_dol} **Odebrane role**", value=usuniete_wzmianki, inline=False)
            embed.add_field(name=f"{emoji_lista} **Powód**", value=powod, inline=False)
            embed.add_field(name=f"{emoji_adm} **Moderator**", value=interaction.user.mention, inline=False)
            embed.set_image(url=URL_BANER)

            log_channel = interaction.guild.get_channel(LOG_AWANSEDEGRADY_ID)
            if log_channel:
                await log_channel.send(embed=embed)

            status_txt = "rezygnację" if akcja == "rezygnacja" else "wydalenie (lotę)"
            return await interaction.followup.send(
                f"{emoji_tak} Pomyślnie przetworzono {status_txt} użytkownika {uzytkownik.display_name}.")
        except discord.Forbidden:
            return await interaction.followup.send(f"{emoji_nie} Bot nie ma uprawnień do edycji ról tego użytkownika.")

    if not z_roli or not na_role:
        return await interaction.followup.send(f"{emoji_brak} Musisz podać parametry `z_roli` oraz `na_role` dla tej akcji!")

    # --- AKCJA: AWANS ---
    if akcja == "awans":
        lvl_wykonawca = get_rank_level(interaction.user)
        lvl_cel = get_rank_level(uzytkownik)

        if not interaction.user.guild_permissions.administrator:
            if lvl_cel >= lvl_wykonawca:
                return await interaction.followup.send(f"{emoji_nie} Nie możesz awansować osoby o równej lub wyższej randze!")

            try:
                lvl_nowej_rangi = HIERARCHIA_RANG_ID.index(na_role.id)
                if lvl_nowej_rangi > lvl_wykonawca:
                    return await interaction.followup.send(f"{emoji_nie} Nie możesz nadać komuś rangi wyższej niż Twoja własna!")
            except ValueError:
                pass

        admin_plusy[uid] = 0
        admin_minusy[uid] = 0
        save_data()

        try:
            await uzytkownik.remove_roles(z_roli)
            await uzytkownik.add_roles(na_role)

            teraz = discord.utils.utcnow()
            embed = discord.Embed(title=f"{emoji_gora} AWANS", color=discord.Color.green(), timestamp=teraz)
            embed.set_thumbnail(url=uzytkownik.display_avatar.url)
            embed.add_field(name=f"{emoji_steve} **Osoba**", value=uzytkownik.mention, inline=False)
            embed.add_field(name=f"{emoji_dol} **Z roli**", value=z_roli.mention, inline=True)
            embed.add_field(name=f"{emoji_gora} **Na role**", value=na_role.mention, inline=True)
            embed.add_field(name=f"{emoji_lista} **Powód**", value=powod, inline=False)
            embed.add_field(name=f"{emoji_adm} **Moderator**", value=interaction.user.mention, inline=False)
            embed.set_image(url=URL_BANER)

            log_channel = interaction.guild.get_channel(LOG_AWANSEDEGRADY_ID)
            if log_channel:
                await log_channel.send(embed=embed)

            return await interaction.followup.send(f"{emoji_tak} Pomyślnie nadano awans użytkownikowi {uzytkownik.display_name}.")

        except discord.Forbidden:
            return await interaction.followup.send(f"{emoji_brak} Bot nie ma uprawnień do zarządzania tymi rolami.")

    # --- AKCJA: DEGRAD ---
    if akcja == "degrad":
        if get_rank_level(uzytkownik) >= get_rank_level(
                interaction.user) and not interaction.user.guild_permissions.administrator:
            return await interaction.followup.send(f"{emoji_nie} Nie możesz degradować osoby o równej lub wyższej randze!")

        admin_plusy[uid] = 0
        admin_minusy[uid] = 0
        save_data()

        try:
            await uzytkownik.remove_roles(z_roli)
            await uzytkownik.add_roles(na_role)

            teraz = discord.utils.utcnow()
            embed = discord.Embed(title=f"{emoji_dol} DEGRAD", color=discord.Color.red(), timestamp=teraz)
            embed.set_thumbnail(url=uzytkownik.display_avatar.url)
            embed.add_field(name=f"{emoji_steve} **Osoba**", value=uzytkownik.mention, inline=False)
            embed.add_field(name=f"{emoji_dol} **Z roli**", value=z_roli.mention, inline=True)
            embed.add_field(name=f"{emoji_gora} **Na role**", value=na_role.mention, inline=True)
            embed.add_field(name=f"{emoji_lista} **Powód**", value=powod, inline=False)
            embed.add_field(name=f"{emoji_adm} **Moderator**", value=interaction.user.mention, inline=False)
            embed.set_image(url=URL_BANER)

            log_channel = interaction.guild.get_channel(LOG_AWANSEDEGRADY_ID)
            if log_channel:
                await log_channel.send(embed=embed)

            return await interaction.followup.send(f"{emoji_tak} Pomyślnie zdegradowano użytkownika {uzytkownik.display_name}.")
        except discord.Forbidden:
            return await interaction.followup.send(f"{emoji_brak} Bot nie ma uprawnień do zmiany ról.")


def parse_duration(duration: str):
    time_dict = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    match = re.match(r"(\d+)([smhd])", duration.lower())
    if match:
        amount, unit = match.groups()
        return int(amount) * time_dict[unit]
    return None

# -----------------------------------------------------------KOMENDY: /rekrutacja ORAZ /wymagania -----------------------------------------------------------

@bot.tree.command(name="rekrutacja", description="Włącza lub wyłącza możliwość klikania w przycisk rekrutacji",
                  guild=discord.Object(id=GUILD_ID))
@app_commands.choices(opcja=[
    app_commands.Choice(name="ON", value="ON"),
    app_commands.Choice(name="OFF", value="OFF")
])
@app_commands.default_permissions(administrator=True)
async def zmiana_rekrutacji(interaction: discord.Interaction, opcja: app_commands.Choice[str]):
    await interaction.response.defer(ephemeral=True)

    bot_config["rekrutacja"] = opcja.value
    save_config(bot_config)

    nowy_view = RekrutacjaView()

    channel_id = bot_config.get("panel_channel_id")
    msg_id = bot_config.get("panel_message_id")

    edycja_sukces = False
    if channel_id and msg_id:
        try:
            kanal = interaction.guild.get_channel(channel_id)
            if kanal:
                wiadomosc = await kanal.fetch_message(msg_id)
                if wiadomosc:
                    await wiadomosc.edit(view=nowy_view)
                    edycja_sukces = True
        except Exception:
            pass

    status_txt = f"{emoji_tak} WŁĄCZONA" if opcja.value == "ON" else f"{emoji_nie} WYŁĄCZONA"

    if edycja_sukces:
        await interaction.followup.send(
            f"{emoji_uwaga} Status rekrutacji został zmieniony na: **{status_txt}**. Przycisk na panelu został pomyślnie zaktualizowany!",
            ephemeral=True)
    else:
        await interaction.followup.send(
            f"️{emoji_uwaga} Status rekrutacji został zmieniony na: **{status_txt}**. Nie odnaleziono aktywnego panelu do edycji, użyj `/rekrutacja-panel` aby wysłać nowy",
            ephemeral=True)


@bot.tree.command(name="wymagania", description="Wysyła embed informujący o statusie wymagań rekrutacyjnych",
                  guild=discord.Object(id=GUILD_ID))
@app_commands.choices(opcja=[
    app_commands.Choice(name="ON", value="ON"),
    app_commands.Choice(name="OFF", value="OFF")
])
@app_commands.default_permissions(administrator=True)
async def wyslij_wymagania(interaction: discord.Interaction, opcja: app_commands.Choice[str]):
    bot_config["wymagania"] = opcja.value
    save_config(bot_config)

    current_time = discord.utils.utcnow().strftime("%d.%m.%Y %H:%M")

    if opcja.value == "ON":
        embed = discord.Embed(
            title=f"{emoji_tak} Wymagania rekrutacyjne WŁĄCZONE",
            description="Wymagania wiekowe i rekrutacyjne są teraz **włączone**.\nAplikanci muszą mieć min. **14 lat** i spełniać wszystkie wymagania rekrutacyjne.",
            color=discord.Color.green()
        )
    else:
        embed = discord.Embed(
            title=f"{emoji_nie} Wymagania rekrutacyjne WYŁĄCZONE",
            description="Wymagania wiekowe i rekrutacyjne są teraz **nieaktywne**.\nAplikanci nie muszą spełniać wymagań rekrutacyjnych.",
            color=discord.Color.red()
        )

    embed.set_footer(text=f"Zmienił: {interaction.user.name} • {current_time}")
    await interaction.response.send_message(embed=embed)


# ------------------------------------------------------------ KLASY TICKETÓW ----------------------------------------------------------------------------

class CreateTicketModal(discord.ui.Modal):
    def __init__(self, category_name, category_id):
        super().__init__(title="Informacje dot. ticketa.")
        self.category_name = category_name
        self.category_id = category_id

        self.nick = discord.ui.TextInput(label="PODAJ SWÓJ NICK", placeholder="Twój nick z gry...", required=True)
        self.add_item(self.nick)

        if category_name in ["cheater", "backup", "unban", "blad", "platnosc"]:
            self.tryb = discord.ui.TextInput(label="NA JAKIM TRYBIE", placeholder="np. Anarchia - FFA, BoxPvP...",
                                             required=True)
            self.add_item(self.tryb)

        if category_name == "unban":
            self.admin_ban = discord.ui.TextInput(label="KTO NADAL CI BANA", placeholder="Nick administratora...",
                                                  required=True)
            self.add_item(self.admin_ban)

        if category_name == "platnosc":
            self.kwota = discord.ui.TextInput(label="ILE PŁACISZ", placeholder="np. 20 PLN PSC / Przelew...",
                                              required=True)
            self.add_item(self.kwota)

        if category_name in ["cheater", "backup"]:
            self.dowod = discord.ui.TextInput(label="LINK DO DOWODU", placeholder="imgur.com / youtube.com...",
                                              required=True)
            self.add_item(self.dowod)

        opis_label = "OPISZ SWOJĄ SPRAWĘ"
        if category_name == "blad": opis_label = "OPISZ BŁĄD"

        self.opis = discord.ui.TextInput(
            label=opis_label,
            placeholder="Opisz tutaj wszystko dokładnie...",
            style=discord.TextStyle.paragraph,
            required=True
        )
        self.add_item(self.opis)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        category = guild.get_channel(self.category_id)

        role_admin = guild.get_role(ROLA_ADMIN_ID)
        role_zarzad = guild.get_role(ZARZAD_ROLA_ID)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True,
                                                          read_message_history=True)
        }

        if self.category_name == "zarzad":
            if role_zarzad:
                overwrites[role_zarzad] = discord.PermissionOverwrite(view_channel=True, send_messages=True,
                                                                      read_message_history=True)
        elif self.category_name != "platnosc":
            if role_admin:
                overwrites[role_admin] = discord.PermissionOverwrite(view_channel=True, send_messages=True,
                                                                     read_message_history=True)

        ticket_channel = await guild.create_text_channel(
            name=f"{self.category_name}-{interaction.user.name}",
            category=category,
            topic=str(interaction.user.id),
            overwrites=overwrites
        )

        desc = f"{emoji_lista}**Witaj na swoim zgłoszeniu.** Czekaj na administratora, który zdoła ci pomóc\n"
        desc += f"{emoji_steve}Ticket został utworzony przez: {interaction.user.mention}\n\n"

        desc += f"**Nick:**\n`{self.nick.value}`\n"

        if hasattr(self, 'tryb'):
            desc += f"**Tryb:**\n`{self.tryb.value}`\n"

        if hasattr(self, 'admin_ban'):
            desc += f"**Kto nadał bana:**\n`{self.admin_ban.value}`\n"

        if hasattr(self, 'kwota'):
            desc += f"**Ile płaci:**\n`{self.kwota.value}`\n"

        if hasattr(self, 'dowod'):
            desc += f"**Link do dowodu:**\n`{self.dowod.value}`\n"

        desc += f"**Opis:**\n`{self.opis.value}`\n"
        desc += f"**Kategoria:** {self.category_name.replace('blad', 'Błąd').capitalize()}\n\n"
        desc += (
            f"{emoji_zegar}**Cierpliwość:** Prosimy cierpliwie poczekać na administratora! Nie tylko ty czekasz na pomoc.\n "
            f"{emoji_uwaga}Maksymalny czas oczekiwania na sprawdzenie zgłoszenia przez administracje to **24h!**\n"
            f"{emoji_brak}**Zarząd:** Nie oznaczaj zarządu. Jedyne osoby które mogą oznaczać zarząd to **administracja**!.\n "
            f"{emoji_cel}Zbyt wiele oznaczeń zarządu będzie się równało **przerwa** na serwerze discord!"
        )

        embed = discord.Embed(description=desc, color=0x2b2d31)
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.set_image(url=TICKET_BANNER)

        ping = interaction.user.mention
        if self.category_name == "zarzad":
            ping += f" <@&{ZARZAD_ROLA_ID}>"
        else:
            ping += f" <@&{ROLA_ADMIN_ID}>"

        await ticket_channel.send(content=ping, embed=embed, view=TicketActionView())
        await interaction.followup.send(f"✅ Otwarto ticket: {ticket_channel.mention}", ephemeral=True)


class TicketActions(discord.ui.Select):
    emoji_konkurs = "<:dailyikon:1516833104378204160>"
    emoji_nie = "<:nie:1516848396684497109>"
    emoji_tak = "<:tak:1516833709796626442>"
    emoji_uwaga = "<:uwagaaa:1531609778944479362>"
    emoji_log = "<:tablica:1516833692985720842>"
    emoji_steve = "<:ikonka_nicku:1516833248246759574>"
    emoji_adm = "<:onlineosobtab:1516833406518820975>"
    emoji_brak = "<:dupa:1530658424335896738>"
    emoji_lista = "<:informacje:1516833263988117587>"
    emoji_czas = "<:nick:1516833363699433492>"
    emoji_plus = "<:plus:1530687822942699760>"
    emoji_minus = "<:minus:1530687824633004042>"
    emoji_stat = "<:staty:1530658283176857690>"
    emoji_gora = "<:gora:1530658287236808764>"
    emoji_dol = "<:dol:1530658293671006228>"
    emoji_zegar = "<:zegar:1516833795410755635>"
    emoji_cel = "<:675:1516834910277734583>"
    emoji_pad = "<:542:1516835059808862239>"
    emoji_sklep = "<:342:1516835085192527953>"
    emoji_ogloszenie = "<:ogloszeniebossbar:1516833385597636780>"
    emoji_klutka = "<:klodka:1516833301518880779>"
    emoji_ziemia = "<:planeta:1516833440979353600>"
    emoji_dc = "<:dc:1516833122929475685>"
    emoji_ranking = "<:ranking:1516833499221594214>"

    def __init__(self):
        options = [
            discord.SelectOption(label="Zamknij", description="Zamyka ticket z powodem (10s)", emoji=self.emoji_nie,
                                 value="close"),
            discord.SelectOption(label="Zmień nazwę", description="Ustawia nową nazwę kanału", emoji=self.emoji_lista,
                                 value="rename"),
            discord.SelectOption(label="Dodaj użytkownika", description="Dodaje osobę po ID", emoji=self.emoji_steve,
                                 value="add"),
            discord.SelectOption(label="Usuń użytkownika", description="Usuwa osobę po ID", emoji=self.emoji_adm,
                                 value="remove"),
            discord.SelectOption(label="Zmień kategorię", description="Przenosi kanał do innej kategorii",
                                 emoji=self.emoji_sklep, value="category"),
            discord.SelectOption(label="Wezwij użytkownika", description="Pinguje użytkownika",
                                 emoji=self.emoji_ogloszenie, value="call"),
            discord.SelectOption(label="Ukryj ticket", description="Ukrywa ticket", emoji=self.emoji_klutka,
                                 value="hide"),
            discord.SelectOption(label="Odkryj ticket", description="Odkrywa ticket", emoji=self.emoji_klutka,
                                 value="show"),
        ]
        super().__init__(placeholder="Wybierz akcję administracyjną...", options=options,
                         custom_id="ticket_admin_actions_v2")

    async def callback(self, interaction: discord.Interaction):
        user_roles_ids = [role.id for role in interaction.user.roles]
        is_admin = ROLA_ADMIN_ID in user_roles_ids or interaction.user.guild_permissions.administrator
        is_zarzad = ZARZAD_ROLA_ID in user_roles_ids or interaction.user.guild_permissions.administrator

        if not is_admin and not is_zarzad:
            return await interaction.response.send_message(f"{emoji_nie} Tylko administracja może używać tych akcji!",
                                                           ephemeral=True)

        val = self.values[0]

        if val in ["hide", "show"]:
            if not is_zarzad:
                return await interaction.response.send_message(f"{emoji_nie} Tylko Zarząd może ukrywać/odkrywać tickety!",
                                                               ephemeral=True)

            role_admin = interaction.guild.get_role(ROLA_ADMIN_ID)
            if not role_admin:
                return await interaction.response.send_message(f"{emoji_nie} Nie znaleziono roli Admina w systemie.",
                                                               ephemeral=True)

            if val == "hide":
                await interaction.channel.set_permissions(role_admin, view_channel=False)
                await interaction.response.send_message("🔒 Ticket został ukryty! Widzi go tylko Zarząd!",
                                                        ephemeral=False)

            elif val == "show":
                await interaction.channel.set_permissions(role_admin, view_channel=True, send_messages=True,
                                                          read_message_history=True)
                await interaction.response.send_message("🔓 Ticket jest ponownie widoczny dla administracji.",
                                                        ephemeral=False)
            return

        if val == "close":
            await interaction.response.send_modal(CloseTicketModal())
        elif val == "rename":
            await interaction.response.send_modal(RenameTicketModal())
        elif val == "add":
            await interaction.response.send_modal(AddUserModal())
        elif val == "remove":
            await interaction.response.send_modal(RemoveUserModal())
        elif val == "category":
            await interaction.response.send_modal(MoveCategoryModal())
        elif val == "call":
            await interaction.response.send_modal(CallUserModal())


class TicketActionView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketActions())


class TicketDropdown(discord.ui.Select):
    emoji_konkursik = "<:konkurs:1531609744152858744>"
    emoji_konkurs = "<:dailyikon:1516833104378204160>"
    emoji_nie = "<:nie:1516848396684497109>"
    emoji_tak = "<:tak:1516833709796626442>"
    emoji_uwaga = "<:uwagaaa:1531609778944479362>"
    emoji_log = "<:tablica:1516833692985720842>"
    emoji_steve = "<:ikonka_nicku:1516833248246759574>"
    emoji_adm = "<:onlineosobtab:1516833406518820975>"
    emoji_brak = "<:dupa:1530658424335896738>"
    emoji_lista = "<:informacje:1516833263988117587>"
    emoji_czas = "<:nick:1516833363699433492>"
    emoji_plus = "<:plus:1530687822942699760>"
    emoji_minus = "<:minus:1530687824633004042>"
    emoji_stat = "<:staty:1530658283176857690>"
    emoji_gora = "<:gora:1530658287236808764>"
    emoji_dol = "<:dol:1530658293671006228>"
    emoji_zegar = "<:zegar:1516833795410755635>"
    emoji_cel = "<:675:1516834910277734583>"
    emoji_pad = "<:542:1516835059808862239>"
    emoji_sklep = "<:342:1516835085192527953>"
    emoji_ogloszenie = "<:ogloszeniebossbar:1516833385597636780>"
    emoji_klutka = "<:klodka:1516833301518880779>"
    emoji_ziemia = "<:planeta:1516833440979353600>"
    emoji_dc = "<:dc:1516833122929475685>"
    emoji_ranking = "<:ranking:1516833499221594214>"

    def __init__(self):
        options = [
            discord.SelectOption(label="Znalazłem błąd", description="Jeśli znalazłeś błąd wybierz te kategorie",
                                 emoji=self.emoji_cel, value="blad"),
            discord.SelectOption(label="Pomoc", description="Potrzebujesz pomocy?", emoji=self.emoji_ogloszenie,
                                 value="pomoc"),
            discord.SelectOption(label="Mam cheatera", description="Znalazłeś cheatera? Wybierz te kategorie",
                                 emoji=self.emoji_uwaga, value="cheater"),
            discord.SelectOption(label="Chcę otrzymać backupa",
                                 description="Kliknij tą opcje jeśli chcesz otrzymać backupa", emoji=self.emoji_ziemia,
                                 value="backup"),
            discord.SelectOption(label="Chcę otrzymać unbana", description="Jeśli chcesz otrzymać unbana to kliknij",
                                 emoji=self.emoji_pad, value="unban"),
            discord.SelectOption(label="Do zarządu", description="Masz sprawe do zarządu?", emoji=self.emoji_klutka,
                                 value="zarzad"),
            discord.SelectOption(label="Płatność", description="Chcę kupić doładowanie za PSC", emoji=self.emoji_sklep,
                                 value="platnosc")
        ]
        super().__init__(placeholder="Wybierz kategorię zgłoszenia", options=options, custom_id="main_ticket_select_v4")

    async def callback(self, interaction: discord.Interaction):
        try:
            val = self.values[0]
            cat_id = TICKET_CATEGORIES.get(val)

            if not cat_id:
                return await interaction.response.send_message(f"{emoji_nie} Kategoria nie istnieje!", ephemeral=True)

            await interaction.response.send_modal(CreateTicketModal(val, cat_id))

        except Exception as e:
            print(f"Błąd w dropdownie: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message(f"{emoji_nie} Wystąpił błąd przy otwieraniu formularza.", ephemeral=True)


class CloseTicketModal(discord.ui.Modal, title="Zamykanie Ticketu"):
    powod = discord.ui.TextInput(label="Powód zamknięcia", placeholder="Np. Problem rozwiązany", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        powod_tekst = self.powod.value
        log_channel = interaction.guild.get_channel(LOGI_TICKET_ID)
        opener_id = interaction.channel.topic

        await interaction.response.send_message(f"{emoji_czas} Zamykanie ticketu i generowanie logów...")

        transcript_txt = f"{emoji_log} LOGI TICKETU: {interaction.channel.name}\n"
        transcript_txt += f"{emoji_steve} Otwarty przez: {opener_id}\n"
        transcript_txt += f"{emoji_adm} Zamknięty przez: {interaction.user} (ID: {interaction.user.id})\n"
        transcript_txt += f"{emoji_lista} Powód: {powod_tekst}\n"
        transcript_txt += "-" * 50 + "\n\n"

        async for message in interaction.channel.history(limit=None, oldest_first=True):
            time_str = message.created_at.strftime("%d.%m.%Y %H:%M:%S")
            content = message.content if message.content else "[Załącznik/Embed]"
            transcript_txt += f"[{time_str}] {message.author}: {content}\n"

        file_admin = discord.File(io.BytesIO(transcript_txt.encode()), filename=f"log-{interaction.channel.name}.txt")
        file_user = discord.File(io.BytesIO(transcript_txt.encode()),
                                 filename=f"Twoja-Transkrypcja-{interaction.channel.name}.txt")

        if log_channel:
            embed_admin = discord.Embed(
                title=f"{emoji_log} Ticket Zamknięty",
                color=0xFF0000,
                timestamp=discord.utils.utcnow()
            )
            embed_admin.add_field(name=f"{emoji_pad} Kanał", value=f"`{interaction.channel.name}`", inline=True)
            embed_admin.add_field(name=f"{emoji_adm} Zamknięty przez", value=interaction.user.mention, inline=True)
            embed_admin.add_field(name=f"{emoji_lista} Powód", value=f"```{powod_tekst}```", inline=False)
            await log_channel.send(embed=embed_admin, file=file_admin)

        if opener_id and opener_id.isdigit():
            try:
                user = await bot.fetch_user(int(opener_id))

                embed_pv = discord.Embed(
                    title=f"{emoji_klutka} Ticket Zamknięty",
                    description=f"Twój ticket **#{interaction.channel.name}** został zamknięty.",
                    color=0xFF0000
                )
                embed_pv.add_field(name=f"{emoji_adm} Zamknięty przez", value=interaction.user.mention, inline=True)
                embed_pv.add_field(name=f"{emoji_lista} Powód", value=f"`{powod_tekst}`", inline=True)
                embed_pv.set_footer(text="777CODE.PL • System Ticket")

                await user.send(embed=embed_pv, file=file_user)
                print(f"{emoji_tak} Wysłano logi .txt na PV do {user.name}")
            except Exception as e:
                print(f"{emoji_nie} Nie udało się wysłać PV do {opener_id}: {e}")

        await asyncio.sleep(10)
        await interaction.channel.delete()


class RenameTicketModal(discord.ui.Modal, title="Zmiana nazwy kanału"):
    nowa_nazwa = discord.ui.TextInput(label="Nowa nazwa", placeholder="np. pomoc-pilne", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.channel.edit(name=self.nowa_nazwa.value)
        await interaction.response.send_message(f"{emoji_tak} Zmieniono nazwę kanału na: `{self.nowa_nazwa.value}`",
                                                ephemeral=True)


class AddUserModal(discord.ui.Modal, title="Dodaj użytkownika do ticketa"):
    user_id = discord.ui.TextInput(label="ID Użytkownika", placeholder="Wklej ID tutaj", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            member = interaction.guild.get_member(int(self.user_id.value))
            if member:
                await interaction.channel.set_permissions(member, view_channel=True, send_messages=True,
                                                          read_message_history=True)
                await interaction.response.send_message(f"{emoji_tak} Dodano {member.mention} do ticketu.", ephemeral=False)
            else:
                await interaction.response.send_message(f"{emoji_nie} Nie znaleziono użytkownika o tym ID.", ephemeral=True)
        except:
            await interaction.response.send_message(f"{emoji_nie} Nieprawidłowe ID.", ephemeral=True)


class RemoveUserModal(discord.ui.Modal, title="Usuń użytkownika z ticketa"):
    user_id = discord.ui.TextInput(label="ID Użytkownika", placeholder="Wklej ID tutaj", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            member = interaction.guild.get_member(int(self.user_id.value))
            if member:
                await interaction.channel.set_permissions(member, overwrite=None)
                await interaction.response.send_message(f"{emoji_tak} Usunięto {member.mention} z ticketu.", ephemeral=False)
            else:
                await interaction.response.send_message(f"{emoji_nie} Nie znaleziono użytkownika.", ephemeral=True)
        except:
            await interaction.response.send_message(f"{emoji_nie} Nieprawidłowe ID.", ephemeral=True)


class MoveCategoryModal(discord.ui.Modal, title="Zmień kategorię"):
    cat_id = discord.ui.TextInput(label="ID Kategorii", placeholder="Wklej ID nowej kategorii", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            category = interaction.guild.get_channel(int(self.cat_id.value))
            if isinstance(category, discord.CategoryChannel):
                await interaction.channel.edit(category=category)
                await interaction.response.send_message(f"{emoji_tak} Przeniesiono kanał do kategorii: **{category.name}**",
                                                        ephemeral=True)
            else:
                await interaction.response.send_message(f"{emoji_nie} To ID nie należy do kategorii.", ephemeral=True)
        except:
            await interaction.response.send_message(f"{emoji_nie} Wystąpił błąd przy przenoszeniu.", ephemeral=True)


class CallUserModal(discord.ui.Modal, title="Wezwij użytkownika"):
    user_id = discord.ui.TextInput(label="ID Użytkownika", placeholder="Wklej ID", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            target_user_id = int(self.user_id.value)
            target_user = await bot.fetch_user(target_user_id)
            opener_id = interaction.channel.topic

            expiry_time = (discord.utils.utcnow() + datetime.timedelta(hours=8)).timestamp()

            data = {}
            if os.path.exists("zamykanie.json"):
                with open("zamykanie.json", "r") as f:
                    data = json.load(f)

            data[str(interaction.channel.id)] = {
                "opener_id": opener_id,
                "expiry": expiry_time
            }

            with open("zamykanie.json", "w") as f:
                json.dump(data, f)

            await interaction.channel.send(
                f"{emoji_ogloszenie} {target_user.mention}, masz **8 godzin** na odpisanie. "
                "Jeśli odpowiesz, automatyczne zamykanie zostanie anulowane."
            )
            await interaction.response.send_message(f"{emoji_tak} Wezwano użytkownika. Automat sprawdzi aktywność za 8h.", ephemeral=True)

            await asyncio.sleep(8 * 3600)
            await self.check_and_close(interaction.channel.id)

        except Exception as e:
            print(f"Błąd wezwania: {e}")

    async def check_and_close(self, channel_id):
        channel = bot.get_channel(channel_id)
        if not channel:
            return

        if os.path.exists("zamykanie.json"):
            with open("zamykanie.json", "r") as f:
                data = json.load(f)

            if str(channel_id) not in data:
                return

            info = data[str(channel_id)]
            opener_id = info["opener_id"]

            last_message = None
            async for msg in channel.history(limit=1):
                last_message = msg

            if last_message:
                member = channel.guild.get_member(last_message.author.id)
                is_staff = last_message.author.bot or (
                            member and any(role.id == ROLA_ADMIN_ID for role in member.roles))

                if not is_staff:
                    del data[str(channel_id)]
                    with open("zamykanie.json", "w") as f:
                        json.dump(data, f)
                    print(f"Anulowano zamknięcie {channel.name} - wykryto odpowiedź.")
                    return

            log_channel = channel.guild.get_channel(LOGI_TICKET_ID)

            transcript_txt = f"{emoji_log} LOGI TICKETU: {channel.name}\nSTATUS: AUTO-ZAMKNIĘCIE (Brak odpowiedzi)\n"
            transcript_txt += "-" * 50 + "\n\n"
            async for message in channel.history(limit=None, oldest_first=True):
                time_str = message.created_at.strftime("%d.%m.%Y %H:%M:%S")
                transcript_txt += f"[{time_str}] {message.author}: {message.content}\n"

            if log_channel:
                embed_admin = discord.Embed(title=f"{emoji_log} Ticket Zamknięty", color=0x414141)
                await log_channel.send(embed=embed_admin,
                                       file=discord.File(io.BytesIO(transcript_txt.encode()), f"auto-{channel.id}.txt"))

            try:
                owner = await bot.fetch_user(int(opener_id))
                embed_pv = discord.Embed(title=f"{emoji_log} Ticket Zamknięty", description="Brak aktywności przez 8h.",
                                         color=0x414141)
                await owner.send(embed=embed_pv,
                                 file=discord.File(io.BytesIO(transcript_txt.encode()), "Transkrypcja.txt"))
            except:
                pass

            del data[str(channel_id)]
            with open("zamykanie.json", "w") as f:
                json.dump(data, f)
            await channel.delete()


class MainTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketDropdown())

@bot.tree.command(name="zamknij", description="Zamyka obecnego ticketa", guild=discord.Object(id=GUILD_ID))
@app_commands.default_permissions(manage_messages=True)
async def zamknij(interaction: discord.Interaction):
    user_roles_ids = [role.id for role in interaction.user.roles]
    is_admin = ROLA_ADMIN_ID in user_roles_ids or interaction.user.guild_permissions.administrator
    is_zarzad = ZARZAD_ROLA_ID in user_roles_ids or interaction.user.guild_permissions.administrator

    if not is_admin and not is_zarzad:
        return await interaction.response.send_message(f"{emoji_nie} Nie masz uprawnień do zamykania ticketów!", ephemeral=True)

    opener_id = interaction.channel.topic
    if not opener_id or not opener_id.isdigit():
        return await interaction.response.send_message(f"{emoji_nie} Ta komenda może być użyta tylko na tickecie!", ephemeral=True)

    await interaction.response.send_modal(CloseTicketModal())

# ---------------------------------------------- WERYFIKACJA - MODAL Z MATEMATYKĄ --------------------------------------

class MathVerifyModal(discord.ui.Modal, title="Weryfikacja Matematyczna"):
    def __init__(self, result, role):
        super().__init__()
        self.correct_result = result
        self.role = role

        self.answer = discord.ui.TextInput(
            label=f"Ile to jest? (Wynik: {self.correct_result} - podpowiedź dla testu)",
            placeholder="Wpisz wynik tutaj...",
            min_length=1,
            max_length=2
        )
        self.add_item(self.answer)

        self.answer.label = "Podaj wynik działania:"

    async def on_submit(self, interaction: discord.Interaction):
        if self.answer.value == str(self.correct_result):
            await interaction.user.add_roles(self.role)

            embed = discord.Embed(
                title=f"{emoji_klutka} Weryfikacja zakończona!",
                description=f"{interaction.user.mention}, zostałeś pomyślnie zweryfikowany.",
                color=discord.Color.green(),
                timestamp=datetime.now(timezone.utc)
            )
            embed.set_thumbnail(url=interaction.user.display_avatar.url)
            embed.set_footer(text="System weryfikacji")

            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(f"{emoji_nie} Niepoprawny wynik. Spróbuj ponownie!", ephemeral=True)


class VerifyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="\u2800" * 13 + "Kliknij, aby się zweryfikować" + "\u2800" * 13,
        style=discord.ButtonStyle.secondary,
        custom_id="rec_th_v2"
    )
    async def verify(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = interaction.guild.get_role(VERIFIED_ROLE_ID)

        if role in interaction.user.roles:
            await interaction.response.send_message(f"{emoji_nie} Jesteś już zweryfikowany.", ephemeral=True)
            return

        a = random.randint(1, 20)
        b = random.randint(1, 20)
        operation = random.choice(["+", "-"])

        if operation == "-":
            if a < b: a, b = b, a
            result = a - b
        else:
            a = random.randint(1, 10)
            b = random.randint(1, 10)
            result = a + b

        modal = MathVerifyModal(result=result, role=role)
        modal.answer.label = f"Ile to jest {a} {operation} {b}?"

        await interaction.response.send_modal(modal)

# ----------------------------------------------------- EVENTY -----------------------------------------------------------------------------------

@bot.event
async def on_ready():
    print(f"✅ Zalogowano jako {bot.user}")
    guild = discord.Object(id=GUILD_ID)
    await bot.tree.sync(guild=guild)
    print("Komendy zsynchronizowane.")

    if os.path.exists("zamykanie.json"):
        with open("zamykanie.json", "r") as f:
            data = json.load(f)

        for ch_id, info in list(data.items()):
            now = discord.utils.utcnow().timestamp()
            remaining = info["expiry"] - now

            if remaining <= 0:
                pass
            else:
                pass

@bot.event
async def on_member_join(member):
    channel = bot.get_channel(WELCOME_CHANNEL_ID)

    if channel:
        desc = (
            f"{emoji_steve} **Cześć!** {member.mention}, dziękujemy,\n"
            f"że dołączyłeś na nasz serwera {emoji_dc} Discord!\n"
            f"Twoja obecność sprawiła, że jest nas już `{member.guild.member_count}` osób!\n\n"
            f"{emoji_lista}**Dołączył(a) na serwer:** <t:{int(member.joined_at.timestamp())}:R>\n"
            f"{emoji_zegar} **Stworzone konto:** <t:{int(member.created_at.timestamp())}:F>"
        )

        embed = discord.Embed(title="`777CODE.PL × Powitalnia`", description=desc, color=discord.Color.green())
        embed.set_footer(
            text="777CODE.PL × SYSTEM POWITAŃ",
            icon_url=member.guild.icon.url if member.guild.icon else None
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_image(url=URL_BANER)
        await channel.send(embed=embed)

# ------------------------------------------------ POZOSTAŁE KOMENDY ----------------------------------------------------

# --- KOMENDA /PRZENIES ---

@bot.tree.command(name="przenies", description="Przenosi kanał do wybranej kategorii",
                  guild=discord.Object(id=GUILD_ID))
@app_commands.default_permissions(administrator=True)
@app_commands.describe(
    kategoria="Kategoria, do której ma trafić kanał",
    kanal="Kanał, który chcesz przenieść (opcjonalnie, domyślnie obecny)"
)
async def przenies(interaction: discord.Interaction, kategoria: discord.CategoryChannel,
                   kanal: discord.TextChannel = None):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message(f"{emoji_nie} Nie masz uprawnień do przenoszenia kanałów!", ephemeral=True)

    target_channel = kanal or interaction.channel

    try:
        await target_channel.edit(category=kategoria)

        embed = discord.Embed(
            title=f"{emoji_tak} Przeniesiono kanał",
            description=f"Kanał {target_channel.mention} został pomyślnie przeniesiony do kategorii **{kategoria.name}**.",
            color=discord.Color.green()
        )
        embed.set_footer(text=f"Przez: {interaction.user.display_name}")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    except Exception as e:
        await interaction.response.send_message(f"{emoji_nie} Wystąpił błąd podczas przenoszenia: {e}", ephemeral=True)


# --- KOMENDA /ZMIANA ---

@bot.tree.command(name="zmiana", description="Wysyła ogłoszenie o zmianie na serwerze",
                  guild=discord.Object(id=GUILD_ID))
@app_commands.default_permissions(administrator=True)
@app_commands.describe(
    tryb="Nagłówek zmiany (np BOXPVP, ANARCHIA-FFA, GENCASH)",
    typzmiany="Wybierz rodzaj zmiany",
    opis="Treść zmiany",
    przezkogo="Osoba odpowiedzialna za zmianę"
)
@app_commands.choices(typzmiany=[
    app_commands.Choice(name="Nowość", value="nowosc"),
    app_commands.Choice(name="Aktualizacja", value="aktualizacja"),
    app_commands.Choice(name="Usunięto", value="usuniecie")
])
async def zmiana(interaction: discord.Interaction, tryb: str, typzmiany: app_commands.Choice[str], opis: str,
                 przezkogo: discord.Member):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message(f"{emoji_brak} Nie masz uprawnień!", ephemeral=True)

    if typzmiany.value == "nowosc":
        kolor = discord.Color.green()
        naglowek = f"{emoji_gora} NOWOŚĆ ({tryb.upper()})"
        tekst_wstepny = "Wprowadziliśmy nowość na serwer!"
    elif typzmiany.value == "aktualizacja":
        kolor = discord.Color.orange()
        naglowek = f"{emoji_uwaga} AKTUALIZACJA ({tryb.upper()})"
        tekst_wstepny = "Wprowadziliśmy zmianę na serwerze!"
    else:
        kolor = discord.Color.red()
        naglowek = f"{emoji_brak} USUNIĘTO ({tryb.upper()})"
        tekst_wstepny = "Usunięto z serwera!"

    embed = discord.Embed(
        title=naglowek,
        description=f"{tekst_wstepny}\n\n```\n{opis}\n```",
        color=kolor
    )

    current_time = discord.utils.utcnow().strftime("%d.%m.%Y %H:%M")
    embed.set_footer(
        text=f"Wprowadzone przez: {przezkogo.display_name} • {current_time}",
        icon_url=przezkogo.display_avatar.url
    )

    role = interaction.guild.get_role(ZMIANA_ROLA_ID)
    ping_content = role.mention if role else ""

    await interaction.response.send_message(content=f"{emoji_tak} Pomyślnie wysłano ogłoszenie!", ephemeral=True)
    await interaction.channel.send(content=ping_content, embed=embed)

# --- KOMENDA /DMALL ---

@bot.tree.command(name="dmall", description="Wysyła wiadomość pv do wszystkich członków serwera.")
@app_commands.describe(
    tytul="Tytul embedu",
    tresc="Tresc embedu"
)
@app_commands.checks.has_permissions(administrator=True)
async def dmall(interaction: discord.Interaction, tytul: str, tresc: str):
    await interaction.response.send_message("Rozpoczynam wysyłanie wiadomości prywatnych...", ephemeral=True)

    guild = interaction.guild
    if not guild:
        return

    embed = discord.Embed(
        title=tytul,
        description=tresc,
        color=discord.Color.green()
    )
    embed.set_image(url=URL_BANER)

    udane = 0
    nieudane = 0

    for member in guild.members:
        if member.bot:
            continue

        try:
            await member.send(embed=embed)
            udane += 1
        except discord.Forbidden:
            nieudane += 1
        except Exception:
            nieudane += 1

    await interaction.followup.send(
        f"Zakończono wysyłanie!\n✅ Wysłano pomyślnie: **{udane}**\n❌ Nie udało się: **{nieudane}**",
        ephemeral=True
    )

# --- KOMENDA /KONKURS ---

@app_commands.command(name="konkurs", description="Tworzy nowy konkurs.")
@app_commands.describe(
    czas="Czas trwania (np. 10s, 5m, 2h, 1d)",
    wygrani="Liczba zwycięzców",
    nagroda="Nagroda do wygrania",
)
async def konkurs(
    interaction: discord.Interaction, czas: str, wygrani: int, nagroda: str
):
    await interaction.response.defer(ephemeral=True)

    unit = czas[-1].lower()
    if unit not in ["s", "m", "h", "d"] or not czas[:-1].isdigit():
        await interaction.followup.send(
            f"{emoji_nie} Nieprawidłowy format czasu! Użyj np. `30s`, `10m`, `2h`, `1d`.",
            ephemeral=True,
        )
        return

    val = int(czas[:-1])
    multipliers = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    seconds = val * multipliers[unit]

    end_time_dt = datetime.now(timezone.utc) + timedelta(seconds=seconds)
    end_ts = int(end_time_dt.timestamp())

    embed = discord.Embed(
        title=f"{emoji_konkursik} KONKURS: {nagroda}",
        description=(
            f"Kliknij przycisk poniżej, aby dołączyć!\n\n"
            f"{emoji_ranking} **Liczba wygranych:** {wygrani}\n"
            f"{emoji_czas} **Koniec:** <t:{end_ts}:R> (<t:{end_ts}:F>)\n"
            f"{emoji_adm} **Organizator:** {interaction.user.mention}"
        ),
        color=discord.Color.green(),
    )
    embed.set_image(url=URL_BANER)
    embed.set_thumbnail(url=URL_LOGO)

    channel = interaction.channel
    msg = await channel.send(embed=embed)

    active_giveaways[str(msg.id)] = {
        "channel_id": channel.id,
        "prize": nagroda,
        "winners_count": wygrani,
        "end_time": end_ts,
        "participants": [],
        "winners": [],
        "ended": False,
    }
    save_giveaways(active_giveaways)

    await msg.edit(view=GiveawayJoinView(msg.id))
    await interaction.followup.send(
        f"{emoji_tak} Konkurs został pomyślnie utworzony na kanale {channel.mention}!",
        ephemeral=True,
    )

# --- KOMENDA /REROLL ---
@app_commands.command(name="reroll", description="Losuje nowego zwycięzcę dla zakończonego konkursu.")
@app_commands.describe(message_id="ID wiadomości z konkursem")
async def reroll(interaction: discord.Interaction, message_id: str):
    await interaction.response.defer(ephemeral=True)

    gw = active_giveaways.get(str(message_id))
    if not gw:
        await interaction.followup.send(f"{emoji_brak} Nie znaleziono konkursu o podanym ID", ephemeral=True)
        return

    participants = gw.get("participants", [])
    if not participants:
        await interaction.followup.send(f"{emoji_brak} Brak uczestników w tym konkursie!", ephemeral=True)
        return

    previous_winners = gw.get("winners", [])
    valid_participants = [u_id for u_id in participants if u_id not in previous_winners]

    if not valid_participants:
        await interaction.followup.send(f"{emoji_brak} Brak innych uczestników do ponownego losowania!", ephemeral=True)
        return

    new_winner_id = random.choice(valid_participants)
    gw.setdefault("winners", []).append(new_winner_id)

    new_winner = interaction.guild.get_member(new_winner_id)
    if not new_winner:
        try:
            new_winner = await interaction.guild.fetch_member(new_winner_id)
        except discord.NotFound:
            new_winner = None

    channel = interaction.guild.get_channel(gw.get("channel_id")) or interaction.channel
    prize = gw.get("prize", "nagrodę")


    if new_winner:
        await channel.send(f"{emoji_konkursik} **REROLL!** Nowym zwycięzcą nagrody **{prize}** zostaje: {new_winner.mention}! Gratulacje!")
        await interaction.followup.send(f"{emoji_tak} Pomyślnie wylosowano nowego zwycięzcę: {new_winner.mention}", ephemeral=True)
    else:
        await interaction.followup.send(f"{emoji_konkursik} **REROLL!** Nowym zwycięzcą został użytkownik o ID `{new_winner_id}`, ale nie ma go już na serwerze.", ephemeral=True)

# --- KOMENDA /PANEL ---
@bot.tree.command(
    name="panel",
    description="Wysyła wybrany panel na kanał",
    guild=discord.Object(id=GUILD_ID),
)
@app_commands.default_permissions(administrator=True)
@app_commands.choices(
    typ=[
        app_commands.Choice(name="Weryfikacja", value="weryfikacja"),
        app_commands.Choice(name="Rekrutacja", value="rekrutacja"),
        app_commands.Choice(name="Tickety", value="ticket"),
    ]
)
async def panel(interaction: discord.Interaction, typ: app_commands.Choice[str]):
    # --- PANEL WERYFIKACJI ---
    if typ.value == "weryfikacja":
        emoji_uwaga = "<:uwagaaa:1531609778944479362>"
        role_mention = f"<@&{1518254880928563240}>"

        embed = discord.Embed(
            title=f"{emoji_klutka} WERYFIKACJA",
            description=(
                f"> {emoji_uwaga} Aby odblokować wszystkie kanały i funkcje serwera, wykonaj krótką weryfikację matematyczną, klikając przycisk poniżej. \n\n"
                f"> {emoji_ziemia} Po pomyślnym ukończeniu weryfikacji automatycznie otrzymasz rolę {role_mention} i uzyskasz pełny dostęp do serwera. \n\n"
                f"> {emoji_pad} Dziękujemy za współpracę i życzymy miłego pobytu na serwerze! "
            ),
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow(),
        )
        embed.set_image(url=URL_BANER)

        await interaction.channel.send(embed=embed, view=VerifyView())
        await interaction.response.send_message(
            f"{emoji_tak} Panel weryfikacji został pomyślnie wysłany.", ephemeral=True
        )

    # --- PANEL REKRUTACJI ---
    elif typ.value == "rekrutacja":
        emoji_lista = "<:informacje:1516833263988117587>"
        await interaction.response.defer(ephemeral=True)

        embed = discord.Embed(
            title=f"{emoji_lista} 777CODE.PL - Rekrutacja",
            description=(
                "Właśnie ruszyła kolejna tura rekrutacji do naszej administracji na range **TestHelper**! Jedyne co trzeba zrobić to kliknąć przycisk pod spodem i wypełnić formularz!\n"
                "Pamiętaj, że musisz spełniać **WSZYSTKIE WYMAGANIA**!\n"
            ),
            color=discord.Color.green(),
        )
        embed.set_image(url=URL_BANER)

        msg = await interaction.channel.send(embed=embed, view=RekrutacjaView())

        bot_config["panel_channel_id"] = interaction.channel_id
        bot_config["panel_message_id"] = msg.id
        save_config(bot_config)

        await interaction.followup.send(
            f"{emoji_tak} Panel rekrutacyjny został pomyślnie wysłany!", ephemeral=True
        )

    # --- PANEL TICKETÓW ---
    elif typ.value == "ticket":
        emoji_lista = "<:informacje:1516833263988117587>"
        emoji_uwaga = "<:uwagaaa:1531609778944479362>"
        emoji_ogloszenie = "<:ogloszeniebossbar:1516833385597636780>"

        embed = discord.Embed(
            title="777CODE.PL × Tickety",
            description=(
                f"{emoji_lista} **Cześć!** Jeśli potrzebujesz pomocy od naszego zespołu administracji,\n "
                f"wybierz odpowiednią kategorię zgłoszenia **poniżej!**\n\n "
                f"{emoji_uwaga} Każde **zgłoszenie** jest dla nas ważne, jednak czas odpowiedzi może wynosić do 24 godzin.\n\n "
                f"{emoji_ogloszenie} Dziękujemy za cierpliwość — odpowiadamy wszystkim po kolei!\n "
                f"Wybierz kategorię, aby rozpocząć zgłoszenie"
            ),
            color=discord.Color.green(),
        )
        embed.set_image(url=TICKET_BANNER)
        embed.set_thumbnail(url=TICKET_LOGO)
        await interaction.channel.send(embed=embed, view=MainTicketView())
        await interaction.response.send_message(f"{emoji_tak} Panel ticketow został pomyślnie wysłany.", ephemeral=True)

# ------------------------------------------ KOMENDY MODERACYJNE ------------------------------------------

URL_LOGO = "https://cdn.discordapp.com/attachments/1530659348139737218/1531265348286943302/777code_-_logo_new.png?ex=6a68957c&is=6a6743fc&hm=9b4feb80af61b16c85f5b74396f3ffc86c28f5103c91e4076b5daaf833b5429d&"
URL_BANER = "https://cdn.discordapp.com/attachments/1530659348139737218/1531265091767636028/777Code-Embedy.png?ex=6a68953f&is=6a6743bf&hm=267db0486f6c4ddf63f1f4c74811a0e27aab95cb21f9e71039f9937c7794f14f&"

@bot.tree.command(name="wezwij", description="Wysyła wezwanie na pv",
                  guild=discord.Object(id=GUILD_ID))
@app_commands.default_permissions(administrator=True)
@app_commands.describe(
    uzytkownik="Kogo chcesz wezwać?",
    kanal="Na jaki kanał ma się stawić?",
    opis="W jakim celu jest wzywany?",
    czas="Ile ma czasu na przybycie?"
)
@app_commands.choices(czas=[
    app_commands.Choice(name="30 sekund", value="30s"),
    app_commands.Choice(name="10 minut", value="10m"),
    app_commands.Choice(name="15 minut", value="15m"),
    app_commands.Choice(name="30 minut", value="30m"),
    app_commands.Choice(name="1 godzina", value="1h"),
    app_commands.Choice(name="8 godzin", value="8h"),
    app_commands.Choice(name="24 godziny", value="24h"),
    app_commands.Choice(name="7 dni", value="7d")
])
async def wezwij(
        interaction: discord.Interaction,
        uzytkownik: discord.Member,
        kanal: discord.TextChannel | discord.VoiceChannel,
        opis: str,
        czas: str
):
    await interaction.response.defer(ephemeral=True)

    embed_pv = discord.Embed(
        title=f"{emoji_uwaga} ZOSTAŁEŚ WEZWANY!",
        description=f"Otrzymałeś wezwanie od **{interaction.user.mention}**.",
        color=discord.Color.green()
    )
    embed_pv.add_field(name=f"{emoji_ziemia} Kanał:", value=kanal.mention, inline=False)
    embed_pv.add_field(name=f"{emoji_czas} Czas:", value=czas, inline=False)
    embed_pv.add_field(name=f"{emoji_lista} Powód:", value=opis, inline=False)
    embed_pv.set_thumbnail(url=URL_LOGO)
    embed_pv.set_image(url=URL_BANER)

    pv_status = f"{emoji_tak} Wysłano pomyślnie"
    try:
        if not uzytkownik.bot:
            await uzytkownik.send(embed=embed_pv)
        else:
            pv_status = f"{emoji_nie} Nie można wezwać bota"
    except discord.Forbidden:
        pv_status = f"{emoji_brak} Użytkownik ma zablokowane pv!"
    except Exception as e:
        pv_status = f"{emoji_brak} Błąd: {str(e)}"

    log_channel = bot.get_channel(LOGI_ADMIN_ID)

    if log_channel:
        embed_log = discord.Embed(
            title=f"{emoji_log} Log WEZWANIA",
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow()
        )
        embed_log.add_field(name=f"{emoji_adm} Wzywający:", value=interaction.user.mention, inline=False)
        embed_log.add_field(name=f"{emoji_steve} Wzywany:", value=uzytkownik.mention, inline=False)
        embed_log.add_field(name=f"{emoji_log} Status dostarczenia:", value=pv_status, inline=False)
        embed_log.add_field(name=f"{emoji_ziemia} Kanał:", value=kanal.mention, inline=False)
        embed_log.add_field(name=f"{emoji_czas} Czas:", value=czas, inline=False)
        embed_log.add_field(name=f"{emoji_lista} Opis:", value=opis, inline=False)
        embed_log.set_thumbnail(url=URL_LOGO)
        embed_log.set_image(url=URL_BANER)

        try:
            await log_channel.send(embed=embed_log)
        except Exception:
            print(f"{emoji_brak} Błąd wysyłania na kanał logów.")
    else:
        print(f"BŁĄD: Nie znaleziono kanału logów o ID {LOGI_ADMIN_ID}")

    await interaction.followup.send(
        f"Wezwano użytkownika.\n**Status wysyłki:** {pv_status}"
    )


@bot.tree.command(name="mute", description="Wycisza użytkownika na określony czas", guild=discord.Object(id=GUILD_ID))
@app_commands.default_permissions(manage_messages=True)
@app_commands.describe(
    uzytkownik="Użytkownik do wyciszenia",
    czas="Czas (np. 10m, 1h, 1d)",
    powod="Powód wyciszenia"
)
async def mute(interaction: discord.Interaction, uzytkownik: discord.Member, czas: str, powod: str = "Brak powodu"):

    seconds = parse_duration(czas)
    if not seconds:
        return await interaction.response.send_message(f"{emoji_nie} Niepoprawny format czasu!", ephemeral=True)

    duration_td = timedelta(seconds=seconds)
    until = discord.utils.utcnow() + duration_td

    try:
        await uzytkownik.timeout(until, reason=f"Przez: {interaction.user} > Powód: {powod}")

        embed_pv = discord.Embed(title=f"{emoji_brak} Zostałeś wyciszony!", color=discord.Color.green())
        end_timestamp = int(until.timestamp())
        embed_pv.add_field(name=f"{emoji_lista} Powód", value=powod, inline=False)
        embed_pv.add_field(name=f"{emoji_czas} Koniec", value=f"<t:{end_timestamp}:R>", inline=False)
        embed_pv.set_thumbnail(url=URL_LOGO)
        embed_pv.set_image(url=URL_BANER)

        try:
            await uzytkownik.send(embed=embed_pv)
        except Exception:
            pass

        log_channel = bot.get_channel(LOGI_ADMIN_ID)
        if log_channel:
            embed_log = discord.Embed(title=f"{emoji_log} Log MUTE", color=discord.Color.green(), timestamp=discord.utils.utcnow())
            embed_log.add_field(name=f"{emoji_steve} Użytkownik", value=uzytkownik.mention, inline=False)
            embed_log.add_field(name=f"{emoji_adm} Administrator", value=interaction.user.mention, inline=False)
            embed_log.add_field(name=f"{emoji_czas} Czas", value=czas, inline=False)
            embed_log.add_field(name=f"{emoji_lista} Powód", value=powod, inline=False)
            embed_log.set_thumbnail(url=URL_LOGO)
            embed_log.set_image(url=URL_BANER)

            await log_channel.send(embed=embed_log)

        await interaction.response.send_message(f"{emoji_tak} Wyciszono {uzytkownik.mention}.", ephemeral=True)

    except Exception as e:
        await interaction.response.send_message(f"{emoji_brak} Błąd: {e}", ephemeral=True)


@bot.tree.command(name="unmute", description="Zdejmuje wyciszenie z użytkownika", guild=discord.Object(id=GUILD_ID))
@app_commands.default_permissions(manage_messages=True)
@app_commands.describe(uzytkownik="Użytkownik, któremu chcesz zdjąć wyciszenie")
async def unmute(interaction: discord.Interaction, uzytkownik: discord.Member):

    if not uzytkownik.is_timed_out():
        return await interaction.response.send_message(f"{emoji_steve} Użytkownik {uzytkownik.mention} nie jest obecnie wyciszony.",
                                                       ephemeral=True)

    try:
        await uzytkownik.timeout(None)

        embed_pv = discord.Embed(
            title=f"{emoji_ogloszenie} Twoje wyciszenie zostało zdjęte!",
            description=f"Twoja blokada na serwerze **{interaction.guild.name}** została usunięta przez {interaction.user.mention}.",
            color=discord.Color.green()
        )
        embed_pv.set_thumbnail(url=URL_LOGO)
        embed_pv.set_image(url=URL_BANER)

        try:
            await uzytkownik.send(embed=embed_pv)
        except Exception:
            pass

        log_channel = bot.get_channel(LOGI_ADMIN_ID)
        if log_channel:
            embed_log = discord.Embed(title=f"{emoji_log} Log UNMUTE", color=discord.Color.green(), timestamp=discord.utils.utcnow())
            embed_log.add_field(name=f"{emoji_steve} Użytkownik", value=uzytkownik.mention, inline=False)
            embed_log.add_field(name=f"{emoji_adm} Administrator", value=interaction.user.mention, inline=False)
            embed_log.add_field(name=f"{emoji_lista} Status", value="Usunieto wyciszenie", inline=False)
            embed_log.set_thumbnail(url=URL_LOGO)
            embed_log.set_image(url=URL_BANER)

            await log_channel.send(embed=embed_log)

        await interaction.response.send_message(f"{emoji_tak} Pomyślnie usunieto wyciszenie użytkownikowi {uzytkownik.mention}.",
                                                ephemeral=True)

    except Exception as e:
        await interaction.response.send_message(f"{emoji_brak} Wystąpił błąd: {e}", ephemeral=True)


WARNS_FILE = "warns.json"

def load_warns():
    if os.path.exists(WARNS_FILE):
        with open(WARNS_FILE, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                return {int(k): v for k, v in data.items()}
            except json.JSONDecodeError:
                return {}
    return {}


def save_warns(warns_data):
    with open(WARNS_FILE, "w", encoding="utf-8") as f:
        json.dump(warns_data, f, ensure_ascii=False, indent=4)


warns_count = load_warns()


@bot.tree.command(name="warn", description="Nakłada ostrzeżenie", guild=discord.Object(id=GUILD_ID))
@app_commands.default_permissions(manage_messages=True)
@app_commands.describe(uzytkownik="Kogo ostrzec", powod="Powód")
async def warn(interaction: discord.Interaction, uzytkownik: discord.Member, powod: str):
    if uzytkownik.bot:
        return await interaction.response.send_message(f"{emoji_nie} Nie możesz ostrzec bota.", ephemeral=True)

    await interaction.response.defer(ephemeral=True)

    user_id = uzytkownik.id
    current_warns = warns_count.get(user_id, 0) + 1

    limit_reached = current_warns >= 3

    if limit_reached:
        warns_count[user_id] = 0
        display_warns = "3/3"
    else:
        warns_count[user_id] = current_warns
        display_warns = f"{current_warns}/3"

    save_warns(warns_count)

    embed_pv = discord.Embed(
        title=f"{emoji_uwaga} Otrzymałeś ostrzeżenie!",
        description=f"\nOtrzymałeś ostrzeżenie na serwerze **777CODE.PL**\n\n{emoji_stat} Ilość ostrzeżeń: **{display_warns}**",
        color=discord.Color.green()
    )
    embed_pv.add_field(name=f"{emoji_lista} Powód:", value=powod, inline=False)
    embed_pv.set_thumbnail(url=URL_LOGO)
    embed_pv.set_image(url=URL_BANER)

    mute_info = ""
    if limit_reached:
        try:
            until_time = datetime.now(timezone.utc) + timedelta(minutes=30)
            await uzytkownik.timeout(until_time, reason="Osiągnięcie limitu 3 ostrzeżeń")
            embed_pv.description += mute_info
        except discord.Forbidden:
            mute_info = "\n*(Brak uprawnień bota – upewnij się, że rola bota jest wyżej niż rola użytkownika)*"
        except Exception as e:
            mute_info = f"\n*(Błąd wyciszenia: {e})*"

    try:
        await uzytkownik.send(embed=embed_pv)
    except Exception:
        pass

    log_channel = bot.get_channel(LOGI_ADMIN_ID)
    if log_channel:
        embed_log = discord.Embed(title=f"{emoji_log} Log WARN", color=discord.Color.green(),
                                  timestamp=datetime.now(timezone.utc))
        embed_log.add_field(name=f"{emoji_steve} Użytkownik", value=f"{uzytkownik.mention}", inline=False)
        embed_log.add_field(name=f"{emoji_stat} Ilość ostrzeżeń", value=display_warns, inline=False)
        embed_log.add_field(name=f"{emoji_adm} Moderator", value=interaction.user.mention, inline=False)
        embed_log.add_field(name=f"{emoji_lista} Powód", value=powod, inline=False)
        embed_log.set_thumbnail(url=URL_LOGO)
        embed_log.set_image(url=URL_BANER)

        try:
            await log_channel.send(embed=embed_log)
        except Exception:
            pass

    await interaction.followup.send(f"{emoji_tak} Ostrzeżono {uzytkownik.mention} ({display_warns}).{mute_info}")

@bot.tree.command(name="checkwarns", description="Sprawdza warny", guild=discord.Object(id=GUILD_ID))
@app_commands.default_permissions(administrator=True)
async def checkwarns(interaction: discord.Interaction, uzytkownik: discord.Member):
    ilosc = warns_count.get(uzytkownik.id, 0)
    embed = discord.Embed(title=f"{emoji_stat} Status warn: {uzytkownik.display_name}", description=f"Ostrzeżenia: **{ilosc}/3**",
                          color=discord.Color.green())
    embed.set_thumbnail(url=URL_LOGO)
    embed.set_image(url=URL_BANER)
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="clearwarns", description="Resetuje warny", guild=discord.Object(id=GUILD_ID))
@app_commands.default_permissions(administrator=True)
async def clearwarns(interaction: discord.Interaction, uzytkownik: discord.Member):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message(f"{emoji_brak} Brak uprawnień!", ephemeral=True)
    warns_count[uzytkownik.id] = 0
    await interaction.response.send_message(f"{emoji_tak} Wyzerowano warny dla {uzytkownik.mention}.", ephemeral=True)


@bot.tree.command(name="kick", description="Wyrzuca użytkownika z serwera", guild=discord.Object(id=GUILD_ID))
@app_commands.default_permissions(administrator=True)
@app_commands.describe(uzytkownik="Kogo wyrzucić", powod="Powód wyrzucenia")
async def kick(interaction: discord.Interaction, uzytkownik: discord.Member, powod: str):
    if not interaction.user.guild_permissions.kick_members:
        return await interaction.response.send_message(f"{emoji_brak} Nie masz uprawnień!", ephemeral=True)

    if uzytkownik.top_role >= interaction.guild.me.top_role:
        return await interaction.response.send_message(
            f"{emoji_nie} Nie możesz wyrzucić tego użytkownika!", ephemeral=True)

    if uzytkownik.top_role >= interaction.user.top_role and interaction.user.id != interaction.guild.owner_id:
        return await interaction.response.send_message(f"{emoji_nie} Nie możesz wyrzucić osoby z rangą wyższą lub równą Twojej!",
                                                       ephemeral=True)

    embed_pv = discord.Embed(
        title=f"{emoji_brak} Zostałeś Wyrzucony!",
        description=f"Twoje konto zostało wyrzucone z serwera **{interaction.guild.name}**",
        color=0x414141
    )
    embed_pv.add_field(name=f"{emoji_adm} Administrator:", value=interaction.user.mention, inline=False)
    embed_pv.add_field(name=f"{emoji_lista} Powód:", value=f"{powod}", inline=False)
    embed_pv.set_thumbnail(url=URL_LOGO)
    embed_pv.set_image(url=URL_BANER)

    try:
        await uzytkownik.send(embed=embed_pv)
    except Exception:
        pass

    try:
        await uzytkownik.kick(reason=f"Przez: {interaction.user} > Powód: {powod}")

        log_channel = bot.get_channel(LOGI_ADMIN_ID)
        if log_channel:
            embed_log = discord.Embed(title=f"{emoji_log} Log KICK", color=discord.Color.green(), timestamp=discord.utils.utcnow())
            embed_log.add_field(name=f"{emoji_steve} Użytkownik", value=f"{uzytkownik.mention}", inline=False)
            embed_log.add_field(name=f"{emoji_adm} Administrator", value=interaction.user.mention, inline=False)
            embed_log.add_field(name=f"{emoji_lista} Powód", value=powod, inline=False)
            embed_log.set_thumbnail(url=URL_LOGO)
            embed_log.set_image(url=URL_BANER)

            await log_channel.send(embed=embed_log)

        res_embed = discord.Embed(
            description=f"{emoji_tak} Pomyślnie wyrzucono użytkownika **{uzytkownik.name}**.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=res_embed, ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"{emoji_brak} Wystąpił błąd podczas wyrzucania: {e}", ephemeral=True)


@bot.tree.command(name="ban", description="Banuje użytkownika z serwera", guild=discord.Object(id=GUILD_ID))
@app_commands.default_permissions(administrator=True)
@app_commands.describe(uzytkownik="Kogo zbanować", powod="Powód bana")
async def ban(interaction: discord.Interaction, uzytkownik: discord.Member, powod: str):
    if not interaction.user.guild_permissions.ban_members:
        return await interaction.response.send_message(f"{emoji_brak} Nie masz uprawnień!", ephemeral=True)

    if uzytkownik.top_role >= interaction.guild.me.top_role:
        return await interaction.response.send_message(f"{emoji_brak} Nie mogę zbanować tego użytkownika!", ephemeral=True)

    embed_pv = discord.Embed(title=f"{emoji_brak} Zostałeś Zbanowany!",
                             description=f"Zostałeś zablokowany na serwerze **777CODE.PL**",
                             color=0x414141)
    embed_pv.add_field(name=f"{emoji_lista} Powód:", value=f"**{powod}**", inline=False)
    embed_pv.add_field(name=f"{emoji_adm} Administrator:", value=f"**{interaction.user.mention}**", inline=False)
    embed_pv.add_field(name="\u200b", value=f"{emoji_uwaga} Jeśli uważasz, że to pomyłka, skontaktuj się z administracją.",
                       inline=False)
    embed_pv.set_thumbnail(url=URL_LOGO)
    embed_pv.set_image(url=URL_BANER)

    try:
        await uzytkownik.send(embed=embed_pv)
    except Exception:
        pass

    try:
        await uzytkownik.ban(reason=f"Przez: {interaction.user} > Powód: {powod}")

        log_channel = bot.get_channel(LOGI_ADMIN_ID)
        if log_channel:
            embed_log = discord.Embed(title=f"{emoji_log} Log BAN", color=discord.Color.green())
            embed_log.add_field(name=f"{emoji_steve} Użytkownik", value=f"{uzytkownik.mention}", inline=False)
            embed_log.add_field(name=f"{emoji_klutka} ID", value=f"{uzytkownik.id}", inline=False)
            embed_log.add_field(name=f"{emoji_adm} Administrator", value=interaction.user.mention, inline=False)
            embed_log.add_field(name=f"{emoji_lista} Powód", value=powod, inline=False)
            embed_log.set_footer(text="Akcja: Permanentny Ban")
            embed_log.set_thumbnail(url=URL_LOGO)
            embed_log.set_image(url=URL_BANER)

            await log_channel.send(embed=embed_log)

        await interaction.response.send_message(
            embed=discord.Embed(description=f"{emoji_tak} Zbanowano **{uzytkownik.mention}**.", color=discord.Color.green()),
            ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"{emoji_brak} Błąd: {e}", ephemeral=True)


@bot.tree.command(name="unban", description="Odbanowuje użytkownika", guild=discord.Object(id=GUILD_ID))
@app_commands.default_permissions(administrator=True)
@app_commands.describe(user_id="ID użytkownika")
async def unban(interaction: discord.Interaction, user_id: str):
    if not interaction.user.guild_permissions.ban_members:
        return await interaction.response.send_message(f"{emoji_brak} Brak uprawnień!", ephemeral=True)

    try:
        user = await bot.fetch_user(int(user_id))
        await interaction.guild.unban(user, reason=f"Odbanowany przez: {interaction.user}")

        log_channel = bot.get_channel(LOGI_ADMIN_ID)
        if log_channel:
            embed = discord.Embed(title=f"{emoji_log} Log UNBAN", color=discord.Color.green())
            embed.add_field(name=f"{emoji_steve} ID", value=f"{user.id}", inline=False)
            embed.add_field(name=f"{emoji_adm} Administrator", value=interaction.user.mention, inline=False)
            embed.set_footer(text="Akcja: Cofnięcie Bana")
            embed.set_thumbnail(url=URL_LOGO)
            embed.set_image(url=URL_BANER)

            await log_channel.send(embed=embed)

        await interaction.response.send_message(
            embed=discord.Embed(description=f"{emoji_tak} Odbanowano **{user.name}**.", color=discord.Color.green()),
            ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"{emoji_brak} Błąd: {e}", ephemeral=True)

@bot.tree.command(name="clear", description="Usuwa określoną ilość wiadomości z kanału.")
@app_commands.describe(ilosc="Liczba wiadomości do usunięcia (max 100)")
@app_commands.checks.has_permissions(manage_messages=True)
async def clear(interaction: discord.Interaction, ilosc: int):
    await interaction.response.defer(ephemeral=True)

    if ilosc <= 0:
        await interaction.followup.send("Podaj liczbę większą od 0!")
        return

    if ilosc > 100:
        await interaction.followup.send("Możesz usunąć maksymalnie 100 wiadomości naraz.")
        return

    deleted = await interaction.channel.purge(limit=ilosc)

    await interaction.followup.send(f"{emoji_tak} Pomyślnie usunięto **{len(deleted)}** wiadomości.")


@clear.error
async def clear_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message(
            f"{emoji_brak} Nie masz uprawnień, aby użyć tej komendy.",
            ephemeral=True
        )

@bot.tree.command(name="urlop", description="Składanie wniosku o urlop", guild=discord.Object(id=GUILD_ID))
@app_commands.default_permissions(administrator=True)
@app_commands.describe(
    na_ile="Na jaki okres czasu? (np. 3 dni, tydzień)",
    powod="Krótki powód (np. Wyjazd, Choroba)",
    uzasadnienie="Szersze wyjaśnienie wniosku",
    dowod="Opcjonalny plik/zdjęcie (np. screen)"
)
async def urlop(
        interaction: discord.Interaction,
        na_ile: str,
        powod: str,
        uzasadnienie: str,
        dowod: discord.Attachment = None
):
    target_channel = interaction.guild.get_channel(ID_KANALU_URLOPOW)
    review_channel = interaction.guild.get_channel(ID_KANALU_SPRAWDZ_URLOP)

    if not target_channel or not review_channel:
        if interaction.response.is_done():
            await interaction.followup.send("Błąd: Nie znaleziono kanału do wysyłania wniosków.", ephemeral=True)
        else:
            await interaction.response.send_message("Błąd: Nie znaleziono kanału do wysyłania wniosków.",
                                                    ephemeral=True)
        return

    embed = discord.Embed(
        title=f"{emoji_log} WNIOSEK O URLOP",
        color=discord.Color.dark_grey(),
        timestamp=interaction.created_at
    )

    embed.set_thumbnail(url=interaction.user.display_avatar.url)

    embed.add_field(name=f"{emoji_steve} Użytkownik", value=interaction.user.mention, inline=False)
    embed.add_field(name=f"{emoji_zegar} Okres trwania", value=na_ile, inline=False)
    embed.add_field(name=f"{emoji_lista} Powód", value=powod, inline=False)
    embed.add_field(name=f"{emoji_pad} Uzasadnienie", value=uzasadnienie, inline=False)

    if dowod:
        embed.add_field(name=f"{emoji_sklep} Dowód", value=f"[{dowod.filename}]({dowod.url})", inline=False)

    main_msg = await target_channel.send(embed=embed)
    await review_channel.send(embed=embed, view=UrlopButtons(main_msg_id=main_msg.id))

    if interaction.response.is_done():
        await interaction.followup.send(
            f"{emoji_tak} Twój wniosek o urlop został pomyślnie wysłany na kanał {target_channel.mention}!", ephemeral=True)
    else:
        await interaction.response.send_message(
            f"{emoji_tak} Twój wniosek o urlop został pomyślnie wysłany na kanał {target_channel.mention}!", ephemeral=True)

# ----------------------------- AUTOMOD -----------------------------

invite_pattern = re.compile(r"(discord\.gg/|discord\.com/invite/)")
ALLOWED_ROLE_ID = 1513799047842893884
MUTE_DATA_FILE = "muted_users.json"


def save_muted_users(data):
    with open(MUTE_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def load_muted_users():
    if os.path.exists(MUTE_DATA_FILE):
        try:
            with open(MUTE_DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}


@bot.event
async def on_message(message):

    if message.author.bot:
        return

    if invite_pattern.search(message.content.lower()):
        if any(role.id == ALLOWED_ROLE_ID for role in message.author.roles):
            return

        try:
            await message.delete()

            duration = timedelta(days=1)
            await message.author.timeout(duration, reason="Reklama bez pozwolenia")

            muted_data = load_muted_users()
            muted_data[str(message.author.id)] = {
                "username": str(message.author),
                "until": (discord.utils.utcnow() + duration).isoformat(),
                "reason": "Reklama bez pozwolenia",
            }
            save_muted_users(muted_data)

            embed_user = discord.Embed(
                title=f"{emoji_uwaga} Zostałeś zmutowany!",
                description=f"**Reklamowanie innych serwerów Discord {emoji_dc} jest surowo zabronione!**",
                color=discord.Color.red(),
            )
            embed_user.add_field(name="Kara", value="Mute na 24 godziny", inline=True)
            embed_user.add_field(
                name="Powód", value="Wysyłanie zaproszeń na czacie", inline=True
            )
            embed_user.set_footer(text=f"SYSTEM - ANTYREKLAM")

            try:
                await message.author.send(embed=embed_user)
            except discord.Forbidden:
                pass

            embed_chat = discord.Embed(
                title=f"{emoji_uwaga} Zostałeś zmutowany!",
                description=f"**Reklamowanie innych serwerów Discord {emoji_dc} jest surowo zabronione!**\n\n{emoji_steve} Użytkownik {message.author.mention} otrzymał wyciszenie na 1 dzien za reklamę.",
                color=discord.Color.red(),
            )
            embed_chat.add_field(
                name="Powód", value="**Wysyłanie zaproszeń na czacie**", inline=True
            )
            embed_chat.set_footer(text=f"SYSTEM - ANTYREKLAM")
            await message.channel.send(embed=embed_chat, delete_after=10.0)

            log_channel = bot.get_channel(LOGI_ADMIN_ID)
            if log_channel:
                embed_log = discord.Embed(
                    title=f"{emoji_uwaga} Logi Administracyjne | Mute za Reklame",
                    color=discord.Color.dark_red(),
                    timestamp=discord.utils.utcnow(),
                )
                embed_log.add_field(
                    name=f"{emoji_steve} Użytkownik:",
                    value=f"{message.author.mention} (`{message.author.id}`)",
                    inline=False,
                )
                embed_log.add_field(
                    name=f"{emoji_sklep} Kanał:", value=message.channel.mention, inline=False
                )
                embed_log.add_field(
                    name=f"{emoji_lista} Treść reklamy:",
                    value=f"||{message.content}||",
                    inline=False,
                )
                embed_log.add_field(
                    name=f"{emoji_zegar} Czas trwania:", value="1 dzień", inline=True
                )
                await log_channel.send(embed=embed_log)

        except discord.Forbidden:
            print(
                f"BŁĄD BRAKU UPRAWNIEŃ: Nie można usunąć wiadomości lub wyciszyć {message.author}"
            )
        except Exception as e:
            print(f"[BŁĄD BOTA]: {e}")

    await bot.process_commands(message)
# ------------------------------- KOMENDA SYNC -----------------------------------
@bot.command()
@commands.is_owner()
async def sync(ctx):
    try:
        fmt = await bot.tree.sync(guild=ctx.guild)
        await ctx.send(f"✅ Zsynchronizowano {len(fmt)} komend slash na tym serwerze.")
    except Exception as e:
        await ctx.send(f"❌ Błąd synchronizacji: {e}")

bot.run(TOKEN)