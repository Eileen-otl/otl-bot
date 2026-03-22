import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import random
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageOps

TOKEN = os.getenv("TOKEN")
GUILD_ID = 1480890046092415027

DATA_FILE = "love_data.json"
BG_PATH = "images/bg.png"
SHIP_BG = "images/ship_bg.png"
TOP_BG_FOLDER = "images/top_bg"
CRUSH_IMG = "images/crush.png"
MATCH_IMG = "images/match.png"
MATCHMAKING_BG = "images/matchmaking.png"
LOVE_GAIN_IMG = "images/love_gain.png"

CONFESSION_CHANNEL_ID = 1483584376804737137

POSITIVE_WORDS = ["love", "cute", "kiss", "heart", "adorable", "mignon", "jtm", "amour"]
NEGATIVE_WORDS = ["hate", "nul", "bizarre", "weird", "méchant", "mechant"]

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

cooldowns = {}
last_active = {}
last_context = {}

# ================= DATA =================

def load_data():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump({"users": {}}, f, indent=4, ensure_ascii=False)
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def fixed_max(user_id):
    return random.Random(str(user_id)).randint(500, 9999)


def ensure_user(data, user_id):
    uid = str(user_id)

    if uid not in data["users"]:
        data["users"][uid] = {
            "points": 0,
            "max": fixed_max(user_id),
            "given": {},
            "crush": None
        }
    else:
        if "given" not in data["users"][uid]:
            data["users"][uid]["given"] = {}

        if "crush" not in data["users"][uid]:
            data["users"][uid]["crush"] = None

        if "points" not in data["users"][uid]:
            data["users"][uid]["points"] = 0

        if "max" not in data["users"][uid]:
            data["users"][uid]["max"] = fixed_max(user_id)


def get_rank(points, maxp):
    if points == 0:
        return "Anomalie"

    r = points / maxp if maxp else 0

    if r < 0.1:
        return "Low Signal"
    if r < 0.3:
        return "Soft Aura"
    if r < 0.6:
        return "Magnetic"
    if r < 0.85:
        return "Heart Sync"
    return "Legendary"

# ================= RELATIONS =================

def get_top_lovers(data, target_id):
    lovers = []
    for uid, user in data["users"].items():
        given = user.get("given", {})
        if target_id in given:
            lovers.append((uid, given[target_id]))

    lovers.sort(key=lambda x: x[1], reverse=True)
    return lovers[:3]


def get_best_match(data, user_id):
    given = data["users"][user_id]["given"]
    if not given:
        return None
    return max(given.items(), key=lambda x: x[1])[0]


def calculate_ship(data, u1, u2):
    u1 = str(u1)
    u2 = str(u2)

    ensure_user(data, u1)
    ensure_user(data, u2)

    p1 = data["users"][u1]["points"]
    p2 = data["users"][u2]["points"]

    love1 = data["users"][u1]["given"].get(u2, 0)
    love2 = data["users"][u2]["given"].get(u1, 0)

    base = (love1 + love2) * 10
    bonus = min(p1, p2) // 50

    return min(100, base + bonus + random.randint(0, 20))

# ================= IMAGE TEXT =================

def draw_text(img, text, x, y, scale=6):
    font = ImageFont.load_default()
    bbox = font.getbbox(text)

    txt = Image.new("RGBA", (bbox[2] + 4, bbox[3] + 4), (0, 0, 0, 0))
    d = ImageDraw.Draw(txt)

    d.text((1, 1), text, font=font, fill=(255, 105, 180))
    d.text((0, 0), text, font=font, fill=(255, 255, 255))

    txt = txt.resize((txt.width * scale, txt.height * scale), Image.Resampling.NEAREST)
    img.alpha_composite(txt, (x, y))


def get_smooth_font(size):
    font_paths = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/Library/Fonts/Arial Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    ]

    for path in font_paths:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass

    return ImageFont.load_default()


def draw_centered_text(img, text, y, size=80):
    draw = ImageDraw.Draw(img)
    font = get_smooth_font(size)

    bbox = font.getbbox(text)
    text_width = bbox[2] - bbox[0]
    x = (img.width - text_width) // 2

    for dx in [-3, -2, -1, 0, 1, 2, 3]:
        for dy in [-3, -2, -1, 0, 1, 2, 3]:
            draw.text((x + dx, y + dy), text, font=font, fill=(255, 105, 180))

    draw.text((x, y), text, font=font, fill=(255, 255, 255))


