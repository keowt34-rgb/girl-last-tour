import discord
from discord.ext import commands
import random, threading, json, os, time
from flask import Flask
from collections import Counter
app = Flask(__name__)
SAVE_FILE = "save.json"
players = {}
dev_mode_users = set()
DEV_IDS = [1200298327531585537]
save_lock = threading.Lock()
ITEM_EN = {
    "压缩口粮 x10": "Compressed Ration x10", "军用口粮 x10": "Military Ration x10",
    "压缩口粮 x1": "Compressed Ration x1", "土豆干 x2": "Dried Potato x2",
    "土豆干": "Dried Potato", "土豆干 x10": "Dried Potato x10", "鱼": "Fish",
    "燃料桶 x20": "Fuel Can x20", "燃料桶(半满)": "Fuel Can (Half)", "燃料桶": "Fuel Can",
    "Kettenkrad履带摩托": "Kettenkrad", "Kettenkrad浴缸": "Kettenkrad Bathtub",
    "38式步枪": "Type 38 Rifle", "手枪与一发子弹": "Pistol & 1 Bullet",
    "千户的日记": "Chito's Diary", "毛毯 x2": "Blanket x2",
    "尤莉的笑脸": "Yuri's Smile", "尤莉的歌声": "Yuri's Song", "尤莉的拥抱": "Yuri's Hug",
    "日记(千户写的)": "Diary (Chito's)", "金泽的眼镜": "Kanazawa's Glasses",
    "世界地图(残缺)": "World Map (Incomplete)", "石像爷爷的刻刀": "Statue Grandpa's Chisel",
    "小地藏雕像": "Small Jizo Statue", "飞机设计图": "Airplane Blueprint",
    "管制官的密钥": "Controller's Key", "发光的努可": "Glowing Nuko",
    "电能 x100": "Energy x100", "星空的照片": "Photo of Starry Sky", "END标记": "END Mark",
    "生锈的螺栓": "Rusty Bolt", "空罐头": "Empty Can", "旧报纸": "Old Newspaper",
    "破布": "Rag", "发光的石头": "Glowing Stone", "38式步枪子弹 x5": "Type 38 Ammo x5",
    "空弹壳": "Empty Shell", "手绘地图碎片": "Hand-drawn Map Fragment",
    "石像 x10": "Statue x10", "螺旋桨碎片": "Propeller Fragment",
    "修理工具": "Repair Tool", "旧式相机胶卷": "Old Camera Film",
    "被吃掉的子弹": "Eaten Bullet", "生锈的仪表盘": "Rusty Dashboard",
    "Kettenkrad履带摩托 x1": "Kettenkrad x1"
}
NPC_EN = {"金泽":"Kanazawa","石像爷爷":"Statue Grandpa","石井":"Ishii","管制官":"Controller","努可":"Nuko","尤莉":"Yuri","千户":"Chito","上层的幽灵":"Ghost of Upper Layer"}
def get_lang(uid): return players.get(uid, {}).get("lang","zh")
def L(uid, zh, en): return en if get_lang(uid)=="en" else zh
def I(uid, name): return ITEM_EN.get(name, name) if get_lang(uid)=="en" else name
def N(uid, name): return NPC_EN.get(name, name) if get_lang(uid)=="en" else name
FOOD_HUNGER = {"压缩口粮 x10": 100, "军用口粮 x10": 100, "压缩口粮 x1": 15, "土豆干 x2": 30, "土豆干": 15, "土豆干 x10": 75, "鱼": 65}
def save_now():
    with save_lock:
        try:
            save_data = {"players": {str(uid): {**pdata, "met_npcs": list(pdata["met_npcs"]), "ever_met": list(pdata.get("ever_met", []))} for uid, pdata in players.items()}, "dev_mode_users": list(dev_mode_users)}
            with open(SAVE_FILE, "w", encoding="utf-8") as f: json.dump(save_data, f, ensure_ascii=False, indent=2)
        except Exception as e: print(f"[SAVE] {e}")
