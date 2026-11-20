"""Firestore-backed inventory tools for KonbiniSensei."""

import os
from google.cloud import firestore

# Explicitly hardcoded GCP project ID as required:
# Do NOT read from google.auth.default() or GOOGLE_CLOUD_PROJECT
PROJECT_ID = "qwiklabs-gcp-03-35246614a316"
COLLECTION_NAME = "konbini_items"

_db = None


def get_firestore_client() -> firestore.Client:
    """Return initialized Firestore client with hardcoded project ID."""
    global _db
    if _db is None:
        _db = firestore.Client(project=PROJECT_ID)
    return _db


def list_shop_items(category: str = "") -> str:
    """List items available in the Japanese convenience store.

    Args:
        category: Optional category filter, e.g. 'food', 'drink', 'daily', 'dessert'.
                  Leave empty to view all items.

    Returns:
        A formatted string describing the available items with kanji, kana, price, and stock.
    """
    db = get_firestore_client()
    collection_ref = db.collection(COLLECTION_NAME)

    docs = list(collection_ref.stream())
    if not docs:
        return "いらっしゃいませ！現在、商品はまだ並んでいません。（商品棚が空です）"

    items = [d.to_dict() for d in docs]
    if category:
        category_clean = category.strip().lower()
        items = [i for i in items if i.get("category", "").lower() == category_clean]
        if not items:
            return f"申し訳ありません。カテゴリー「{category}」の商品は現在ありません。"

    lines = ["【コンビニ商品棚 (商品一覧)】"]
    for item in items:
        lines.append(
            f"・{item.get('name_kanji')}（{item.get('name_kana')}）: ¥{item.get('price_jpy')} "
            f"[在庫: {item.get('stock')}個] - {item.get('description', '')}"
        )
    return "\n".join(lines)


def get_item_details(item_name: str) -> str:
    """Get detailed information about a specific shop item by name or ID.

    Args:
        item_name: The name (kanji, kana, or English) or ID of the item.

    Returns:
        Details about the item including price, description, and remaining stock.
    """
    db = get_firestore_client()
    collection_ref = db.collection(COLLECTION_NAME)

    target = item_name.strip().lower()
    docs = list(collection_ref.stream())

    for d in docs:
        item = d.to_dict()
        if (
            target == d.id.lower()
            or target in item.get("name_kanji", "").lower()
            or target in item.get("name_kana", "").lower()
            or target in item.get("english_name", "").lower()
        ):
            return (
                f"商品名: {item.get('name_kanji')}（{item.get('name_kana')}）\n"
                f"価格: ¥{item.get('price_jpy')}（税込目安: ¥{int(item.get('price_jpy', 0) * 1.08)}）\n"
                f"カテゴリー: {item.get('category')}\n"
                f"在庫: {item.get('stock')}個\n"
                f"説明: {item.get('description', '')}"
            )

    return f"申し訳ありません。「{item_name}」は見つかりませんでした。別の商品をお探しですか？"


def purchase_item(item_name: str, quantity: int = 1) -> str:
    """Purchase a specified quantity of an item, decrementing its stock in Firestore.

    Args:
        item_name: Name (kanji/kana/english) or ID of the item to buy.
        quantity: Number of items to buy (default is 1).

    Returns:
        A purchase receipt confirming the transaction, total price, and remaining stock.
    """
    if quantity <= 0:
        return "購入個数は1個以上を指定してください。"

    db = get_firestore_client()
    collection_ref = db.collection(COLLECTION_NAME)

    target = item_name.strip().lower()
    docs = list(collection_ref.stream())

    target_doc = None
    target_data = None
    for d in docs:
        item = d.to_dict()
        if (
            target == d.id.lower()
            or target in item.get("name_kanji", "").lower()
            or target in item.get("name_kana", "").lower()
            or target in item.get("english_name", "").lower()
        ):
            target_doc = d
            target_data = item
            break

    if not target_doc:
        return f"申し訳ありません。「{item_name}」という商品は見つかりませんでした。"

    current_stock = target_data.get("stock", 0)
    if current_stock < quantity:
        return (
            f"大変申し訳ありません！「{target_data.get('name_kanji')}」の在庫は残り{current_stock}個しかありません。"
            f"（ご希望: {quantity}個）"
        )

    new_stock = current_stock - quantity
    doc_ref = collection_ref.document(target_doc.id)
    doc_ref.update({"stock": new_stock})

    unit_price = target_data.get("price_jpy", 0)
    total_price = unit_price * quantity

    return (
        f"【お買い上げありがとうございます！】\n"
        f"・商品: {target_data.get('name_kanji')}（{target_data.get('name_kana')}）\n"
        f"・数量: {quantity}個\n"
        f"・単価: ¥{unit_price}\n"
        f"・合計金額: ¥{total_price}\n"
        f"・残り在庫: {new_stock}個\n"
        f"店員: 『ありがとうございました！またお越しくださいませ！』"
    )