def draw_smooth_text_left(img, text, x, y, size=52,
                          fill_main=(255, 255, 255),
                          fill_outline=(255, 105, 180)):
    draw = ImageDraw.Draw(img)
    font = get_smooth_font(size)

    for dx in [-3, -2, -1, 0, 1, 2, 3]:
        for dy in [-3, -2, -1, 0, 1, 2, 3]:
            draw.text((x + dx, y + dy), text, font=font, fill=fill_outline)

    draw.text((x, y), text, font=font, fill=fill_main)

# ================= PROFILE IMAGE =================

async def generate_profile(member, data, guild):
    user = data["users"][str(member.id)]

    bg = Image.open(BG_PATH).convert("RGBA").resize((900, 600))

    avatar = Image.open(BytesIO(await member.display_avatar.read())).convert("RGBA")
    avatar = ImageOps.fit(avatar, (200, 200))

    bg.alpha_composite(avatar, (152, 296))

    # points / max = style pixel plus gros
    draw_text(bg, str(user["points"]), 505, 78, scale=6)
    draw_text(bg, "/", 625, 78, scale=6)
    draw_text(bg, str(user["max"]), 690, 78, scale=6)

    # texte lisse plus gros
    draw_smooth_text_left(bg, member.display_name, 170, 120, size=82)
    draw_smooth_text_left(bg, get_rank(user["points"], user["max"]), 110, 210, size=60)

    uid = str(member.id)
    lovers = get_top_lovers(data, uid)
    best = get_best_match(data, uid)
    crush = data["users"][uid]["crush"]

    start_x = 520
    y = 260

    if best:
        duo_member = guild.get_member(int(best))
        if duo_member:
            draw_smooth_text_left(bg, f"Duo : {duo_member.display_name}", start_x, y, size=50)
            y += 58

    if crush:
        draw_smooth_text_left(bg, "Crush : ???", start_x, y, size=50)
        y += 58

    if lovers:
        draw_smooth_text_left(bg, "Interet recu :", start_x, y, size=50)
        y += 48

        for lover_id, count in lovers[:3]:
            lover_member = guild.get_member(int(lover_id))
            if lover_member:
                draw_smooth_text_left(
                    bg,
                    f"- {lover_member.display_name} ({count})",
                    start_x + 8,
                    y,
                    size=34
                )
                y += 42

    path = f"profile_{member.id}.png"
    bg.save(path)
    return path

# ================= TOPLOVE IMAGE =================

def get_random_top_background():
    if not os.path.exists(TOP_BG_FOLDER):
        return None

    files = [
        f for f in os.listdir(TOP_BG_FOLDER)
        if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))
    ]

    if not files:
        return None

    return os.path.join(TOP_BG_FOLDER, random.choice(files))


def generate_toplove_image(guild, top_users):
    bg_path = get_random_top_background()

    if bg_path:
        img = ImageOps.fit(Image.open(bg_path).convert("RGBA"), (900, 1400))
    else:
        img = Image.new("RGBA", (900, 1400), (25, 18, 30, 255))

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ov = ImageDraw.Draw(overlay)

    ov.rounded_rectangle((70, 80, 830, 1320), radius=35, fill=(20, 10, 25, 120))
    img = Image.alpha_composite(img, overlay)

    draw_centered_text(img, "TOP LOVE", 100, size=100)

    y = 260
    line_gap = 170

    for i, (uid, user_data) in enumerate(top_users, start=1):
        member = guild.get_member(int(uid))
        name = member.display_name if member else "Unknown"
        points = user_data.get("points", 0)
        maxp = user_data.get("max", 0)

        line = f"{i}. {name}"
        score_line = f"{points} / {maxp}"

        draw_centered_text(img, line, y, size=58)
        draw_centered_text(img, score_line, y + 55, size=42)

        y += line_gap
        if y > 1200:
            break

    final_path = "toplove_result.png"
    img.save(final_path)
    return final_path

# ================= EVENTS =================