def load_save():
    global players, dev_mode_users
    if os.path.exists(SAVE_FILE):
        try:
            with open(SAVE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for uid, pdata in data.get("players", {}).items():
                    pdata["met_npcs"] = set(pdata.get("met_npcs", ["千户","尤莉"]))
                    pdata["ever_met"] = set(pdata.get("ever_met", list(pdata["met_npcs"])))
                    pdata["npc_met_km"] = pdata.get("npc_met_km", {"千户":0,"尤莉":0})
                    pdata["fixed_done"] = pdata.get("fixed_done", [])
                    pdata["in_fixed_story"] = pdata.get("in_fixed_story", None)
                    pdata["rice_pity"] = pdata.get("rice_pity", 0)
                    pdata["lang"] = pdata.get("lang","zh")
                    pdata["name"] = pdata.get("name", f"玩家{str(uid)[-4:]}")
                    if "stats" not in pdata: pdata["stats"] = {"normal":0,"rice":0,"endless_km":0,"total_km":0}
                    players[int(uid)] = pdata
                dev_mode_users = set(data.get("dev_mode_users", []))
        except Exception as e: print(f"[LOAD] {e}")
load_save()
def format_backpack(inventory, uid=None):
    counter = Counter(inventory); seen=[]
    for i in inventory:
        if i not in seen: seen.append(i)
    if uid: lines=[f"{I(uid,name)} x{counter[name]}" if counter[name]>1 else I(uid,name) for name in seen]
    else: lines=[f"{name} x{counter[name]}" if counter[name]>1 else name for name in seen]
    return lines, counter
def get_unique_for_trade(inventory):
    seen=[]
    for i in inventory:
        if i not in seen: seen.append(i)
    return seen
def get_food_value(name): return FOOD_HUNGER.get(name, 0)
def get_fuel_value(name):
    if "燃料桶 x20" in name: return 20
    if "燃料桶(半满)" in name: return 5
    if name=="燃料桶": return 5
    return 0
def sync_item(p, item_name, add=True):
    fu = get_fuel_value(item_name)
    if fu: p["fuel"] = max(0, p["fuel"] + fu * (1 if add else -1))
@app.route("/")
def index(): return f"Kettenkrad v28.3 Final Complete | {len(players)} players"
def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
intents = discord.Intents.default()
intents.guilds = True
bot = commands.Bot(command_prefix="/", intents=intents)
def localized_command(**kwargs):
    def decorator(func):
        try:
            return bot.tree.command(**kwargs)(func)
        except TypeError:
            kwargs.pop('name_localizations', None)
            kwargs.pop('description_localizations', None)
            return bot.tree.command(**kwargs)(func)
    return decorator
SPECIAL_REWARDS = {
    "尤莉的笑脸": {"text_zh": "尤莉：嘿嘿~ 千户你看我笑得可爱吗？\n千户：...笨蛋。", "text_en": "Yuri: Hehe~ Chito, do I look cute?\nChito: ...Idiot.", "image": "https://cdn.discordapp.com/attachments/1566063305385316543/1566063444560445480/44b80e01a3f2b3cb9d0bb35479393411.jpg?ex=6ae72dbd&is=6ae5dc3d&hm=1952055c7b7135992458986cec7ad036921259df1eec0cea2d73f45eabb31deb&", "color": 0xf2c17c, "effect": "none"},
    "尤莉的歌声": {"text_zh": "尤莉：♪~ 拉拉拉~ 终末世界也要唱歌！", "text_en": "Yuri: La~ la la~ Sing even at the end!", "image": None, "color": 0xf2c17c, "effect": "none"},
    "尤莉的拥抱": {"text_zh": "尤莉：千户，好冷啊，抱一下！", "text_en": "Yuri: Chito, so cold, hug me!", "image": "https://cdn.discordapp.com/attachments/1566063305385316543/1566063444950523984/50.jpg?ex=6ae72dbd&is=6ae5dc3d&hm=564ccfec315dc229aa95b72a6e6ae6843d7c9f2c3fd487bac166f8454e6042b1&", "color": 0xf2c17c, "effect": "none"},
    "日记(千户写的)": {"text_zh": "千户的日记：今天尤莉又把枪弄丢了...", "text_en": "Chito's diary: Yuri lost the gun again today...", "image": None, "color": 0x8b9a7d, "effect": "none"},
    "金泽的眼镜": {"text_zh": "金泽：没有这个我看不清地图了...", "text_en": "Kanazawa: Can't see map without this...", "image": None, "color": 0x87ceeb, "effect": "none"},
    "世界地图(残缺)": {"text_zh": "金泽：这地图我画了半辈子...", "text_en": "Kanazawa: I drew this map for half my life...", "image": None, "color": 0x87ceeb, "effect": "none"},
    "石像爷爷的刻刀": {"text_zh": "石像爷爷：用这个刻，能刻得更久。", "text_en": "Grandpa: With this you can carve longer.", "image": None, "color": 0xa9a9a9, "effect": "none"},
    "小地藏雕像": {"text_zh": "石像爷爷：保佑你们的旅途。", "text_en": "Grandpa: Bless your journey.", "image": None, "color": 0xa9a9a9, "effect": "none"},
    "飞机设计图": {"text_zh": "石井：这架飞机本来想去上层的...", "text_en": "Ishii: This plane wanted to go to upper layer...", "image": None, "color": 0xdeb887, "effect": "none"},
    "管制官的密钥": {"text_zh": "管制官：密钥已移交...工厂将永远运行。", "text_en": "Controller: Key transferred... Factory will run forever.", "image": None, "color": 0xff4444, "effect": "none"},
    "发光的努可": {"text_zh": "努可把子弹吃掉了，全身发光...", "text_en": "Nuko ate bullet and glows...", "image": None, "color": 0xffffff, "effect": "fuel_full"},
    "电能 x100": {"text_zh": "努可：努可！ (释放100电能)", "text_en": "Nuko: Nuko! (Release 100 energy)", "image": None, "color": 0xffffff, "effect": "fuel+100"},
    "星空的照片": {"text_zh": "……嗯。\n千户：...好美。\n—— 终末的星空", "text_en": "……Yeah.\nChito: ...Beautiful.\n—— Starry sky at the end", "image": "https://cdn.discordapp.com/attachments/1566063305385316543/1566063444128698511/135.jpg.webp?ex=6ae72dbd&is=6ae5dc3d&hm=141fc406da127cff7264dfadf290388b4ac6fb54304d12037ada87125cea9489&", "color": 0x000000, "effect": "END"},
    "END标记": {"text_zh": "上面什么都没有了。", "text_en": "There is nothing above.", "image": "https://cdn.discordapp.com/attachments/1566063305385316543/1566063445772865556/Screenshot_20261028_203421.jpg?ex=6ae72dbd&is=6ae5dc3d&hm=4b9b076070d2ceb2a3b891e326991ff7d92d96aac9797c3ebc14ffd903b6f7a8&", "color": 0x000000, "effect": "END"},
}
NPC_DIALOGUE = {
    "金泽": {"zh": "金泽：哦...又是旅人吗？", "en": "Kanazawa: Oh... another traveler?"},
    "石像爷爷": {"zh": "石像爷爷：你们要去上层？", "en": "Statue Grandpa: You want to go to upper layer?"},
    "石井": {"zh": "石井：我的飞机...本来想飞到上层去的", "en": "Ishii: My plane... wanted to fly to upper layer"},
    "管制官": {"zh": "管制官：...你们不是工厂的人吧？", "en": "Controller: ...You're not factory workers?"},
    "努可": {"zh": "努可：努可！\n尤莉：哇！白白的！好可爱！", "en": "Nuko: Nuko!\nYuri: Wow! White! So cute!"},
}
ALL_NPCS = {"金泽": {"color": 0x87ceeb, "km_need": 150},"石像爷爷": {"color": 0xa9a9a9, "km_need": 450},"石井": {"color": 0xdeb887, "km_need": 900},"管制官": {"color": 0xff4444, "km_need": 1500},"努可": {"color": 0xffffff, "km_need": 2100},"尤莉": {"color": 0xf2c17c, "km_need": 0},"千户": {"color": 0x8b9a7d, "km_need": 0},"上层的幽灵": {"color": 0x000000, "km_need": 3000},}
DROP_TABLE = {"尤莉": [("尤莉的笑脸", 5), ("尤莉的歌声", 15), ("尤莉的拥抱", 10), ("空弹壳", 70)],"千户": [("日记(千户写的)", 30), ("修理工具", 20), ("旧式相机胶卷", 50)],"金泽": [("世界地图(残缺)", 20), ("手绘地图碎片", 50), ("金泽的眼镜", 30)],"石像爷爷": [("小地藏雕像", 40), ("石像 x10", 30), ("石像爷爷的刻刀", 30)],"石井": [("飞机设计图", 15), ("土豆干", 50), ("螺旋桨碎片", 35)],"管制官": [("燃料桶 x20", 40), ("军用口粮 x10", 40), ("管制官的密钥", 20)],"努可": [("发光的努可", 20), ("电能 x100", 50), ("被吃掉的子弹", 30)],"上层的幽灵": [("星空的照片", 50), ("END标记", 50)],}
RANDOM_LOOT = [("生锈的螺栓", 15, "尤莉：这是什么？能吃吗？\n千户：不能", "Yuri: What is this? Can eat?\nChito: No"),("空罐头", 15, "尤莉：空的...", "Yuri: Empty..."),("旧报纸", 10, "千户：...几百年前的新闻了", "Chito: ...News from hundreds years ago"),("破布", 8, "尤莉：破的...", "Yuri: Torn..."),("发光的石头", 2, "尤莉：哇！会发光！", "Yuri: Wow! Glows!"),("38式步枪子弹 x5", 7, "尤莉：子弹！", "Yuri: Bullets!"),]
ALL_ITEMS_POOL = list(set(list(FOOD_HUNGER.keys()) + ["燃料桶 x20","燃料桶(半满)","生锈的螺栓","空罐头","旧报纸","破布","发光的石头","38式步枪子弹 x5","空弹壳","手绘地图碎片","世界地图(残缺)","金泽的眼镜","小地藏雕像","石像 x10","石像爷爷的刻刀","飞机设计图","螺旋桨碎片","管制官的密钥","日记(千户写的)","修理工具","旧式相机胶卷","尤莉的笑脸","尤莉的歌声","尤莉的拥抱","发光的努可","电能 x100","星空的照片","END标记"]))
FIXED_STORIES = {
    "fish": {"type": "km", "at": 85, "title_zh": "📍 大型水坝", "title_en": "📍 Giant Dam",
        "pages_zh": ["他们从寒冷的仓库出来后遇到了巨型水坝\n\n尤莉：是水坝耶！\n千户：我知道啦，那些水是融化掉了的雪水....我们下去看看，尤莉。\n尤莉：好！","于是他们从旁边的楼梯走了下去\n\n尤莉：千户，我们下去是干嘛的。\n千户：看水坝啊。\n尤莉：就单单看水坝吗？\n千户：不可能只是单单看水坝啦...","他们走到了楼梯口后，脱掉了鞋子前往水域\n\n千户：好冷...\n尤莉：我也是...啊秋!","尤莉：千户你看！天空好蔚蓝耶！\n千户：嗯？\n千户：确实很蓝...这天气我们要不洗衣服吧。\n尤莉：诶？要洗衣服吗？","他们换上了另一套服并绑绳子在各自的腰上防止被水冲走\n\n尤莉：千户干嘛要绑绳子啦。\n千户：防止被水冲走啊。\n尤莉：好吧...","过了20分钟后尤莉看到了一条鱼，于是不顾千户的警告去抓了那条鱼\n\n尤莉：千户你看！是鱼耶！\n千户：干嘛去抓鱼啦...这很危险啦。不过在这个末日环境下竟然还有生物，真是奇迹。\n尤莉：千户要不我们把它烤来吃吧。\n千户：好主意！","于是他们烤了鱼后并吃了下去\n\n尤莉：千户，你尝尝。很好吃！\n千户：给我我试看。\n千户：嗯~ 味道确实不错但有点怪\n—— 饥饿度+65%","吃饱喝足后他们就躺在石头上享受风吹来的感觉\n\n千户：啊，爽了。\n尤莉：是啊。","简单收拾了后他们就继续上路了"],
        "pages_en": ["They came out of cold warehouse and saw giant dam\n\nYuri: It's a dam!\nChito: I know, melted snow... Let's go down, Yuri.\nYuri: Okay!","They went down stairs next to it\n\nYuri: Chito what are we going down for?\nChito: To see dam.\nYuri: Just to see dam?\nChito: Can't be just that...","They reached stairs, took off shoes to water\n\nChito: So cold...\nYuri: Me too... Achoo!","Yuri: Chito look! Sky so blue!\nChito: Huh?\nChito: Really blue... Should we wash clothes?\nYuri: Eh? Wash clothes?","They changed clothes and tied rope to not be washed away\n\nYuri: Why tie rope?\nChito: To not be washed away.\nYuri: Okay...","After 20 mins Yuri saw fish and ignored warning to catch it\n\nYuri: Chito look! Fish!\nChito: Why catch fish... dangerous. But life in apocalypse, miracle.\nYuri: Let's grill it.\nChito: Good idea!","They grilled and ate fish\n\nYuri: Taste it, yummy!\nChito: Let me try.\nChito: Hmm~ good but weird\n—— Hunger +65%","Full, they lay on rocks enjoying wind\n\nChito: Ah, refreshed.\nYuri: Yeah.","After packing they continued"],
        "images": {}},
    "soup": {"type": "step", "at": 6, "title_zh": "📍 夜光下的热汤", "title_en": "📍 Soup Under Starlight",
        "pages_zh": ["尤莉：肚子好饿...千户，难得出来我们喝口汤吧。\n千户：好啦，就当作是纪念我们出来了\n尤莉：太棒了！","于是他们在附近暂时居住喝口汤\n\n尤莉：千户可以喝了吗？\n千户：不行，还没煮好\n尤莉：好吧","过了几分钟后...\n\n尤莉：千户，好了！\n千户：知道啦。\n千户为自己跟尤莉倒了杯汤\n\n尤莉：啊，好好喝！\n千户：嗯~\n过后他们简单收拾了后就继续上路了\n\n—— 饥饿度+40%"],
        "pages_en": ["Yuri: So hungry... Chito let's have soup.\nChito: Okay as memory\nYuri: Awesome!","So they settled to have soup\n\nYuri: Can drink?\nChito: Not cooked yet\nYuri: Okay","After few mins...\n\nYuri: Ready!\nChito: I know.\nChito poured soup\n\nYuri: So good!\nChito: Yeah~\nAfter packing they continued\n\n—— Hunger +40%"],
        "images": { 
            2:"https://cdn.discordapp.com/attachments/1566063305385316543/1566063446976499882/Screenshot_20261029_215528_com.android.chrome_edit_193623155043371.jpg?ex=6ae72dbd&is=6ae5dc3d&hm=e48f3dae7d96102ddce73b8f2d4373e5d0d1d8f4568e971c016017401fdd3893&"
        }
    },
    "hotspring": {"type": "km", "at": 70, "title_zh": "📍 暴风雪中的温泉", "title_en": "📍 Hot Spring in Blizzard","pages_zh": ["雪越来越大了，什么都看不见只有一个巨大的工厂。\n\n他们走进去后，四周只有巨大的管道在风里嘎吱响，Kettenkrad的车灯是唯一的光。\n能见度不到5米。\n\n尤莉：千户...好冷...\n千户：再坚持一下！","千户：等一下...那个水管有热气？\n尤莉：诶？真的耶！\n\n那根水管上面竟然没有雪，顺着蒸汽找过去，废弃的管道上...居然有水声。\n尤莉：是温泉！是温泉啊千户！\n千户：真的是热水...想要洗个澡。\n尤莉：你等我一下，看我拿枪射爆那个水管。\n\n砰的一声，水管爆开了，千户赶紧驾Kettenkrad拉来了一个废弃水管","两个人把Kettenkrad停好，脱掉厚重的军大衣。\n\n千户：呜啊~ 活过来了~\n尤莉：千户你脸好红~\n千户：是...是被热气熏的啦！\n雪还在外面下，这里却暖和得像梦一样。","过后他们在工厂里面找了一个地方生火休息\n千户就提到了日记...\n\n尤莉：千户，这是什么来的。\n千户：这是日记，日记可以拿来记起我们会遗忘的东西，像你这种人应该更需要这个东西\n尤莉：哦。\n千户：火要没了，填一下火。\n尤莉：ok。","尤莉：那个千户，我可以拿一本来看吗。\n随后千户拿了一本书给尤莉\n千户：拿去吧\n尤莉：ok。","过了几分钟后...\n\n千户：尤莉，火要燃尽了，加一下燃料。\n尤莉：ok。\n随后尤莉就把千户的一本日记丢了下去","千户：等下！我的日记！\n\n千户赶紧把被烧了一半的日记出来\n\n千户：尤莉！\n尤莉：对不起千户，我不是故意的。\n千户：baka kuzi gomni！(笨蛋，废物，垃圾！)\n随后千户就生气的跑去睡觉了\n尤莉看到千户真的生气了，随后拿了千户的其中一本日记并涂鸦了","明天一早，千户醒来就看到尤莉的涂鸦画作\n\n千户：尤莉，这是不是你涂鸦的。\n尤莉：我不知道啊。\n千户：唉，不过还蛮怪可爱的"],
        "pages_en": ["Snow heavier, only huge factory visible.\n\nInside, only pipes creaking, Kettenkrad light only light.\nVisibility <5m.\n\nYuri: Chito... so cold...\nChito: Hold on!","Chito: Wait... that pipe has steam?\nYuri: Really!\n\nThat pipe has no snow, following steam... water sound.\nYuri: Hot spring! Hot spring Chito!\nChito: Really hot water... want bath.\nYuri: Wait let me shoot pipe.\n\nBang, pipe exploded, Chito drove Kettenkrad to bring pipe","They parked Kettenkrad, took off coats.\n\nChito: Wooo~ alive again~\nYuri: Chito your face red~\nChito: It's steam!\nSnow outside, warm like dream inside.","After they found place to make fire\nChito mentioned diary...\n\nYuri: Chito what is this.\nChito: Diary to remember things we forget, someone like you needs it more\nYuri: Oh.\nChito: Fire dying, add fuel.\nYuri: ok.","Yuri: Chito can I take one to read.\nChito gave book\nChito: Here\nYuri: ok.","After few mins...\n\nChito: Yuri fire dying add fuel.\nYuri: ok.\nThen Yuri threw Chito's diary in","Chito: Wait! My diary!\n\nChito took out half-burned diary\n\nChito: Yuri!\nYuri: Sorry Chito, not meant.\nChito: baka kuzi gomni! (Idiot, trash!)\nThen Chito went sleep angry\nYuri saw Chito angry, then took diary and doodled","Next morning Chito woke saw doodle\n\nChito: Yuri did you doodle?\nYuri: I don't know.\nChito: Sigh, kinda cute though"],
        "images": {}}
}
def roll(npc):
    table = DROP_TABLE.get(npc, [("垃圾", 100)]); r=random.randint(1,100); cur=0
    for item,p in table:
        cur+=p
        if r<=cur: return item
    return table[-1][0]
def get_player(user_id):
    if user_id not in players:
        players[user_id] = {"km": 0, "hunger": 100, "fuel": 28, "step": 0,"visited_airplane": False, "ended": False,"bike_scrapped": False, "bath_to_delete": False,"endless": False, "pause_until": 0,"met_npcs": set(["千户","尤莉"]),"ever_met": set(["千户","尤莉"]),"npc_met_km": {"千户":0,"尤莉":0},"inventory": ["Kettenkrad履带摩托","38式步枪","手枪与一发子弹","千户的日记","毛毯 x2","土豆干 x2","压缩口粮 x1"],"fixed_done": [], "in_fixed_story": None, "rice_pity": 0, "lang": "zh","stats": {"normal":0,"rice":0,"endless_km":0,"total_km":0}}
    p = players[user_id]
    if "stats" not in p: p["stats"] = {"normal":0,"rice":0,"endless_km":0,"total_km":0}
    if "rice_pity" not in p: p["rice_pity"] = 0
    if "fixed_done" not in p: p["fixed_done"] = []
    if "in_fixed_story" not in p: p["in_fixed_story"] = None
    if "lang" not in p: p["lang"] = "zh"
    return p
def is_paused(p): return time.time() < p.get("pause_until",0)
class FoodUseSelect(discord.ui.Select):
    def __init__(self, user_id, inventory):
        self.user_id = user_id; foods = [i for i in inventory if get_food_value(i) > 0]; unique=[]
        for f in foods:
            if f not in unique: unique.append(f)
        if not unique: options=[discord.SelectOption(label=L(user_id,"没有食物","No food"), value="none")]
        else:
            _, counter = format_backpack(inventory); options=[]
            for item in unique[:25]:
                add=get_food_value(item); cnt=counter[item]; label=f"{I(user_id,item)} (+{add}%)"+(f" x{cnt}" if cnt>1 else "")
                options.append(discord.SelectOption(label=label[:100], value=item, description=L(user_id,f"恢复 {add}% 饥饿度",f"Restore {add}% hunger")))
        super().__init__(placeholder=L(user_id,"🍙 选择食物使用","🍙 Select food"), min_values=1, max_values=1, options=options)
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(L(self.user_id,"❌ 不是你的背包","❌ Not your backpack"), ephemeral=True); return
        if self.values[0]=="none":
            await interaction.response.send_message(L(self.user_id,"❌ 没有食物","❌ No food"), ephemeral=True); return
        item_name=self.values[0]; p=get_player(self.user_id)
        if item_name not in p["inventory"]:
            await interaction.response.send_message(L(self.user_id,"❌ 食物已不在背包","❌ Food gone"), ephemeral=True); return
        add=get_food_value(item_name); p["inventory"].remove(item_name); p["hunger"]=min(100,p["hunger"]+add); save_now()
        embed=discord.Embed(title=f"{p['km']}km {L(self.user_id,'背包','Backpack')} - {p['hunger']}%", color=0x8b9a7d)
        await interaction.response.edit_message(embed=embed, view=WalkView(self.user_id))
class FixedStoryView(discord.ui.View):
    def __init__(self, user_id, story_id, page=0):
        super().__init__(timeout=None); self.user_id=user_id; self.story_id=story_id; self.page=page; self.children[0].label=L(user_id,"▶️ 下一步","▶️ Next")
    @discord.ui.button(label="▶️ 下一步", style=discord.ButtonStyle.primary)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(L(self.user_id,"❌ 不是你的旅途","❌ Not your journey"), ephemeral=True); return
        p=get_player(self.user_id); story=FIXED_STORIES[self.story_id]; lang=get_lang(self.user_id); self.page+=1
        if self.page>=len(story[f"pages_{lang}"]):
            if self.story_id not in p["fixed_done"]:
                p["fixed_done"].append(self.story_id)
                if self.story_id=="fish": p["inventory"].append("鱼"); p["hunger"]=min(100,p["hunger"]+65)
                elif self.story_id=="soup": p["hunger"]=min(100,p["hunger"]+40)
            p["in_fixed_story"]=None; save_now()
            await interaction.response.edit_message(embed=discord.Embed(title=f"{story[f'title_{lang}']} - End", description=L(self.user_id,"继续前进...","Continue..."), color=0x8b9a7d), view=WalkView(self.user_id)); return
        embed=discord.Embed(title=f"{story[f'title_{lang}']} [{self.page+1}/{len(story[f'pages_{lang}'])}]", description=story[f"pages_{lang}"][self.page], color=0x8b9a7d)
        if "images" in story and self.page in story["images"]: embed.set_image(url=story["images"][self.page])
        await interaction.response.edit_message(embed=embed, view=FixedStoryView(self.user_id, self.story_id, self.page))
class WalkView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=None); self.user_id=user_id; p=get_player(user_id); self.add_item(FoodUseSelect(user_id, p["inventory"]))
    @discord.ui.button(label="继续步行 (-5%饥饿)", style=discord.ButtonStyle.primary, emoji="🚶")
    async def continue_walk(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(L(self.user_id,"❌ 不是你的旅途","❌ Not your journey"), ephemeral=True); return
        p=get_player(interaction.user.id)
        if is_paused(p):
            left=int(p["pause_until"]-time.time()); await interaction.response.send_message(L(self.user_id,f"⏸️ 暂停中，还剩 {left}秒",f"⏸️ Paused, {left}s left"), ephemeral=True); return
        await interaction.response.defer(); await do_walk_logic(interaction)
    @discord.ui.button(label="暂停前进", style=discord.ButtonStyle.secondary, emoji="⏸️")
    async def pause_walk(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id: return
        p=get_player(interaction.user.id); p["pause_until"]=time.time()+300; save_now()
        await interaction.response.edit_message(embed=discord.Embed(title=L(self.user_id,"⏸️ 已暂停前进 5分钟","⏸️ Paused for 5 minutes"), color=0x555555), view=ResumeView(self.user_id))
class ResumeView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=None); self.user_id=user_id; p=get_player(user_id); self.add_item(FoodUseSelect(user_id, p["inventory"])); self.children[0].label=L(user_id,"恢复前进","Resume")
    @discord.ui.button(label="恢复前进", style=discord.ButtonStyle.success, emoji="▶️")
    async def resume(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id: return
        p=get_player(interaction.user.id); p["pause_until"]=0; save_now()
        await interaction.response.edit_message(embed=discord.Embed(title=L(self.user_id,"▶️ 已恢复","▶️ Resumed"), color=0x8b9a7d), view=WalkView(self.user_id))
class EndlessConfirmView(discord.ui.View):
    def __init__(self, user_id, to_endless: bool):
        super().__init__(timeout=60); self.user_id=user_id; self.to_endless=to_endless; self.children[0].label=L(user_id,"确定","Confirm")
    @discord.ui.button(label="确定", style=discord.ButtonStyle.danger, emoji="⚠️")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id: return
        old=get_player(interaction.user.id); old_pity=old.get("rice_pity",0); old_stats=old.get("stats", {"normal":0,"rice":0,"endless_km":0,"total_km":0}); lang=old.get("lang","zh"); old_name=old.get("name","")
        if self.to_endless:
            players[interaction.user.id]={"km": 0, "hunger": 100, "fuel": 38, "step": 0,"visited_airplane": False, "ended": False,"bike_scrapped": False, "bath_to_delete": False,"endless": True, "pause_until":0,"met_npcs": set(["千户","尤莉","金泽","石像爷爷","石井","管制官","努可"]),"ever_met": set(["千户","尤莉","金泽","石像爷爷","石井","管制官","努可"]),"npc_met_km": {"千户":0,"尤莉":0},"inventory": ["Kettenkrad履带摩托","38式步枪","手枪与一发子弹","毛毯 x2"],"fixed_done": [], "in_fixed_story": None,"rice_pity": old_pity, "stats": old_stats, "lang": lang, "name": old_name}
        else:
            players[interaction.user.id]={"km": 0, "hunger": 100, "fuel": 28, "step": 0,"visited_airplane": False, "ended": False,"bike_scrapped": False, "bath_to_delete": False,"endless": False, "pause_until":0,"met_npcs": set(["千户","尤莉"]),"ever_met": set(["千户","尤莉"]),"npc_met_km": {"千户":0,"尤莉":0},"inventory": ["Kettenkrad履带摩托","38式步枪","手枪与一发子弹","千户的日记","毛毯 x2","土豆干 x2","压缩口粮 x1"],"fixed_done": [], "in_fixed_story": None,"rice_pity": old_pity, "stats": old_stats, "lang": lang, "name": old_name}
        save_now(); await interaction.response.edit_message(embed=discord.Embed(title=L(self.user_id,"已切换","Switched"), color=0x00ffaa), view=None)
class RestartView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=None); self.user_id=user_id; self.children[0].label=L(user_id,"重新开始","Restart")
    @discord.ui.button(label="重新开始", style=discord.ButtonStyle.primary, emoji="🔄")
    async def restart(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id: return
        old=get_player(interaction.user.id); old_pity=old.get("rice_pity",0); old_stats=old.get("stats", {"normal":0,"rice":0,"endless_km":0,"total_km":0}); lang=old.get("lang","zh"); old_name=old.get("name","")
        players[interaction.user.id]={"km": 0, "hunger": 100, "fuel": 28, "step": 0,"visited_airplane": False, "ended": False,"bike_scrapped": False, "bath_to_delete": False,"endless": False, "pause_until":0,"met_npcs": set(["千户","尤莉"]),"ever_met": set(["千户","尤莉"]),"npc_met_km": {"千户":0,"尤莉":0},"inventory": ["Kettenkrad履带摩托","38式步枪","手枪与一发子弹","千户的日记","毛毯 x2","土豆干 x2","压缩口粮 x1"],"fixed_done": [], "in_fixed_story": None,"rice_pity": old_pity, "stats": old_stats, "lang": lang, "name": old_name}
        save_now(); await interaction.response.edit_message(embed=discord.Embed(title=L(self.user_id,"🔄 重新开始","🔄 Restart"), color=0x8b9a7d), view=None)
class TradeView(discord.ui.View):
    def __init__(self, from_id, to_id=None, npc_name=None, inventory=None):
        super().__init__(timeout=120); self.from_id=from_id; self.to_id=to_id; self.npc_name=npc_name; self.offer=None; inv=inventory or []
        if inv:
            _, counter=format_backpack(inv); unique=get_unique_for_trade(inv)
            opts=[discord.SelectOption(label=f"{I(from_id,item)} (x{counter[item]})"[:100] if counter[item]>1 else I(from_id,item)[:100], value=f"{idx}|{item}") for idx, item in enumerate(unique[:25])]
            self.select_give=discord.ui.Select(placeholder=L(from_id,f"选择物品 共{len(inv)}件",f"Select item Total {len(inv)}"), min_values=1, max_values=1, options=opts); self.select_give.callback=self.select_callback; self.add_item(self.select_give)
    async def select_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.from_id: return
        _, item_name=self.select_give.values[0].split("|",1); self.offer=item_name
        await interaction.response.send_message(L(self.from_id,f"已选择：**{item_name}**",f"Selected: **{I(self.from_id,item_name)}**"), ephemeral=True)
    @discord.ui.button(label="确认交易", style=discord.ButtonStyle.success, emoji="🤝")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.from_id: return
        if not self.offer:
            await interaction.response.send_message(L(self.from_id,"❌ 请先选物品","❌ Select item first"), ephemeral=True); return
        p=get_player(self.from_id)
        if self.offer not in p["inventory"]:
            await interaction.response.send_message(L(self.from_id,"❌ 物品不在了","❌ Item gone"), ephemeral=True); return
        sync_item(p, self.offer, add=False)
        if self.npc_name:
            reward=roll(self.npc_name); p["inventory"].remove(self.offer); p["inventory"].append(reward); sync_item(p, reward, add=True)
            sp=SPECIAL_REWARDS.get(reward)
            if sp:
                if sp["effect"]=="fuel_full": p["fuel"]=999
                if sp["effect"]=="fuel+100": p["fuel"]+=100
                if sp["effect"]=="END": p["ended"]=True
            lang=get_lang(self.from_id); txt=sp[f"text_{lang}"] if sp else ""
            emb=discord.Embed(title=f"✨ {I(self.from_id,reward)}", description=f"{txt}\n\n{I(self.from_id,self.offer)} -> {I(self.from_id,reward)}", color=sp["color"] if sp else ALL_NPCS[self.npc_name]["color"])
            if sp and sp.get("image"): emb.set_image(url=sp["image"])
            save_now(); await interaction.response.edit_message(embed=emb, view=TradeView(self.from_id, to_id=self.to_id, npc_name=self.npc_name, inventory=p["inventory"]))
        else:
            target=get_player(self.to_id); target["inventory"].append(self.offer); sync_item(target, self.offer, add=True); p["inventory"].remove(self.offer); save_now()
            await interaction.response.edit_message(embed=discord.Embed(title=L(self.from_id,"交易完成","Trade Done"), description=f"{I(self.from_id,self.offer)}"), view=TradeView(self.from_id, to_id=self.to_id, npc_name=self.npc_name, inventory=p["inventory"]))
    @discord.ui.button(label="重新交易", style=discord.ButtonStyle.secondary, emoji="🔄")
    async def retrade(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.from_id: return
        p=get_player(self.from_id)
        await interaction.response.edit_message(embed=discord.Embed(title=L(self.from_id,f"与 {N(self.from_id,self.npc_name) if self.npc_name else '玩家'} 交易",f"Trade with {N(self.from_id,self.npc_name) if self.npc_name else 'Player'}")), view=TradeView(self.from_id, to_id=self.to_id, npc_name=self.npc_name, inventory=p["inventory"]))
class GiveView(discord.ui.View):
    def __init__(self, user_id, inventory):
        super().__init__(timeout=120); self.user_id=user_id; self.offer=None; unique=get_unique_for_trade(inventory)
        opts=[discord.SelectOption(label=I(user_id,item)[:100], value=f"{idx}|{item}") for idx, item in enumerate(unique[:25])]
        self.select_give=discord.ui.Select(placeholder=L(user_id,"选择要给予的物品","Select item to give"), min_values=1, max_values=1, options=opts); self.select_give.callback=self.select_callback; self.add_item(self.select_give)
    async def select_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id: return
        _, item_name=self.select_give.values[0].split("|",1); self.offer=item_name
        await interaction.response.send_message(L(self.user_id,f"已选择：**{item_name}**",f"Selected: **{I(self.user_id,item_name)}**"), ephemeral=True)
    @discord.ui.button(label="确认给予", style=discord.ButtonStyle.success, emoji="🎁")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id: return
        if not self.offer:
            await interaction.response.send_message(L(self.user_id,"❌ 请先选物品","❌ Select first"), ephemeral=True); return
        p=get_player(self.user_id); p["inventory"].append(self.offer); sync_item(p, self.offer, add=True); save_now()
        await interaction.response.edit_message(embed=discord.Embed(title="DEV给予成功", description=f"已获得 {I(self.user_id,self.offer)}", color=0xffd700), view=None)
class LanguageView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=None); self.user_id=user_id
    @discord.ui.button(label="🇨🇳 华文", style=discord.ButtonStyle.primary, custom_id="lang_zh")
    async def zh_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id: return
        get_player(self.user_id)["lang"]="zh"; save_now()
        await interaction.response.edit_message(embed=discord.Embed(title="已切换为华文", color=0x8b9a7d), view=None)
    @discord.ui.button(label="🇺🇸 English", style=discord.ButtonStyle.secondary, custom_id="lang_en")
    async def en_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id: return
        get_player(self.user_id)["lang"]="en"; save_now()
        await interaction.response.edit_message(embed=discord.Embed(title="Switched to English", color=0x8b9a7d), view=None)
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"v28.3 Final Complete | {len(bot.guilds)} guilds")

async def do_walk_logic(interaction):
    data = get_player(interaction.user.id); data["name"] = interaction.user.display_name; is_dev_now = interaction.user.id in dev_mode_users; is_endless = data.get("endless", False); prev_km = data["km"]; uid = interaction.user.id
    if data.get("in_fixed_story"):
        story_id = data["in_fixed_story"]; story = FIXED_STORIES.get(story_id)
        if story:
            lang=get_lang(uid); embed=discord.Embed(title=f"{story[f'title_{lang}']} - {L(uid,'剧情进行中','Story in progress')}", description=L(uid,"⚠️ 剧情还没看完，不能继续步行！","⚠️ Story not finished!"), color=0xff4444)
            await interaction.followup.send(embed=embed, view=FixedStoryView(uid, story_id, 0)); return
        else: data["in_fixed_story"]=None
    if data.get("ended") and not is_endless:
        embed=discord.Embed(title=L(uid,"—— 3000km，终点","—— 3000km, The End"), description=L(uid,"......嗯。\n\n千户：我们现在这样，是正确的吗？\n尤莉：我们现在是世界上最幸福的人。\n—— 少女终末旅行 完","......Yeah."), color=0x000000)
        await interaction.followup.send(embed=embed, view=RestartView(uid)); return
    if not is_endless:
        expired=[]
        for npc_name in list(data["met_npcs"]):
            if npc_name in ["千户","尤莉"]: continue
            if data["km"] - data["npc_met_km"].get(npc_name, 0) > 15:
                data["met_npcs"].discard(npc_name); expired.append(npc_name)
        if expired and random.random() < 0.3:
            save_now(); left_text = L(uid,"离开了","left")
            await interaction.followup.send(embed=discord.Embed(title=f"{N(uid,expired[0])} {left_text}", color=0x555555), view=WalkView(uid)); return
    data["step"]+=1; has_bike=any(i in ["Kettenkrad履带摩托", "Kettenkrad履带摩托 x1"] for i in data["inventory"])
    if data["step"] == 5 and not is_endless:
        save_now()
        embed=discord.Embed(title=L(uid,"📍 看到了夜晚的月光","📍 Moonlight at night"), description=L(uid,"尤莉：哇！是星空耶！\n千户：嗯！\n尤莉：快看那个星星！","Yuri: Wow! Starry sky!\nChito: Yeah!\nYuri: Look at that star!"), color=0x8b9a7d)
        embed.set_image(url="https://cdn.discordapp.com/attachments/1519326691095478272/1565373186659328020/Screenshot_20261029_215400_com.android.chrome_edit_193629864750661.jpg?ex=6ae4aae2&is=6ae35962&hm=9ec2dd36a7f71b4441e19652001fb6827ba9ea8d667913e1f034ca10b3518e55&")
        await interaction.followup.send(embed=embed, view=WalkView(uid)); return
    if data.get("bath_to_delete", False) and not is_endless:
        data["bath_to_delete"]=False
        for i in range(len(data["inventory"])-1, -1, -1):
            if "Kettenkrad浴缸" in data["inventory"][i]:
                del data["inventory"][i]; break
        save_now(); await interaction.followup.send(embed=discord.Embed(title=L(uid,"留在2550km","Left at 2550km"), description=L(uid,"Kettenkrad浴缸留在了原地","Kettenkrad bathtub left behind"), color=0x555555), view=WalkView(uid)); return
    if is_endless: move=random.randint(1, 2) if (not has_bike or data["fuel"] <= 0) else random.randint(4, 7); data["km"]+=move
    else:
        if not has_bike: move=random.randint(1, 3) if data.get("bike_scrapped") else random.randint(1, 2)
        elif data["fuel"] <= 0: move=random.randint(1, 2)
        else: move=random.randint(3, 6)
        data["km"]+=move
    if "stats" not in data: data["stats"]={"normal":0,"rice":0,"endless_km":0,"total_km":0}
    data["stats"]["total_km"]+=move
    if is_endless: data["stats"]["endless_km"]+=move
    prev_step=data["step"]-1
    for story_id, story in FIXED_STORIES.items():
        if story_id in data.get("fixed_done", []): continue
        triggered=False
        if story.get("type")=="step":
            if prev_step < story["at"] <= data["step"]: triggered=True
        else:
            if prev_km < story["at"] <= data["km"]: triggered=True
        if triggered:
            data["in_fixed_story"]=story_id; lang=get_lang(uid)
            embed=discord.Embed(title=f"{story[f'title_{lang}']} [1/{len(story[f'pages_{lang}'])}]", description=story[f"pages_{lang}"][0], color=0x8b9a7d)
            if "images" in story and 0 in story["images"]: embed.set_image(url=story["images"][0])
            await interaction.followup.send(embed=embed, view=FixedStoryView(uid, story_id, 0)); save_now(); return
    if data["step"] <= 4:
        walked_zh = f"目前走了 {data['step']} 步 / {data['km']}km\n四周很安静，还没有遇到什么事。"
        walked_en = f"Walked {data['step']} steps / {data['km']}km\nQuiet around, nothing yet."
        embed=discord.Embed(title=L(uid,"🚶‍♀️ 继续前进...","🚶‍♀️ Continue..."), description=L(uid,walked_zh,walked_en), color=0x8b9a7d)
        await interaction.followup.send(embed=embed, view=WalkView(uid)); save_now(); return
    if data["step"] == 11 and not data["visited_airplane"] and not is_endless:
        data["visited_airplane"]=True; data["inventory"].extend(["压缩口粮 x10", "生锈的仪表盘"]); save_now()
        embed=discord.Embed(title=L(uid,"📍 发现报废战斗机","📍 Found scrapped fighter"), description=L(uid,"尤莉：是飞机耶！\n千户：那是战斗机\n尤莉：诶...他还能飞吗\n千户：已经不能了....走，我们进去看有没有粮食\n获得：压缩口粮 x10 (+100%)","Yuri: It's a plane!\nChito: It's a fighter\nYuri: Can it still fly?\nChito: No... Let's see if there's food\nGot: Compressed Ration x10 (+100%)"), color=0x8b9a7d)
        embed.set_image(url="https://cdn.discordapp.com/attachments/1519326691095478272/1565001787013079181/Screenshot_20261028_215740.jpg?ex=6ae4a27e&is=6ae350fe&hm=132eeaa5e705c08425bc46743d5d843ada7fc3b882a2a06a4904b097c6ec8cdc&")
        await interaction.followup.send(embed=embed, view=WalkView(uid)); return
    if not is_dev_now:
        if data["step"] > 10: data["hunger"]=max(0,data["hunger"]-5)
        if data["fuel"] > 0: data["fuel"]=max(0,data["fuel"]-1)
        if data["hunger"] <= 0:
            old_pity=data.get("rice_pity",0); old_stats=data.get("stats", {"normal":0,"rice":0,"endless_km":0,"total_km":0}); old_lang=data.get("lang","zh"); old_name=data.get("name","")
            players[interaction.user.id]={"km": 0, "hunger": 100, "fuel": 38 if is_endless else 28, "step": 0,"visited_airplane": False, "ended": False,"bike_scrapped": False, "bath_to_delete": False,"endless": is_endless, "pause_until":0,"met_npcs": set(["千户","尤莉","金泽","石像爷爷","石井","管制官","努可"]) if is_endless else set(["千户","尤莉"]),"ever_met": set(["千户","尤莉","金泽","石像爷爷","石井","管制官","努可"]) if is_endless else set(["千户","尤莉"]),"npc_met_km": {"千户":0,"尤莉":0},"inventory": ["Kettenkrad履带摩托","38式步枪","手枪与一发子弹","毛毯 x2"] if is_endless else ["Kettenkrad履带摩托","38式步枪","手枪与一发子弹","千户的日记","毛毯 x2","土豆干 x2","压缩口粮 x1"],"fixed_done": [], "in_fixed_story": None,"rice_pity": old_pity, "stats": old_stats, "lang": old_lang, "name": old_name}
            save_now(); await interaction.followup.send(embed=discord.Embed(title=L(uid,"💀 饿死了...","💀 Starved..."), description=L(uid,f"饥饿度0%倒下... 已重置 饥饿100% / 0km","Starved... Reset to 100% / 0km"), color=0x000000), view=WalkView(uid)); return
    if not is_endless and prev_km < 1650 <= data["km"]:
        save_now()
        embed=discord.Embed(title=L(uid,"⚠️ 进入中层 - 1650km","⚠️ Enter middle layer - 1650km"), description=L(uid,"你已进入中层，接下来食物与燃料不会频繁出现了\n\n千户：从这里开始...要省着点了。\n尤莉：诶...那我的零食呢？","You entered middle layer, food and fuel will be rarer\n\nChito: From here... we need to save.\nYuri: Eh... what about my snacks?"), color=0xff8800)
        await interaction.followup.send(embed=embed, view=WalkView(uid)); return
    if not is_endless and prev_km < 2250 <= data["km"]:
        save_now()
        embed=discord.Embed(title=L(uid,"☠️ 进入上层 - 2250km","☠️ Enter upper layer - 2250km"), description=L(uid,"你已进入上层了，接下来将不会再生成食物与燃料了\n\n千户：...上层什么都没有了。\n尤莉：千户，好冷...","You entered upper layer, no more food and fuel will spawn\n\nChito: ...There is nothing in upper layer anymore.\nYuri: Chito, so cold..."), color=0x111111)
        await interaction.followup.send(embed=embed, view=WalkView(uid)); return
    if not is_endless and not data.get("bike_scrapped", False) and prev_km < 2550 <= data["km"]:
        data["bike_scrapped"]=True; data["bath_to_delete"]=True
        for i in range(len(data["inventory"])-1, -1, -1):
            if ("Kettenkrad" in data["inventory"][i] or "履带摩托" in data["inventory"][i]) and "浴缸" not in data["inventory"][i]:
                del data["inventory"][i]; break
        data["inventory"].append("Kettenkrad浴缸"); save_now()
        zh_desc = "嘎吱...碎。\n\n千户：...不动了。\n尤莉：修一下就好了吧？\n千户：...履带断了，引擎也烧死了。修不了了。\n尤莉：...\n\n千户：它陪我们走了2550km啊...\n尤莉：一直以为...它会陪我们到上层的...\n\n沉默了很久。\n\n尤莉：千户...我们把它当浴缸吧。\n尤莉：这样...它还能再陪我们一下。\n千户：嗯。\n\n热水倒进Kettenkrad的车斗里。\n呜啊——\n\n尤莉：最后的热水澡啊...\n千户：明明这么暖和...为什么有点想哭。\n\n—— Kettenkrad报废了\n获得：Kettenkrad浴缸\n下一次步行后，浴缸会留在原地。"
        en_desc = "Creak... crack. Broken.\n\nChito: ...Not moving.\nYuri: Can we fix it?\nChito: ...Tracks broken, engine burned out. Can't fix.\nYuri: ...\n\nChito: It walked 2550km with us...\nYuri: I always thought... it would go to the upper layer with us...\n\nLong silence.\n\nYuri: Chito... let's make it a bathtub.\nYuri: Then... it can stay with us a little longer.\nChito: Yeah.\n\nHot water poured into Kettenkrad's cargo bed.\nWoooaa—\n\nYuri: Last hot bath...\nChito: It's so warm... why do I want to cry.\n\n—— Kettenkrad scrapped\nGot: Kettenkrad Bathtub\nNext walk, bathtub will be left behind."
        embed=discord.Embed(title=L(uid,"💥 Kettenkrad 报废 - 2550km","💥 Kettenkrad scrapped - 2550km"), description=L(uid, zh_desc, en_desc), color=0x555555)
        embed.set_image(url="https://cdn.discordapp.com/attachments/1519326691095478272/1565030660282912889/082.jpg.webp?ex=6ae414a2&is=6ae2c322&hm=e31e3f5b77f36334ba75bec96e4e0fa23c0c1057623cb57ee1cf688810f93622&")
        await interaction.followup.send(embed=embed, view=WalkView(uid)); return
    if not is_endless and data["km"] >= 3000 and not data["ended"]:
        pity=data.get("rice_pity",0); chance=0.01+(pity*0.01); is_hit=random.random()<chance or pity>=99
        if is_hit:
            data["km"]=3000; data["ended"]=True; data["rice_pity"]=0; data["stats"]["rice"]+=1; data["stats"]["normal"]+=1; save_now()
            zh_rice = f"尤莉：千户！这里是......?\n千户：诶？稻田？\n\n在望不到头的稻田上，还有一个正方形的石头\n不是无尽的虚无，也没有寒冷的雪，取而代替的是一个由大量稻米组成的稻田\n\n千户：竟然是...稻米！太好了！\n尤莉：千户，我们是不是有吃不完的食物了\n千户：嗯，是的....\n\n—— 1% 隐藏结局触发 (保底 {pity+1}/100)\n\n(注意：这个隐藏结局是游戏作者自己加入的，跟原作毫无相关。)"
            en_rice = f"Yuri: Chito! What is here...?\nChito: Eh? Rice field?\n\nEndless rice field with square stone\nNot endless void, not cold snow, but field of rice\n\nChito: It's... rice! Great!\nYuri: Do we have endless food now?\nChito: Yeah....\n\n—— 1% Hidden ending triggered (Pity {pity+1}/100)\n\n(Note: This ending is fan-made, not canon.)"
            embed=discord.Embed(title=L(uid,"—— 3000km，隐藏结局 - 稻田","—— 3000km, Hidden Ending - Rice Field"), description=L(uid, zh_rice, en_rice), color=0xFFD700)
            embed.set_image(url="https://cdn.discordapp.com/attachments/1561003741052797019/1565650419374358558/images_30.jpg?ex=6ae5ad14&is=6ae45b94&hm=68483345fb91a55aa7877d2bbef814a2145e9e12f7d6837a9cac603f50782881&")
            await interaction.followup.send(embed=embed, view=RestartView(uid)); return
        else:
            data["rice_pity"]=pity+1; data["km"]=3000; data["ended"]=True; data["stats"]["normal"]+=1; save_now()
            embed=discord.Embed(title=L(uid,"—— 3000km，虚无的上层","—— 3000km, Void upper layer"), description=L(uid,"......嗯。\n\n千户：我们现在这样，是正确的吗？\n尤莉：我们现在是世界上最幸福的人。\n—— 少女终末旅行 完","......Yeah.\n\nChito: Are we doing the right thing?\nYuri: We are the happiest people in the world.\n—— Girls' Last Tour END"), color=0x000000)
            embed.set_image(url="https://cdn.discordapp.com/attachments/1519326691095478272/1564967119534432256/images_32.jpg?ex=6ae52af4&is=6ae3d974&hm=56d64ddcd4c31ce90adc48d6e4e6262e7f3d260c3c3de1902bab22fc6df15dc5&")
            await interaction.followup.send(embed=embed, view=RestartView(uid)); return
    if is_endless:
        last_150=(prev_km//150)*150; curr_150=(data["km"]//150)*150
        if curr_150>last_150 and curr_150>0:
            hunger_l = L(uid,'饥饿','Hunger'); fuel_l = L(uid,'燃料','Fuel')
            save_now(); await interaction.followup.send(embed=discord.Embed(title=f"♾️ {L(uid,'无尽','Endless')} {curr_150}km", description=f"{hunger_l}{data['hunger']}% {fuel_l}{data['fuel']} +{move}km", color=0x00ffaa), view=WalkView(uid)); return
    if not is_endless:
        force_met=[]
        for name, nd in ALL_NPCS.items():
            if name in ["上层的幽灵","千户","尤莉"]: continue
            if name not in data["met_npcs"] and name not in data.get("ever_met", set()) and data["km"] >= nd["km_need"]:
                data["met_npcs"].add(name); data["ever_met"].add(name); data["npc_met_km"][name]=data["km"]; force_met.append(name)
        if force_met:
            name=force_met[0]; save_now(); lang=get_lang(uid)
            trade_zh = f"\n15km内可 /交易 {name}"; trade_en = f"\n/trade {N(uid,name)} within 15km"
            title_zh = f"📍 遇到了 {name} - {data['km']}km"; title_en = f"📍 Met {N(uid,name)} - {data['km']}km"
            await interaction.followup.send(embed=discord.Embed(title=L(uid,title_zh,title_en), description=NPC_DIALOGUE.get(name,{}).get(lang,"") + L(uid,trade_zh,trade_en), color=ALL_NPCS[name]["color"]), view=WalkView(uid)); return
    if data["km"] < 1650: roll_type=random.choices(["空空", "食物", "杂物"], weights=[30, 45, 25])[0]
    else: roll_type=random.choices(["空空", "食物", "杂物"], weights=[45, 35, 20])[0]
    if roll_type == "空空":
        save_now(); empty_zh = random.choice(["什么都没有...","风声..."]); empty_en = random.choice(["Nothing...","Wind..."])
        hunger_l = L(uid,'饥饿','Hunger'); fuel_l = L(uid,'燃料','Fuel')
        embed=discord.Embed(title=L(uid,"空空","Empty"), description=L(uid,empty_zh,empty_en), color=0x555555)
        embed.set_author(name=f"{'♾️' if is_endless else ''}{data['km']}km | {hunger_l}{data['hunger']}% {fuel_l}{data['fuel']} +{move}km")
        await interaction.followup.send(embed=embed, view=WalkView(uid)); return
    if roll_type == "食物":
        if data["km"] >= 2250 and not is_dev_now and not is_endless:
            save_now(); await interaction.followup.send(embed=discord.Embed(title=L(uid,"空空","Empty"), description=L(uid,"上层什么都没有...","Nothing in upper layer..."), color=0x555555), view=WalkView(uid)); return
        food_item=random.choice(["压缩口粮 x1", "土豆干 x2", "压缩口粮 x10", "军用口粮 x10"]) if random.random() < 0.6 else random.choice(["燃料桶(半满)", "燃料桶 x20"])
        data["inventory"].append(food_item)
        if get_fuel_value(food_item): data["fuel"]+=get_fuel_value(food_item)
        save_now(); is_food = get_food_value(food_item) > 0; title_text = L(uid, "🍙 找到食物！" if is_food else "⛽ 找到燃料！", "🍙 Found food!" if is_food else "⛽ Found fuel!")
        hunger_l = L(uid,'饥饿','Hunger'); fuel_l = L(uid,'燃料','Fuel'); got_l = L(uid,'获得','Got')
        embed=discord.Embed(title=title_text, description=f"{got_l} {I(uid,food_item)}\n{hunger_l}{data['hunger']}% {fuel_l}{data['fuel']}", color=0x8b9a7d)
        embed.set_author(name=f"{'♾️' if is_endless else ''}{data['km']}km | {hunger_l}{data['hunger']}% {fuel_l}{data['fuel']} +{move}km")
        await interaction.followup.send(embed=embed, view=WalkView(uid)); return
    if roll_type == "杂物":
        item, weight, dialogue_zh, dialogue_en = random.choice(RANDOM_LOOT)
        data["inventory"].append(item); save_now(); lang=get_lang(uid); dialogue=dialogue_en if lang=="en" else dialogue_zh
        hunger_l = L(uid,'饥饿','Hunger'); fuel_l = L(uid,'燃料','Fuel'); got_l = L(uid,'获得','Got')
        embed=discord.Embed(title=L(uid,"🔧 找到杂物","🔧 Found junk"), description=f"{got_l} {I(uid,item)}\n\n{dialogue}", color=0x666666)
        embed.set_author(name=f"{'♾️' if is_endless else ''}{data['km']}km | {hunger_l}{data['hunger']}% {fuel_l}{data['fuel']} +{move}km")
        await interaction.followup.send(embed=embed, view=WalkView(uid)); return

@localized_command(name="dev", description="Dev mode [Owner only]", name_localizations={"zh-CN": "开发者", "zh-TW": "開發者"}, description_localizations={"zh-CN": "开发者模式[仅限]", "zh-TW": "開發者模式[僅限]"})
async def dev_cmd(interaction: discord.Interaction):
    if interaction.user.id not in DEV_IDS:
        await interaction.response.send_message(L(interaction.user.id,"❌ 不是开发者","❌ Not dev"), ephemeral=True); return
    p=get_player(interaction.user.id)
    if interaction.user.id in dev_mode_users:
        dev_mode_users.remove(interaction.user.id)
        await interaction.response.send_message(embed=discord.Embed(title=L(interaction.user.id,"DEV 已关闭","DEV OFF"), color=0xff0000))
    else:
        dev_mode_users.add(interaction.user.id)
        for k in ALL_NPCS.keys():
            p["met_npcs"].add(k); p["ever_met"].add(k); p["npc_met_km"][k]=p["km"]
        await interaction.response.send_message(embed=discord.Embed(title=L(interaction.user.id,"DEV 已开启","DEV ON"), color=0xffd700))
    save_now()
@localized_command(name="jump", description="Jump to km [Dev]", name_localizations={"zh-CN": "跳跃", "zh-TW": "跳躍"}, description_localizations={"zh-CN": "跳跃到指定公里[开发者]", "zh-TW": "跳躍到指定公里[開發者]"})
async def jump_cmd(interaction: discord.Interaction, km: int):
    if interaction.user.id not in dev_mode_users:
        await interaction.response.send_message(L(interaction.user.id,"❌ 需先 /开发者","❌ Need /dev"), ephemeral=True); return
    d=get_player(interaction.user.id); d["km"]=km; d["step"]+=1; save_now()
    await interaction.response.send_message(embed=discord.Embed(title="DEV跳跃", description=f"{L(interaction.user.id,'已到','Now at')} {km}km", color=0xffd700))
@localized_command(name="give", description="Give item [Dev]", name_localizations={"zh-CN": "给予", "zh-TW": "給予"}, description_localizations={"zh-CN": "给予物品[开发者]", "zh-TW": "給予物品[開發者]"})
async def give_cmd(interaction: discord.Interaction):
    if interaction.user.id not in dev_mode_users:
        await interaction.response.send_message(L(interaction.user.id,"❌ 需先 /开发者","❌ Need /dev"), ephemeral=True); return
    await interaction.response.send_message(embed=discord.Embed(title=L(interaction.user.id,"DEV给予","DEV Give")), view=GiveView(interaction.user.id, inventory=ALL_ITEMS_POOL), ephemeral=True)
@localized_command(name="endless", description="Enter endless mode", name_localizations={"zh-CN": "无尽模式", "zh-TW": "無盡模式"}, description_localizations={"zh-CN": "进入无尽模式", "zh-TW": "進入無盡模式"})
async def endless_cmd(interaction: discord.Interaction):
    d = get_player(interaction.user.id)
    if not d.get("endless", False):
        await interaction.response.send_message(embed=discord.Embed(title=L(interaction.user.id,"♾️ 开启无尽模式？","♾️ Enable endless?"), description=L(interaction.user.id,"⚠️ 普通进度会消失","⚠️ Normal progress will be lost"), color=0xff8800), view=EndlessConfirmView(interaction.user.id, True), ephemeral=True)
    else:
        await interaction.response.send_message(embed=discord.Embed(title=L(interaction.user.id,"返回普通模式？","Return to normal?"), description=L(interaction.user.id,"⚠️ 无尽进度会消失","⚠️ Endless progress lost"), color=0xff8800), view=EndlessConfirmView(interaction.user.id, False), ephemeral=True)
@localized_command(name="language", description="Switch language", name_localizations={"zh-CN": "语言", "zh-TW": "語言"}, description_localizations={"zh-CN": "切换语言", "zh-TW": "切換語言"})
async def language_cmd(interaction: discord.Interaction):
    await interaction.response.send_message(embed=discord.Embed(title="🌐 选择语言 / Choose Language", description=L(interaction.user.id,"点击下方按钮切换","Click button below")), view=LanguageView(interaction.user.id), ephemeral=True)
@localized_command(name="walk", description="Walk 3000km to upper layer", name_localizations={"zh-CN": "步行", "zh-TW": "步行"}, description_localizations={"zh-CN": "步行3000km到上层", "zh-TW": "步行3000km到上層"})
async def walk_cmd(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=False)
    await do_walk_logic(interaction)
@localized_command(name="backpack", description="Check your backpack", name_localizations={"zh-CN": "背包", "zh-TW": "背包"}, description_localizations={"zh-CN": "查看背包", "zh-TW": "查看背包"})
async def backpack_cmd(interaction: discord.Interaction):
    d=get_player(interaction.user.id)
    lines, _=format_backpack(d["inventory"], interaction.user.id)
    text="\n".join(lines) if lines else L(interaction.user.id,"空空如也","Empty")
    embed=discord.Embed(title=f"{'♾️ ' if d.get('endless') else ''}{d['km']}km {L(interaction.user.id,'背包','Backpack')} - {d['hunger']}% {d['fuel']}", description=text, color=0x8b9a7d)
    await interaction.response.send_message(embed=embed, view=WalkView(interaction.user.id))
@localized_command(name="trade", description="Trade items with NPC", name_localizations={"zh-CN": "交易", "zh-TW": "交易"}, description_localizations={"zh-CN": "与NPC交易物品", "zh-TW": "與NPC交易物品"})
@discord.app_commands.choices(npc=[discord.app_commands.Choice(name=NPC_EN.get(k,k), value=k) for k in ALL_NPCS.keys()])
async def trade_cmd(interaction: discord.Interaction, 用户: discord.Member=None, npc: str=None):
    await interaction.response.defer(ephemeral=True)
    d=get_player(interaction.user.id)
    if npc:
        if interaction.user.id not in dev_mode_users and npc not in d["met_npcs"]:
            await interaction.followup.send(L(interaction.user.id,f"❌ 还没遇到 {npc}",f"❌ Haven't met {N(interaction.user.id,npc)} yet"), ephemeral=True); return
        view=TradeView(interaction.user.id, npc_name=npc, inventory=d["inventory"])
        await interaction.followup.send(embed=discord.Embed(title=L(interaction.user.id,f"与 {N(interaction.user.id,npc)} 交易",f"Trade with {N(interaction.user.id,npc)}")), view=view, ephemeral=True)
    else:
        if not 用户:
            await interaction.followup.send(L(interaction.user.id,"❌ 请@玩家或选NPC","❌ Mention player or select NPC"), ephemeral=True); return
        view=TradeView(interaction.user.id, to_id=用户.id, inventory=d["inventory"])
        await interaction.followup.send(embed=discord.Embed(title=L(interaction.user.id,f"与 {用户.display_name} 交易",f"Trade with {用户.display_name}")), view=view, ephemeral=True)
@localized_command(name="leaderboard", description="Show distance leaderboard", name_localizations={"zh-CN": "排行榜", "zh-TW": "排行榜"}, description_localizations={"zh-CN": "显示距离排行榜", "zh-TW": "顯示距離排行榜"})
async def leaderboard_cmd(interaction: discord.Interaction):
    await interaction.response.defer()
    if not players:
        await interaction.followup.send(L(interaction.user.id,"还没人开始旅行呢...","No one started journey yet...")); return
    sorted_list=sorted(players.items(), key=lambda x: (x[1].get("stats", {}).get("normal", 0), x[1].get("stats", {}).get("total_km", 0)), reverse=True)
    lang=get_lang(interaction.user.id)
    title="🏆 终末之旅 排行榜" if lang=="zh" else "🏆 Last Tour Leaderboard"
    embed=discord.Embed(title=title, color=0xFFD700)
    text=""
    for rank, (uid, pdata) in enumerate(sorted_list[:10], 1):
        s=pdata.get("stats", {"normal":0,"rice":0,"endless_km":0,"total_km":0})
        name=pdata.get("name", f"玩家{str(uid)[-4:]}")
        icon="🥇" if rank==1 else "🥈" if rank==2 else "🥉" if rank==3 else f"`{rank}.`"
        if lang=="en": text+=f"{icon} **{name}**\n> Clear {s.get('normal',0)} | Hidden {s.get('rice',0)} | Endless {s.get('endless_km',0)}km\n\n"
        else: text+=f"{icon} **{name}**\n> 通关 {s.get('normal',0)} | 隐藏 {s.get('rice',0)} | 无尽 {s.get('endless_km',0)}km\n\n"
    embed.description=text
    await interaction.followup.send(embed=embed)
if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    TOKEN = os.environ.get("DISCORD_TOKEN")
    bot.run(TOKEN)