def restock_item(item_name: str, quantity: int = 5) -> str:
    """Restock an item by adding more quantity to Firestore.

    Args:
        item_name: Name or ID of the item to restock.
        quantity: Amount of stock to add (default is 5).

    Returns:
        Confirmation message with the new total stock.
    """
    if quantity <= 0:
        return "補充個数は1個以上を指定してください。"

    db = get_firestore_client()
    collection_ref = db.collection(COLLECTION_NAME)

    target = item_name.strip().lower()
    docs = list(collection_ref.stream())

    target_doc = None
    target_data = None
    for d in docs:
        item = d.to_dict()
        if (
            target == d.id.lower()
            or target in item.get("name_kanji", "").lower()
            or target in item.get("name_kana", "").lower()
            or target in item.get("english_name", "").lower()
        ):
            target_doc = d
            target_data = item
            break

    if not target_doc:
        return f"「{item_name}」は見つかりませんでした。"

    current_stock = target_data.get("stock", 0)
    new_stock = current_stock + quantity
    collection_ref.document(target_doc.id).update({"stock": new_stock})

    return f"【補充完了】{target_data.get('name_kanji')} を {quantity}個 補充しました。（新在庫: {new_stock}個）"

# ==========================================
# 提案 2: 超商集點卡與單字學習紀錄 (User Profile & Points)
# ==========================================
USER_LEARNING_COLLECTION = "user_learning_records"


def get_learning_profile(user_id: str = "current_user") -> str:
    """Retrieve user's Konbini points, learned vocabulary, and mastered grammar points from Firestore.

    Args:
        user_id: The user identifier (defaults to 'current_user').

    Returns:
        Formatted summary of the user's loyalty points, backpack items, and study history.
    """
    db = get_firestore_client()
    doc_ref = db.collection(USER_LEARNING_COLLECTION).document(user_id)
    doc = doc_ref.get()

    if not doc.exists:
        # Initialize default user profile
        default_profile = {
            "user_id": user_id,
            "points": 50,  # 50 welcome points
            "learned_vocab": ["いらっしゃいませ", "おにぎり", "お茶"],
            "learned_grammar": ["〜ましょうか", "〜ています"],
            "backpack": ["鮭おにぎり"],
        }
        doc_ref.set(default_profile)
        data = default_profile
    else:
        data = doc.to_dict()

    vocab_str = "、".join(data.get("learned_vocab", [])) or "なし"
    grammar_str = "、".join(data.get("learned_grammar", [])) or "なし"
    backpack_str = "、".join(data.get("backpack", [])) or "空っぽ"

    return (
        f"【🏪 コンビニ会員証＆学習手帳（{user_id}）】\n"
        f"・累計ポイント: {data.get('points', 0)} pt (Ponta / dポイント)\n"
        f"・カバンの中身（持ち物）: {backpack_str}\n"
        f"・マスターした単語: {vocab_str}\n"
        f"・学習済みJ3文法: {grammar_str}\n"
        f"店員: 『いつもご利用ありがとうございます！ポイントが貯まっていますよ！』"
    )