@bot.event
async def on_ready():
    print("Bot prêt")
    await tree.sync(guild=discord.Object(id=GUILD_ID))


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    data = load_data()
    user_id = str(message.author.id)

    ensure_user(data, message.author.id)

    now = message.created_at.timestamp()

    # perte d'inactivité
    if user_id in last_active:
        diff = now - last_active[user_id]
        if diff > 3600:
            data["users"][user_id]["points"] = max(
                0,
                data["users"][user_id]["points"] - 2
            )

    last_active[user_id] = now

    # gain simple
    last = cooldowns.get(user_id, 0)
    if now - last > 60:
        data["users"][user_id]["points"] += 1
        cooldowns[user_id] = now

    # bonus/malus mots
    content_lower = message.content.lower()
    if any(word in content_lower for word in POSITIVE_WORDS):
        data["users"][user_id]["points"] += 1
    if any(word in content_lower for word in NEGATIVE_WORDS):
        data["users"][user_id]["points"] = max(0, data["users"][user_id]["points"] - 1)

    save_data(data)

    # drama random
    if random.random() < 0.03:
        drama_types = {
            "jalousie": [
                "💔 Quelqu’un devient jaloux...",
                "👀 L’ambiance change… quelqu’un observe trop.",
                "💭 Une tension étrange s’installe."
            ],
            "crush": [
                "💘 Quelqu’un pense à quelqu’un d’autre...",
                "💞 Une connexion se forme doucement...",
                "👁️ Des regards en disent long..."
            ]
        }

        context = random.choice(list(drama_types.keys()))
        msg = random.choice(drama_types[context])

        last_context[message.channel.id] = context
        await message.channel.send(msg)

    # réponses au bot
    if message.reference:
        try:
            referenced = await message.channel.fetch_message(message.reference.message_id)

            if referenced.author == bot.user:
                context = last_context.get(message.channel.id)

                if context == "jalousie":
                    replies = [
                        f"{message.author.mention} tu vois pas que quelqu’un supporte pas la situation ?",
                        f"{message.author.mention} c’est évident pourtant… y’a de la jalousie dans l’air.",
                        f"{message.author.mention} hm... ça te concerne peut-être plus que tu crois."
                    ]
                elif context == "crush":
                    replies = [
                        f"{message.author.mention} oh... ça parle de quelqu’un en particulier là.",
                        f"{message.author.mention} intéressant... y’a clairement un crush qui se cache.",
                        f"{message.author.mention} t’es sûr(e) que c’est juste innocent ?"
                    ]
                else:
                    replies = [
                        f"{message.author.mention} je regarde juste ce qu’il se passe.",
                        f"{message.author.mention} continue... c’est intéressant."
                    ]

                await message.reply(random.choice(replies), mention_author=False)
                return
        except Exception:
            pass

    # anomalie
    if data["users"][user_id]["points"] == 0:
        await message.channel.send(f"⚠️ {message.author.mention} est devenu une anomalie...")

    await bot.process_commands(message)

# ================= COMMANDES =================

@tree.command(name="profile", guild=discord.Object(id=GUILD_ID))
async def profile(interaction: discord.Interaction, member: discord.Member = None):
    if not member:
        member = interaction.user

    data = load_data()
    ensure_user(data, member.id)

    img = await generate_profile(member, data, interaction.guild)
    await interaction.response.send_message(file=discord.File(img))


@tree.command(name="givelove", guild=discord.Object(id=GUILD_ID))
async def givelove(interaction: discord.Interaction, member: discord.Member):
    if member.bot or member == interaction.user:
        await interaction.response.send_message("❌ impossible", ephemeral=True)
        return

    data = load_data()

    giver = str(interaction.user.id)
    target = str(member.id)

    ensure_user(data, giver)
    ensure_user(data, target)

    data["users"][target]["points"] += 1

    given = data["users"][giver]["given"]
    given[target] = given.get(target, 0) + 1

    save_data(data)

    for other_id, amount in data["users"][giver]["given"].items():
        if other_id != target and amount >= 3:
            other = interaction.guild.get_member(int(other_id))
            if other:
                await interaction.channel.send(f"💔 {other.mention} semble jaloux(se)...")
            break

    file = discord.File(LOVE_GAIN_IMG, filename="love.png")

    embed = discord.Embed(
        description=f"{interaction.user.mention} → {member.mention} 💖 +1"
    )
    embed.set_thumbnail(url="attachment://love.png")

    await interaction.response.send_message(
        embed=embed,
        file=file
    )


