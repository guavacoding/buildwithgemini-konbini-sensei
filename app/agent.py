# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
from zoneinfo import ZoneInfo

from a2ui.basic_catalog.provider import BasicCatalog
from a2ui.schema.manager import A2uiSchemaManager
from app.a2ui_utils import a2ui_callback
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.code_executors.agent_engine_sandbox_code_executor import (
    AgentEngineSandboxCodeExecutor,
)
from google.adk.models import Gemini
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.genai import types


# WRITE: after each turn, send the session to Memory Bank for extraction.
async def generate_memories_callback(callback_context: CallbackContext):
    """Callback to extract and persist user facts/allergies to Vertex AI Memory Bank."""
    try:
        await callback_context.add_session_to_memory()
    except ValueError:
        # Memory service not attached (e.g. basic unit test or in-memory runner)
        pass
    except Exception:
        pass
    return None

# Agent Engine Code Execution Sandbox
SANDBOX_RESOURCE_NAME = "projects/555304044942/locations/us-east1/reasoningEngines/2833528326197346304/sandboxEnvironments/5851726227349438464"
AGENT_ENGINE_RESOURCE_NAME = "projects/555304044942/locations/us-east1/reasoningEngines/2833528326197346304"

sandbox_executor = AgentEngineSandboxCodeExecutor(
    sandbox_resource_name=SANDBOX_RESOURCE_NAME,
    agent_engine_resource_name=AGENT_ENGINE_RESOURCE_NAME,
)


MODEL = "gemini-3.8-flash"


def get_weather(query: str) -> str:
    """Simulates a web search. Use it get information on weather.

    Args:
        query: A string containing the location to get weather information for.

    Returns:
        A string with the simulated weather information for the queried location.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        return "It's 60 degrees and foggy."
    return "It's 90 degrees and sunny."


def get_current_time(query: str) -> str:
    """Simulates getting the current time for a city.

    Args:
        city: The name of the city to get the current time for.

    Returns:
        A string with the current time information.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        tz_identifier = "America/Los_Angeles"
    else:
        return f"Sorry, I don't have timezone information for query: {query}."

    tz = ZoneInfo(tz_identifier)
    now = datetime.datetime.now(tz)
    return f"The current time for query {query} is {now.strftime('%Y-%m-%d %H:%M:%S %Z%z')}"


from app.konbini_tools import (
    explain_grammar_and_phrase,
    find_nearby_places,
    geocode_address,
    generate_item_image,
    get_item_details,
    get_learning_profile,
    list_shop_items,
    lookup_japanese_dictionary,
    purchase_item,
    restock_item,
    update_points_and_learning_log,
)

schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

A2UI_INSTRUCTION = schema_manager.generate_system_prompt(
    role_description=(
        "你是「コンビニ先生（KonbiniSensei）」，一個熱情友善的日本便利商店店員兼日語學習導師。\n"
        "你的任務是透過真實的日本便利商店情境，陪伴學習者（N5 / J3 初級程度）練習日文會話、生活購物、文法與單字。\n"
        "當顧客詢問商品、結帳、查看會員手帳、查詢辭典、查看商品圖片、尋找周邊超商或執行運算時，呼叫對應的工具。\n"
        "【重要】特別注意並牢記使用者的所有過敏原（如花生、堅果、海鮮、蛋類、乳製品、麩質等食物或藥物過敏）。每當使用者提及過敏時，必須在記憶中隨時留意，並在推薦食品或結帳時主動把關避開含有過敏原的商品。"
    ),
    workflow_description="Analyze the request and return structured UI when appropriate.",
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket). Set the Image url to that exact https link, for example "
        "{\"Image\": {\"url\": {\"literalString\": \"https://...\"}}}. Never point an "
        "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
        "not have a public URL, add a short Text line noting the image instead. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
        "headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
    ),
    include_schema=True,
    include_examples=True,
)

INSTRUCTION = f"""{A2UI_INSTRUCTION}

額外業務與對話指引：
- 親切有禮貌，使用 N5 程度的日語（如「いらっしゃいませ！」、「温めましょうか？」、「ポイントカードはお持ちですか？」、「袋はどうなさいますか？」）。
- 適時提供平假名發音輔助與繁體中文說明。
- 自然引導並練習 J3 / N5 核心文法（〜ています、〜てくれます、〜てもらえませんか、〜ましょうか、〜ので 等）。
- 查詢日文辭典時使用 lookup_japanese_dictionary；生成超商美食商品圖片時使用 generate_item_image 並將回傳的公開 HTTPS 網址放入 A2UI Image 組件。
- 嚴格遵守過敏原安全防護，牢記使用者的過敏史並守護顧客健康。
"""

root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=INSTRUCTION,
    code_executor=sandbox_executor,
    after_model_callback=a2ui_callback,
    after_agent_callback=generate_memories_callback,
    tools=[
        PreloadMemoryTool(),
        list_shop_items,
        get_item_details,
        purchase_item,
        restock_item,
        get_learning_profile,
        update_points_and_learning_log,
        explain_grammar_and_phrase,
        lookup_japanese_dictionary,
        generate_item_image,
        geocode_address,
        find_nearby_places,
        get_weather,
        get_current_time,
    ],
)

app = App(
    root_agent=root_agent,
    name="app",
)