def update_points_and_learning_log(
    user_id: str = "current_user",
    points_to_add: int = 10,
    vocab_word: str = "",
    grammar_pattern: str = "",
    item_bought: str = "",
) -> str:
    """Award loyalty points and record newly practiced vocabulary or J3 grammar in Firestore.

    Args:
        user_id: User identifier.
        points_to_add: Number of loyalty points to award (e.g. 10 per purchase/correct sentence).
        vocab_word: Optional Japanese vocabulary word practiced (e.g. '温める', '傘').
        grammar_pattern: Optional J3 grammar pattern practiced (e.g. '〜てもらえませんか', '〜ので').
        item_bought: Optional item purchased to add to user's backpack.

    Returns:
        Confirmation message of points awarded and progress saved.
    """
    db = get_firestore_client()
    doc_ref = db.collection(USER_LEARNING_COLLECTION).document(user_id)
    doc = doc_ref.get()

    if not doc.exists:
        data = {
            "user_id": user_id,
            "points": 0,
            "learned_vocab": [],
            "learned_grammar": [],
            "backpack": [],
        }
    else:
        data = doc.to_dict()

    new_points = data.get("points", 0) + max(0, points_to_add)
    learned_vocab = list(set(data.get("learned_vocab", [])))
    learned_grammar = list(set(data.get("learned_grammar", [])))
    backpack = list(data.get("backpack", []))

    added_items = []
    if vocab_word and vocab_word not in learned_vocab:
        learned_vocab.append(vocab_word)
        added_items.append(f"新単語『{vocab_word}』")
    if grammar_pattern and grammar_pattern not in learned_grammar:
        learned_grammar.append(grammar_pattern)
        added_items.append(f"新文法『{grammar_pattern}』")
    if item_bought:
        backpack.append(item_bought)
        added_items.append(f"持ち物『{item_bought}』")

    doc_ref.set(
        {
            "user_id": user_id,
            "points": new_points,
            "learned_vocab": learned_vocab,
            "learned_grammar": learned_grammar,
            "backpack": backpack,
        }
    )

    badge_msg = f"（{', '.join(added_items)} を記録しました！）" if added_items else ""
    return (
        f"【ポイント付与完了】\n"
        f"+{points_to_add} pt 付与しました！現在ポイント: {new_points} pt {badge_msg}\n"
        f"店員: 『ポイントカードをお返ししますね！勉強もお買い物もお見事です！』"
    )


