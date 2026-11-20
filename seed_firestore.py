#!/usr/bin/env python3
"""Seed Firestore with initial Konbini items."""

from google.cloud import firestore

# Hardcoded project ID as required: do not use google.auth.default() or GOOGLE_CLOUD_PROJECT
PROJECT_ID = "qwiklabs-gcp-03-35246614a316"
COLLECTION_NAME = "konbini_items"

SAMPLE_ITEMS = [
    {
        "id": "onigiri_salmon",
        "name_kanji": "鮭おにぎり",
        "name_kana": "さけおにぎり",
        "english_name": "Salmon Rice Ball",
        "category": "food",
        "price_jpy": 150,
        "stock": 12,
        "description": "新鮮な鮭が入っている美味しいおにぎりです。",
        "image_url": "https://www.irodori.jpf.go.jp/assets/img/illust/starter/l_03_01.png",
    },
    {
        "id": "karaage_bento",
        "name_kanji": "唐揚げ弁当",
        "name_kana": "からあげべんとう",
        "english_name": "Fried Chicken Bento",
        "category": "food",
        "price_jpy": 550,
        "stock": 8,
        "description": "温かいご飯とジューシーな唐揚げの弁当です。『温めてもらえませんか』と頼んでみてください。",
        "image_url": "https://www.irodori.jpf.go.jp/assets/img/illust/starter/l_03_02.png",
    },
    {
        "id": "tamago_sandwich",
        "name_kanji": "たまごサンドイッチ",
        "name_kana": "たまごサンドイッチ",
        "english_name": "Egg Sandwich",
        "category": "food",
        "price_jpy": 240,
        "stock": 10,
        "description": "柔らかくて美味しい卵のサンドイッチです。",
        "image_url": "https://www.irodori.jpf.go.jp/assets/img/illust/starter/l_03_03.png",
    },
    {
        "id": "ocha_green_tea",
        "name_kanji": "冷たいお茶",
        "name_kana": "つめたいおちゃ",
        "english_name": "Cold Green Tea",
        "category": "drink",
        "price_jpy": 130,
        "stock": 20,
        "description": "すっきりした日本の緑茶です。暑い日によく飲みます。",
        "image_url": "https://www.irodori.jpf.go.jp/assets/img/illust/starter/l_03_04.png",
    },
    {
        "id": "kasa_umbrella",
        "name_kanji": "ビニール傘",
        "name_kana": "ビニールがさ",
        "english_name": "Plastic Umbrella",
        "category": "daily",
        "price_jpy": 600,
        "stock": 5,
        "description": "雨の日に便利で丈夫な透明の傘です。",
        "image_url": "https://www.irodori.jpf.go.jp/assets/img/illust/starter/l_03_05.png",
    },
    {
        "id": "purin_pudding",
        "name_kanji": "カスタードプリン",
        "name_kana": "カスタードプリン",
        "english_name": "Custard Pudding",
        "category": "dessert",
        "price_jpy": 180,
        "stock": 15,
        "description": "甘くて美味しいコンビニの人気デザートです。",
        "image_url": "https://www.irodori.jpf.go.jp/assets/img/illust/starter/l_03_06.png",
    },
]


def seed_database():
    db = firestore.Client(project=PROJECT_ID)
    print(f"Connecting to Firestore project: {PROJECT_ID}")
    collection_ref = db.collection(COLLECTION_NAME)

    for item in SAMPLE_ITEMS:
        item_id = item["id"]
        doc_ref = collection_ref.document(item_id)
        doc_ref.set(item)
        print(f"  ✓ Seeded item: {item['name_kanji']} ({item_id})")

    print(f"\nSuccessfully seeded {len(SAMPLE_ITEMS)} items into '{COLLECTION_NAME}' collection.")


if __name__ == "__main__":
    seed_database()