@tree.command(name="ship", guild=discord.Object(id=GUILD_ID))
async def ship(interaction: discord.Interaction, u1: discord.Member, u2: discord.Member):
    data = load_data()

    ensure_user(data, u1.id)
    ensure_user(data, u2.id)

    score = calculate_ship(data, u1.id, u2.id)

    bg = Image.open(SHIP_BG).convert("RGBA")

    center_y = bg.height // 2
    draw_centered_text(bg, u1.display_name, center_y - 180, size=78)
    draw_centered_text(bg, u2.display_name, center_y + 110, size=78)

    heart_size = int(120 + score * 0.5)

    heart = Image.new("RGBA", (heart_size, heart_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(heart)

    color = (255, int(100 + score), int(150 + score))

    draw.ellipse((0, 0, heart_size // 2, heart_size // 2), fill=color)
    draw.ellipse((heart_size // 2, 0, heart_size, heart_size // 2), fill=color)
    draw.polygon([
        (0, heart_size // 3),
        (heart_size, heart_size // 3),
        (heart_size // 2, heart_size)
    ], fill=color)

    bg.alpha_composite(
        heart,
        (bg.width // 2 - heart_size // 2, bg.height // 2 - heart_size // 2)
    )

    draw_centered_text(bg, f"{score}%", center_y - 20, size=52)

    path = f"ship_{u1.id}_{u2.id}.png"
    bg.save(path)

    await interaction.response.send_message(file=discord.File(path))


@tree.command(name="matchmaking", guild=discord.Object(id=GUILD_ID))
async def matchmaking(interaction: discord.Interaction):
    data = load_data()

    users = list(data["users"].keys())
    results = []

    for uid in users:
        ensure_user(data, uid)

        given = data["users"][uid].get("given", {})
        if not given:
            continue

        best = max(given.items(), key=lambda x: x[1])[0]

        if best and best != uid:
            score = calculate_ship(data, uid, best)
            results.append((uid, best, score))

    if not results:
        await interaction.response.send_message("💔 Aucun couple détecté...", ephemeral=True)
        return

    results.sort(key=lambda x: x[2], reverse=True)

    base = Image.open(MATCHMAKING_BG).convert("RGBA")
    base = ImageOps.fit(base, (900, 1400))

    overlay = Image.new("RGBA", base.size, (0, 0, 0, 90))
    base = Image.alpha_composite(base, overlay)

    draw_centered_text(base, "MATCHMAKING", 80, size=90)

    y = 250

    for uid, bid, score in results[:5]:
        u = interaction.guild.get_member(int(uid))
        b = interaction.guild.get_member(int(bid))

        if not u or not b:
            continue

        text = f"{u.display_name} ❤️ {b.display_name}"
        percent = f"{score}%"

        draw_centered_text(base, text, y, size=50)
        draw_centered_text(base, percent, y + 55, size=38)

        y += 180

    path = "matchmaking_result.png"
    base.save(path)

    await interaction.response.send_message(file=discord.File(path))


@tree.command(name="toplove", guild=discord.Object(id=GUILD_ID))
async def toplove(interaction: discord.Interaction):
    data = load_data()

    users = data.get("users", {})
    if not users:
        await interaction.response.send_message("Aucune donnée pour le classement.")
        return

    top = sorted(
        users.items(),
        key=lambda x: x[1].get("points", 0),
        reverse=True
    )[:10]

    img_path = generate_toplove_image(interaction.guild, top)
    await interaction.response.send_message(file=discord.File(img_path))


@tree.command(name="crush", guild=discord.Object(id=GUILD_ID))
async def crush(interaction: discord.Interaction, member: discord.Member):
    if member.bot or member == interaction.user:
        await interaction.response.send_message("❌ choix invalide", ephemeral=True)
        return

    data = load_data()

    uid = str(interaction.user.id)
    tid = str(member.id)

    ensure_user(data, uid)
    ensure_user(data, tid)

    data["users"][uid]["crush"] = tid

    if data["users"][tid].get("crush") == uid:
        data["users"][uid]["points"] += 10
        data["users"][tid]["points"] += 10
        save_data(data)

        base = Image.open(MATCH_IMG).convert("RGBA")
        base = ImageOps.fit(base, (900, 900))

        overlay = Image.new("RGBA", base.size, (0, 0, 0, 80))
        base = Image.alpha_composite(base, overlay)

        draw = ImageDraw.Draw(base)
        font = get_smooth_font(92)

        text = "✨ MATCH ✨"

        bbox = font.getbbox(text)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        x = (base.width - text_width) // 2
        y = (base.height - text_height) // 2

        for dx in [-3, -2, -1, 0, 1, 2, 3]:
            for dy in [-3, -2, -1, 0, 1, 2, 3]:
                draw.text((x + dx, y + dy), text, font=font, fill=(255, 105, 180))

        draw.text((x, y), text, font=font, fill=(255, 255, 255))

        path = "match_result.png"
        base.save(path)

        await interaction.response.send_message(file=discord.File(path), ephemeral=True)

    else:
        save_data(data)

        base = Image.open(CRUSH_IMG).convert("RGBA")
        base = ImageOps.fit(base, (900, 900))

        overlay = Image.new("RGBA", base.size, (0, 0, 0, 90))
        base = Image.alpha_composite(base, overlay)

        draw = ImageDraw.Draw(base)
        font = get_smooth_font(64)
        small_font = get_smooth_font(42)

        main_text = "CRUSH ENREGISTRÉ"
        sub_text = "secret 🤫"

        bbox = font.getbbox(main_text)
        text_width = bbox[2] - bbox[0]
        x = (base.width - text_width) // 2
        y = 55

        for dx in [-2, -1, 0, 1, 2]:
            for dy in [-2, -1, 0, 1, 2]:
                draw.text((x + dx, y + dy), main_text, font=font, fill=(255, 105, 180))
        draw.text((x, y), main_text, font=font, fill=(255, 255, 255))

        bbox2 = small_font.getbbox(sub_text)
        text_width2 = bbox2[2] - bbox2[0]
        x2 = (base.width - text_width2) // 2
        y2 = 135

        for dx in [-2, -1, 0, 1, 2]:
            for dy in [-2, -1, 0, 1, 2]:
                draw.text((x2 + dx, y2 + dy), sub_text, font=small_font, fill=(255, 105, 180))
        draw.text((x2, y2), sub_text, font=small_font, fill=(255, 255, 255))

        path = "crush_result.png"
        base.save(path)

        await interaction.response.send_message(file=discord.File(path), ephemeral=True)


@tree.command(name="mycrush", guild=discord.Object(id=GUILD_ID))
async def mycrush(interaction: discord.Interaction):
    data = load_data()
    uid = str(interaction.user.id)
    ensure_user(data, uid)

    crush_id = data["users"][uid].get("crush")

    if not crush_id:
        await interaction.response.send_message("💔 Aucun crush pour le moment", ephemeral=True)
        return

    member = interaction.guild.get_member(int(crush_id))
    if not member:
        await interaction.response.send_message("❓ introuvable", ephemeral=True)
        return

    await interaction.response.send_message(
        f"💘 Ton crush actuel : **{member.display_name}**",
        ephemeral=True
    )


@tree.command(name="resetcrush", guild=discord.Object(id=GUILD_ID))
async def resetcrush(interaction: discord.Interaction):
    data = load_data()
    uid = str(interaction.user.id)
    ensure_user(data, uid)

    data["users"][uid]["crush"] = None
    save_data(data)

    await interaction.response.send_message("💔 Crush supprimé", ephemeral=True)


@tree.command(name="confess", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(
    member="La personne ciblée",
    message="Ton message",
    anonyme="Envoyer anonymement ?"
)
async def confess(interaction: discord.Interaction, member: discord.Member, message: str, anonyme: bool = True):
    if member.bot or member == interaction.user:
        await interaction.response.send_message("❌ impossible", ephemeral=True)
        return

    if len(message) > 300:
        await interaction.response.send_message("❌ message trop long", ephemeral=True)
        return

    channel = bot.get_channel(CONFESSION_CHANNEL_ID)
    if channel is None:
        await interaction.response.send_message("❌ salon introuvable", ephemeral=True)
        return

    await interaction.response.send_message("💌 envoyé", ephemeral=True)

    txt = (
        f"{member.mention}\n"
        f"💌 {'anonyme' if anonyme else interaction.user.display_name} :\n"
        f"{message}"
    )

    await channel.send(txt)


@tree.command(name="guideotl", guild=discord.Object(id=GUILD_ID))
async def guideotl(interaction: discord.Interaction):
    await interaction.response.send_message(
        "💖 **SYSTÈME DE LOVE POINTS**\n\n"
        "Dans ce serveur, chaque personne possède des Love Points.\n"
        "Ils représentent l’attention, l’intérêt et la place que tu occupes ici.\n\n"
        "✨ Tu peux en gagner en parlant, en restant actif(ve) et quand quelqu’un te donne un point avec /givelove.\n\n"
        "📉 Tu peux en perdre si tu disparais trop longtemps.\n\n"
        "🧪 Si tu tombes à 0 → tu deviens une Anomalie.\n\n"
        "💞 Le bot observe aussi les relations :\n"
        "- qui donne de l’amour à qui\n"
        "- qui t’apprécie le plus\n"
        "- ton duo principal\n"
        "- les connexions les plus fortes\n\n"
        "💘 /crush permet d’enregistrer un crush secret.\n"
        "Si c’est réciproque → match.\n\n"
        "❤️ /ship calcule une compatibilité.\n"
        "🏆 /toplove affiche le classement avec fond aléatoire.\n"
        "💘 /matchmaking propose les meilleurs couples du serveur.\n"
        "💌 /confess permet d’envoyer une confession anonyme ou non.\n\n"
        "**Commandes principales :**\n"
        "/profile\n"
        "/givelove\n"
        "/ship\n"
        "/toplove\n"
        "/matchmaking\n"
        "/crush\n"
        "/mycrush\n"
        "/resetcrush\n"
        "/confess\n"
        "/guideotl"
    )

# ================= RUN =================

bot.run(TOKEN)