# ==========================================
# 提案 3: J3 句型精準拆解與假名注音器
# ==========================================
J3_GRAMMAR_PATTERNS = [
    {
        "pattern": "〜ています / 〜ている",
        "keywords": ["ています", "てい", "ている", "知っています", "住んでいます", "働いています", "つけています", "着ています", "はいています", "かけています", "しています"],
        "name": "動詞ています（狀態、著裝、習慣、居住、認識）",
        "explanation": "表示動作後的狀態持續、長期狀態（如住處、職業），或是身上的穿戴打扮（著裝動詞：着る、はく、かける、つける、する）。",
        "examples": ["私は腕時計をつけています。（我戴著手錶。）", "山田さんはスーツを着ている人です。（山田先生是穿著西裝的那位。）"],
    },
    {
        "pattern": "動詞普通形＋名詞 / 連體修飾",
        "keywords": ["る人", "た人", "る映画", "た映画", "る店", "た店", "るもの", "たもの"],
        "name": "動詞普通形＋名詞（日文關係子句/連體修飾）",
        "explanation": "日語中用動詞的普通形（辭書形、た形、ない形、なかった形）直接放在名詞前面，作為形容詞般的修飾句。",
        "examples": ["明日見る映画は２時からです。（明天要看的電影是兩點開始。）", "昨日会った人です。（那是昨天見過的人。）"],
    },
    {
        "pattern": "〜くて / 〜で",
        "keywords": ["くて", "で、", "で面白い", "で元気", "で親切", "で静か"],
        "name": "連結兩個以上的形容詞",
        "explanation": "い形容詞去い加『〜くて』；な形容詞加『〜で』。用來串聯多個描述特徵。",
        "examples": ["狭くて暗い部屋です。（狹窄又陰暗的房間。）", "田中さんは元気で面白い人です。（田中先生是有精神又有趣的人。）"],
    },
    {
        "pattern": "名詞は名詞が形容詞",
        "keywords": ["は", "が下手", "が上手", "が高い", "が安い", "が好き", "が嫌い"],
        "name": "名詞は名詞が形容詞（整體與局部特徵）",
        "explanation": "用『〜は〜が＋形容詞』來描述大主題中的某個特定面向或特徵（能力、好惡、價格等）。",
        "examples": ["あのレストランは値段が高いです。（那家餐廳價格很高。）", "私は歌が下手です。（我不擅長唱歌。）"],
    },
    {
        "pattern": "〜が",
        "keywords": ["ですが", "したが", "ますが", "いですが"],
        "name": "轉折語氣 〜が（但是/可是）",
        "explanation": "接在句子後面表示轉折，語氣比『でも』更加自然與柔和。",
        "examples": ["この料理は美味しいですが、ちょっと辛いです。（這道菜很好吃，但是有點辣。）"],
    },
    {
        "pattern": "〜と思います / 〜と思いませんか",
        "keywords": ["と思います", "と思う", "思っています", "だと思", "ないと思", "たと思"],
        "name": "意見與推測 〜と思います（我覺得…… / 我想……）",
        "explanation": "普通形＋と思います。表達說話者的主觀推測、意見或想法，比直接斷定更有禮貌。",
        "examples": ["田中さんは遅れると思います。（我想田中先生會遲到。）", "明日は休みだと思います。（我覺得明天是放假。）"],
    },
    {
        "pattern": "授受動詞（あげます・もらいます・くれます・てくれます）",
        "keywords": ["あげま", "もらいま", "くれま", "あげた", "もらった", "くれた", "てあげ", "てもら", "てくれ"],
        "name": "授受動詞（給予與接受行為）",
        "explanation": "・あげます：我給別人 / 別人給別人\n・もらいます：從某人那裡得到\n・くれます：別人主動給我（或我方的人）\n・〜てくれます：別人為我做某事（感謝他人）\n・〜てもらいます：委請他人為我做某事",
        "examples": ["友達が私に映画のチケットをくれました。（朋友給了我電影票。）", "田中さんに京都を案内してもらいました。（請田中先生為我導覽京都。）"],
    },
    {
        "pattern": "動詞ましょうか",
        "keywords": ["ましょうか"],
        "name": "提議與主動提議提供協助 〜ましょうか",
        "explanation": "動詞ます形去ます＋ましょうか。超商生活極核心用法！店員主動提議幫顧客加熱、拿袋子時常使用。",
        "examples": ["お弁当を温めましょうか。（需要為您微波加熱便當嗎？）", "手伝いましょうか。（需要我幫忙嗎？）"],
    },
    {
        "pattern": "原因理由：〜て/なくて、〜 / 〜ので",
        "keywords": ["ので", "て、疲れ", "なくて、よかっ", "が多くて", "が好きなので", "が痛いので", "休みなので"],
        "name": "原因理由 〜て/なくて、〜 / 〜ので（因為……所以……）",
        "explanation": "・動詞て形/い形容詞くて：輕微客觀因果關係\n・〜ので：接在普通形後（名詞/な形容詞＋な），語氣客觀且極具禮貌，超商與商務首選。",
        "examples": ["日本の夏はとても暑いので、よく冷たいビールを飲みます。（因為日本夏天很熱，所以常喝冰啤酒。）"],
    },
    {
        "pattern": "〜てもらえませんか / 〜ていただけませんか",
        "keywords": ["てもらえませんか", "ていただけませんか", "てもらえますか", "ていただけますか"],
        "name": "委婉請求 〜てもらえませんか / 〜ていただけませんか",
        "explanation": "動詞て形＋てもらえませんか（口語客氣）或 ていただけませんか（更為尊敬）。日本超商請店員微波或拿物品的必備金句！",
        "examples": ["お弁当を温めてもらえませんか。（可以麻煩幫我微波便當嗎？）", "この平仮名の読み方を教えてもらえませんか。（能請您教我這個平假名的讀法嗎？）"],
    },
    {
        "pattern": "動詞（ます削除）＋かた（方）",
        "keywords": ["かた", "使い方", "買い方", "作り方", "行き方", "読み方"],
        "name": "動作的方法 〜かた（……的方式/做法）",
        "explanation": "動詞ます形去ます＋かた。名詞化用法，例如「買う」→「買い方」（購買方式）。",
        "examples": ["チケットの買い方を教えてもらえませんか。（能教我怎麼買票嗎？）", "パソコンの使い方を教えてください。（請教我電腦的使用方法。）"],
    },
    {
        "pattern": "動詞てみます / 〜てみたい",
        "keywords": ["てみます", "てみたい", "てみて", "てみてもいい"],
        "name": "嘗試去做 〜てみます（試試看……）",
        "explanation": "動詞て形＋みます。表示親自嘗試某個動作來體驗看看。",
        "examples": ["これは美味しいお菓子です。食べてみてください。（這是很美味的點心，請吃吃看。）", "日本語で話してみてもいいですか。（可以用日文試著說說看嗎？）"],
    },
    {
        "pattern": "動詞なくてもいいですか",
        "keywords": ["なくてもいい", "なくてもいいですか"],
        "name": "免除/許可 〜なくてもいいですか（不……也可以嗎？）",
        "explanation": "動詞ない形去い＋くてもいいです(か)。超商常客婉拒塑膠袋、收據、加熱時非常實用！",
        "examples": ["レシートをもらわなくてもいいですか。（可以不用拿收據嗎？）", "袋を持って行かなくてもいいですか。（不用帶袋子去也可以嗎？）"],
    },
    {
        "pattern": "〜んです / どうしたんですか",
        "keywords": ["んです", "んですか", "んだ", "どうしたんですか"],
        "name": "情境說明與強調原因 〜んです",
        "explanation": "普通形＋んです（名詞/な形容詞＋なんです）。向對方說明狀況背景或深入尋求原因，語氣強烈且親近。",
        "examples": ["どうしたんですか。（怎麼了嗎？）", "お腹が痛いんです。（肚子好痛啊。）", "財布を忘れたんです。（把錢包給忘了。）"],
    },
    {
        "pattern": "〜たら / もし〜たら",
        "keywords": ["たら", "もし"],
        "name": "條件與假定 〜たら（如果……的話 / ……之後）",
        "explanation": "動詞/形容詞的た形＋ら。表示假定條件（如果～）或是確定動作完成後的下一個動作（～之後）。",
        "examples": ["仕事が終わったら、コンビニに行きませんか。（工作結束後要不要去超商？）", "もし雨が降ったら、傘を貸してください。（如果下雨的話，請借我傘。）"],
    },
]


def explain_grammar_and_phrase(phrase: str) -> str:
    """Analyze a Japanese phrase, identify its target J3/N5 grammar patterns, and return a structured breakdown.

    Args:
        phrase: The Japanese sentence or phrase to analyze (e.g. 'お弁当を温めてもらえませんか', '雨が降っているので傘を買います').

    Returns:
        A detailed explanation of the grammar rule, meaning, breakdown, and convenience store usage tip.
    """
    phrase_clean = phrase.strip()
    matched = []

    for item in J3_GRAMMAR_PATTERNS:
        for kw in item["keywords"]:
            if kw in phrase_clean:
                matched.append(item)
                break

    if not matched:
        return (
            f"【日本語フレーズ解説】: 「{phrase_clean}」\n"
            f"・日常會話常用語，適合在便利商店購物與問詢時使用。\n"
            f"・提示：可以嘗試融入 J3 常用文法（如『〜てもらえませんか』、『〜ので』、『〜と思います』）來造句喔！"
        )

    lines = [f"【🎓 日本語文法・フレーズ解説】: 「{phrase_clean}」"]
    for m in matched:
        lines.append(f"\n📌 文法項目: {m['name']} ({m['pattern']})")
        lines.append(f"💡 用法說明: {m['explanation']}")
        lines.append("📖 例句參考:")
        for ex in m["examples"]:
            lines.append(f"   ・{ex}")

    lines.append("\n🏪 コンビニでのワンポイントアドバイス:")
    lines.append("店員に話しかける時は、この文法を使うととても丁寧で自然な日本語になりますよ！")

    return "\n".join(lines)

# ==========================================
# 自由公開 API: Jisho 日本語辞書検索ツール
# (https://github.com/public-apis/public-apis -> Dictionaries / Jisho)
# ==========================================
import urllib.parse
import requests


def lookup_japanese_dictionary(keyword: str) -> str:
    """Look up a Japanese word in the free public Jisho.org dictionary API to fetch real readings, English definitions, and JLPT levels.

    Args:
        keyword: The Japanese or English term to look up (e.g. '割引', 'おにぎり', '弁当', 'receipt').

    Returns:
        Real dictionary entry including kanji, hiragana reading, JLPT level, and primary definitions.
    """
    keyword_clean = keyword.strip()
    if not keyword_clean:
        return "検索する単語を入力してください。"

    encoded_kw = urllib.parse.quote(keyword_clean)
    url = f"https://jisho.org/api/v1/search/words?keyword={encoded_kw}"

    try:
        resp = requests.get(url, timeout=6)
        if resp.status_code != 200:
            return f"辞書APIの呼び出しに失敗しました（HTTP {resp.status_code}）。"

        data = resp.json().get("data", [])
        if not data:
            return f"「{keyword_clean}」に関する辞書データは見つかりませんでした。"

        first = data[0]
        japanese = first.get("japanese", [{}])[0]
        word = japanese.get("word") or first.get("slug", keyword_clean)
        reading = japanese.get("reading", "")
        jlpt_tags = first.get("jlpt", [])
        jlpt_str = ", ".join(t.upper() for t in jlpt_tags) if jlpt_tags else "日常単語 (General)"
        senses = first.get("senses", [])
        definitions = senses[0].get("english_definitions", []) if senses else []
        def_str = "; ".join(definitions[:4])

        return (
            f"【📖 Jisho 実時間オンライン日本語辞書】: 「{keyword_clean}」\n"
            f"・表記: {word}\n"
            f"・読み（ふりがな）: {reading}\n"
            f"・JLPT難易度: {jlpt_str}\n"
            f"・意味（定義）: {def_str}\n"
            f"店員: 『Jisho辞書で調べました！日本の生活やコンビニでもよく使う単語ですね！』"
        )
    except Exception as e:
        return f"辞書検索中に通信エラーが発生しました: {str(e)}"

# ==========================================
# gemini-3.1-flash-lite-image 画像生成ツール
# ==========================================
import time
from google import genai
from google.genai import types
from google.cloud import storage
from google.adk.tools import ToolContext

# Hardcoded bucket name as explicitly requested:
ASSETS_BUCKET_NAME = "konbini-sensei-assets-qwiklabs-gcp-03-35246614a316"


def generate_item_image(
    item_description: str,
    tool_context: ToolContext,
) -> str:
    """Generate an appetizing, illustrative image for a convenience store item using gemini-3.1-flash-lite-image in the global region.

    The generated image is saved to the Playground Artifacts panel and uploaded directly to Cloud Storage.

    Args:
        item_description: Description or name of the item to visualize (e.g. '鮭おにぎり', 'karaage bento', 'matcha ice cream', 'strawberry sandwich').
        tool_context: ADK execution context used to save the artifact to the session.

    Returns:
        The public HTTPS URL of the uploaded image on Google Cloud Storage.
    """
    if not item_description or not item_description.strip():
        return "画像生成のための商品名または説明を入力してください。"

    prompt = (
        f"A delicious, high-quality Japanese convenience store (konbini) food item: "
        f"{item_description.strip()}. Clean studio lighting, appetizing presentation, "
        f"vibrant colors, isolated on a clean simple background, professional food photography style."
    )

    try:
        # Call gemini-3.1-flash-lite-image in global region
        genai_client = genai.Client(
            vertexai=True,
            project=PROJECT_ID,
            location="global",
        )
        response = genai_client.models.generate_content(
            model="gemini-3.1-flash-lite-image",
            contents=prompt,
        )

        image_bytes = None
        mime_type = "image/jpeg"
        if response.candidates:
            for part in response.candidates[0].content.parts:
                if part.inline_data and part.inline_data.data:
                    image_bytes = part.inline_data.data
                    mime_type = part.inline_data.mime_type or "image/jpeg"
                    break

        if not image_bytes:
            return "画像の生成に失敗しました（画像データが返されませんでした）。"

        filename = f"konbini_{int(time.time())}.jpg"

        # (1) Save with tool_context.save_artifact so it shows up in Playground's Artifacts panel
        if tool_context is not None:
            artifact_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
            tool_context.save_artifact(filename=filename, artifact=artifact_part)

        # (2) Upload the same image bytes to public Cloud Storage bucket without writing to local file
        storage_client = storage.Client(project=PROJECT_ID)
        bucket = storage_client.bucket(ASSETS_BUCKET_NAME)
        object_name = f"items/{filename}"
        blob = bucket.blob(object_name)
        blob.upload_from_string(image_bytes, content_type=mime_type)

        public_url = f"https://storage.googleapis.com/{ASSETS_BUCKET_NAME}/{object_name}"

        return (
            f"【🖼️ 商品イラスト生成完了】\n"
            f"・対象商品: {item_description.strip()}\n"
            f"・公開画像URL: {public_url}\n"
            f"・アーティファクト名: {filename}（Playground の Artifacts パネルに保存されました）\n"
            f"店員: 『出来立てで美味しそうな商品のイラストをご用意しました！どうぞご覧ください！』"
        )
    except Exception as e:
        return f"画像生成またはアップロード中にエラーが発生しました: {str(e)}"

# ==========================================
# Google Maps Geocoding & Places API (New) ツール
# ==========================================
def geocode_address(address: str) -> dict | str:
    """Turn a street address or location name into geographic coordinates using Google Maps Geocoding API.

    Args:
        address: The address or place name to geocode (e.g. 'Tokyo Station', 'Shibuya Scramble Crossing', '東京都千代田区丸の内1-9-1').

    Returns:
        Structured dictionary with key fields: name, address, and location (latitude, longitude).
    """
    api_key = os.getenv("GOOGLE_MAPS_API_KEY", "")
    if not api_key:
        return "GOOGLE_MAPS_API_KEY が環境変数に設定されていません。"

    address_clean = address.strip()
    if not address_clean:
        return "住所または地名を入力してください。"

    try:
        url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {"address": address_clean, "key": api_key}
        resp = requests.get(url, params=params, timeout=8)
        data = resp.json()

        if data.get("status") != "OK" or not data.get("results"):
            return f"ジオコーディングに失敗しました: {data.get('status', 'NO_RESULTS')}"

        first_res = data["results"][0]
        formatted_address = first_res.get("formatted_address", "")
        loc = first_res.get("geometry", {}).get("location", {})
        latitude = loc.get("lat")
        longitude = loc.get("lng")

        return {
            "name": address_clean,
            "address": formatted_address,
            "location": {"latitude": latitude, "longitude": longitude},
        }
    except Exception as e:
        return f"Geocoding API 呼び出し中にエラーが発生しました: {str(e)}"


def find_nearby_places(
    latitude: float,
    longitude: float,
    place_type: str = "convenience_store",
    radius_meters: float = 1000.0,
) -> list[dict] | str:
    """Find nearby places of a given type around coordinates using the Google Maps Places API (New).

    Args:
        latitude: Center latitude coordinate (e.g. 35.6812).
        longitude: Center longitude coordinate (e.g. 139.7671).
        place_type: The place type to search for (e.g. 'convenience_store', 'restaurant', 'cafe', 'supermarket').
        radius_meters: Search radius in meters (default 1000.0, max 50000.0).

    Returns:
        List of places containing key fields: name, address, and location.
    """
    api_key = os.getenv("GOOGLE_MAPS_API_KEY", "")
    if not api_key:
        return "GOOGLE_MAPS_API_KEY が環境変数に設定されていません。"

    url = "https://places.googleapis.com/v1/places:searchNearby"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location",
    }
    payload = {
        "includedTypes": [place_type],
        "maxResultCount": 5,
        "locationRestriction": {
            "circle": {
                "center": {
                    "latitude": float(latitude),
                    "longitude": float(longitude),
                },
                "radius": float(radius_meters),
            }
        },
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=8)
        if resp.status_code != 200:
            return f"Places API (New) 呼び出しに失敗しました（HTTP {resp.status_code}）: {resp.text}"

        data = resp.json()
        places_data = data.get("places", [])
        if not places_data:
            return f"指定された地点周辺に該当する施設（{place_type}）は見つかりませんでした。"

        results = []
        for p in places_data:
            display_name = p.get("displayName", {}).get("text", "")
            address = p.get("formattedAddress", "")
            location = p.get("location", {})
            results.append({
                "name": display_name,
                "address": address,
                "location": {
                    "latitude": location.get("latitude"),
                    "longitude": location.get("longitude"),
                },
            })

        return results
    except Exception as e:
        return f"Places API (New) 呼び出し中にエラーが発生しました: {str(e)}"
