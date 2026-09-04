import json
import os
import re
import time
from typing import TypedDict, Optional, Literal
import streamlit as st
from pydantic import BaseModel, Field, ValidationError
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_openai.chat_models.base import OpenAIRateLimitError
from langgraph.graph import StateGraph, START, END

# ============================================================
# 0. ENVIRONMENT & OPENROUTER CONFIGURATION
# ============================================================

load_dotenv()

api_key = os.getenv("OPENROUTER_API_KEY", "").strip().strip('"\'')

if not api_key and "OPENROUTER_API_KEY" in st.secrets:
    api_key = st.secrets["OPENROUTER_API_KEY"].strip()

# OpenRouter keys work for all models. Gemma free is often rate-limited,
# so we keep it primary and fall back when needed.
DEFAULT_MODEL = "google/gemma-4-26b-a4b-it:free"
FALLBACK_MODELS = [
    "google/gemma-4-26b-a4b-it:free",
    "google/gemma-4-31b-it:free",
    "nvidia/nemotron-3.5-lightning:free",
]
STRUCTURED_METHODS = ("function_calling", "json_schema")

model_name = os.getenv("OPENROUTER_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL


def make_llm(model: str) -> ChatOpenAI:
    return ChatOpenAI(
        model=model,
        openai_api_key=api_key if api_key else "missing_key",
        openai_api_base="https://openrouter.ai/api/v1",
        temperature=0,
        max_tokens=1024,
        max_retries=1,
        extra_body={
            "reasoning": {
                "enabled": False
            }
        },
        default_headers={
            "HTTP-Referer": "https://localhost",
            "X-Title": "Mr.Shop",
        },
    )


llm = make_llm(model_name)


def _extract_json_object(text: str) -> dict:
    """Pull the first JSON object out of a free-form model reply."""
    text = (text or "").strip()
    if not text:
        raise ValueError("Empty model response")

    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object found in response: {text[:200]!r}")

    data = json.loads(match.group(0))
    if not isinstance(data, dict):
        raise ValueError("Parsed JSON is not an object")
    return data


def _invoke_json_prompt(candidate_llm: ChatOpenAI, schema: type[BaseModel], prompt: str):
    schema_prompt = (
        f"{prompt}\n\n"
        "Respond with ONLY a valid JSON object. No markdown, no explanation.\n"
        f"JSON schema:\n{json.dumps(schema.model_json_schema(), indent=2)}"
    )
    response = candidate_llm.invoke(schema_prompt)
    content = response.content if hasattr(response, "content") else response
    if isinstance(content, list):
        content = "".join(
            block.get("text", "") if isinstance(block, dict) else str(block)
            for block in content
        )
    return schema.model_validate(_extract_json_object(str(content)))


def invoke_structured(schema: type[BaseModel], prompt: str):
    """
    Structured call with retries across:
    1) models (Gemma first, then free fallbacks)
    2) structured-output methods
    3) plain JSON prompting as last resort
    """
    candidates = [model_name] + [m for m in FALLBACK_MODELS if m != model_name]
    last_error: Exception | None = None

    for candidate in candidates:
        candidate_llm = llm if candidate == model_name else make_llm(candidate)

        for method in STRUCTURED_METHODS:
            try:
                return candidate_llm.with_structured_output(
                    schema, method=method
                ).invoke(prompt)
            except OpenAIRateLimitError as exc:
                last_error = exc
                print(f"[warn] rate-limited on {candidate} ({method}); trying next...")
                break
            except (ValueError, ValidationError, TypeError, KeyError) as exc:
                last_error = exc
                print(
                    f"[warn] structured parse failed on {candidate} "
                    f"({method}): {type(exc).__name__}; trying next..."
                )
                continue
            except Exception as exc:
                last_error = exc
                print(
                    f"[warn] call failed on {candidate} ({method}): "
                    f"{type(exc).__name__}; trying next..."
                )
                continue

        try:
            return _invoke_json_prompt(candidate_llm, schema, prompt)
        except OpenAIRateLimitError as exc:
            last_error = exc
            print(f"[warn] rate-limited on {candidate} (json prompt); trying next...")
            continue
        except Exception as exc:
            last_error = exc
            print(
                f"[warn] json prompt failed on {candidate}: "
                f"{type(exc).__name__}; trying next..."
            )
            continue

    if last_error is not None:
        raise last_error
    raise RuntimeError("No OpenRouter models available to invoke.")


# ============================================================
# 1. STATE
# ============================================================

class ShopState(TypedDict):
    messages: list
    intent: Optional[str]
    memory_update: dict
    ambient_memory: dict
    response: Optional[str]


# ============================================================
# 2. AMBIENT MEMORY SCHEMA
# ============================================================

class MemoryUpdate(BaseModel):
    wardrobe: list[str] = Field(default_factory=list)
    preferences: dict = Field(default_factory=dict)
    budget: Optional[int] = None


# ============================================================
# 3. INTENT SCHEMA
# ============================================================

class IntentResult(BaseModel):
    intent: Literal[
        "WARDROBE_UPLOAD",
        "STYLING_ADVICE",
        "PURCHASE",
        "BOOKING"
    ]


# ============================================================
# 4. HELPER — GET USER MESSAGE
# ============================================================

def get_user_message(state: ShopState) -> str:
    message = state["messages"][-1]

    # If using a LangChain Message object (HumanMessage, AIMessage, etc.)
    if hasattr(message, "content"):
        return str(message.content)

    # If message is a dictionary
    if isinstance(message, dict):
        return str(message.get("content", ""))

    return str(message)


# ============================================================
# 5. MEMORY EXTRACTION
# ============================================================

def memory_extraction(state: ShopState):

    user_message = get_user_message(state)

    prompt = f"""
You are the memory extraction system for Mr.Shop,
a conversational AI fashion stylist.

Extract ONLY information that is useful to remember
about the user for future turns.

Possible memory categories:

1. wardrobe
   Clothing items the user owns.

2. preferences
   Fashion preferences such as fit, colors, brands,
   styles, etc.

3. budget
   The user's stated spending limit.

Do not store temporary conversational information.

User message:
{user_message}

Return the information that should be added or updated
in the user's ambient memory.
"""

    result = invoke_structured(MemoryUpdate, prompt)

    update_data = (
        result.model_dump()
        if hasattr(result, "model_dump")
        else (result if isinstance(result, dict) else {})
    )

    return {
        "memory_update": update_data
    }


# ============================================================
# 6. UPDATE AMBIENT MEMORY
# ============================================================

def update_memory(state: ShopState):

    existing = state.get("ambient_memory") or {}
    updated_memory = {
        "wardrobe": list(existing.get("wardrobe") or []),
        "preferences": dict(existing.get("preferences") or {}),
        "budget": existing.get("budget")
    }

    update = state.get("memory_update") or {}

    # Add wardrobe items
    for item in update.get("wardrobe", []):
        if item not in updated_memory["wardrobe"]:
            updated_memory["wardrobe"].append(item)

    # Update preferences
    updated_memory["preferences"].update(
        update.get("preferences", {})
    )

    # Update budget if provided
    if update.get("budget") is not None:
        updated_memory["budget"] = update["budget"]

    return {
        "ambient_memory": updated_memory
    }


# ============================================================
# 7. INTENT CLASSIFICATION
# ============================================================

def intent_classifier(state: ShopState):

    user_message = get_user_message(state)

    prompt = f"""
You are the intent classifier for Mr.Shop.

Classify the user's current request into exactly ONE
of these intents:

WARDROBE_UPLOAD
STYLING_ADVICE
PURCHASE
BOOKING

Definitions:

WARDROBE_UPLOAD:
User wants to add, update, remove, inspect, or manage
items in their digital wardrobe.

STYLING_ADVICE:
User wants outfit recommendations, fashion advice,
fit advice, color advice, or styling suggestions.

PURCHASE:
User wants to find, compare, or buy a fashion product.

BOOKING:
User wants to book or consult a human stylist
or colour analyst.

User message:
{user_message}

Return JSON like: {{"intent": "STYLING_ADVICE"}}
"""

    result = invoke_structured(IntentResult, prompt)

    intent_val = getattr(result, "intent", None)
    if not intent_val and isinstance(result, dict):
        intent_val = result.get("intent")

    return {
        "intent": intent_val
    }


# ============================================================
# 8. ROUTER
# ============================================================

def router(state: ShopState):

    intent = state.get("intent")
    valid_intents = {"WARDROBE_UPLOAD", "STYLING_ADVICE", "PURCHASE", "BOOKING"}
    if intent in valid_intents:
        return intent
    return "STYLING_ADVICE"


# ============================================================
# 9. AGENTS
# ============================================================

def _normalize_content(content) -> str:
    if isinstance(content, list):
        return "".join(
            block.get("text", "") if isinstance(block, dict) else str(block)
            for block in content
        ).strip()
    return str(content or "").strip()


def invoke_chat(prompt: str) -> str:
    """Plain chat completion with the same model fallback chain."""
    candidates = [model_name] + [m for m in FALLBACK_MODELS if m != model_name]
    last_error: Exception | None = None
    saw_account_limit = False

    for candidate in candidates:
        candidate_llm = llm if candidate == model_name else make_llm(candidate)
        try:
            response = candidate_llm.invoke(prompt)
            text = _normalize_content(
                response.content if hasattr(response, "content") else response
            )
            if not text:
                raise ValueError("Empty chat response")
            return text
        except OpenAIRateLimitError as exc:
            last_error = exc
            if "free-models-per-min" in str(exc):
                saw_account_limit = True
                print("[warn] account free-tier minute limit hit; stopping model fan-out")
                break
            print(f"[warn] rate-limited on {candidate} (chat); trying next...")
            continue
        except Exception as exc:
            last_error = exc
            print(
                f"[warn] chat failed on {candidate}: "
                f"{type(exc).__name__}; trying next..."
            )
            continue

    if saw_account_limit and isinstance(last_error, OpenAIRateLimitError):
        # One short pause, then a single retry on the preferred model.
        print("[warn] waiting 15s for free-tier window, then one retry...")
        time.sleep(15)
        try:
            response = llm.invoke(prompt)
            text = _normalize_content(
                response.content if hasattr(response, "content") else response
            )
            if text:
                return text
        except Exception as exc:
            last_error = exc

    if last_error is not None:
        raise last_error
    raise RuntimeError("No OpenRouter models available for chat.")


def format_ambient_memory(state: ShopState) -> str:
    memory = state.get("ambient_memory") or {}
    return (
        f"- wardrobe: {memory.get('wardrobe') or []}\n"
        f"- preferences: {memory.get('preferences') or {}}\n"
        f"- budget: {memory.get('budget')}"
    )


def fallback_agent_answer(state: ShopState, agent_label: str) -> str:
    """Local reply when all free LLM calls are rate-limited."""
    memory = state.get("ambient_memory") or {}
    preferences = memory.get("preferences") or {}
    wardrobe = memory.get("wardrobe") or []
    budget = memory.get("budget")
    user_message = get_user_message(state).lower()

    if "prefer" in user_message or "preference" in user_message:
        if preferences:
            return (
                f"From what I've saved so far, your preferences are: {preferences}."
                + (f" Budget noted: ₹{budget}." if budget is not None else "")
            )
        return (
            "I don't have a saved outfit preference yet. "
            "Tell me styles you like (e.g. traditional, oversized, minimal) and I'll remember them."
        )

    if agent_label.startswith("Styling"):
        bits = []
        if preferences:
            bits.append(f"leaning into {preferences}")
        if wardrobe:
            bits.append(f"using pieces from your wardrobe: {wardrobe}")
        if budget is not None:
            bits.append(f"keeping looks around ₹{budget}")
        detail = "; ".join(bits) if bits else "share a vibe or occasion"
        return f"I can help style you — {detail}. What occasion is this for?"

    if agent_label.startswith("Purchase"):
        if budget is not None:
            return (
                f"I can help you shop within ₹{budget}. "
                f"What item are you looking for?"
            )
        return "I can help you find pieces to buy. What's your budget and what do you need?"

    if agent_label.startswith("Wardrobe"):
        if wardrobe:
            return f"Your saved wardrobe items: {wardrobe}. Want to add or update anything?"
        return "Your wardrobe is empty so far. Tell me what you own and I'll save it."

    return (
        "I can help book a human stylist or colour analyst. "
        "What city/date works, and is this for styling or colour analysis?"
    )


def run_agent(state: ShopState, agent_label: str, role_instructions: str) -> dict:
    user_message = get_user_message(state)
    prompt = f"""
You are the {agent_label} for Mr.Shop, a conversational AI fashion stylist
in an Instagram DM chat.

{role_instructions}

Known ambient memory about this user:
{format_ambient_memory(state)}

User message:
{user_message}

Reply in a helpful, concise chat tone (2-6 short sentences).
Use the ambient memory when relevant.
If memory is missing for what they asked, say what you know and ask one clear follow-up.
Do not mention JSON, intents, routers, or that you are an agent framework.
Return ONLY the final response to the user.
Do not output your reasoning, analysis, planning, drafts, or thinking process.
"""
    try:
        answer = invoke_chat(prompt)
    except Exception as exc:
        print(f"[warn] agent LLM unavailable ({type(exc).__name__}); using local fallback")
        answer = fallback_agent_answer(state, agent_label)

    return {
        "response": f"**{agent_label} selected.**\n\n{answer}"
    }


def wardrobe_agent(state: ShopState):
    return run_agent(
        state,
        "Wardrobe agent",
        "Help the user add, update, inspect, or organize items in their digital wardrobe.",
    )


def styling_agent(state: ShopState):
    return run_agent(
        state,
        "Styling agent",
        "Give outfit ideas, fit/color advice, and styling suggestions based on their preferences and wardrobe.",
    )


def purchase_agent(state: ShopState):
    return run_agent(
        state,
        "Purchase agent",
        "Help them find, compare, or buy fashion products within their budget and taste.",
    )


def booking_agent(state: ShopState):
    return run_agent(
        state,
        "Booking agent",
        "Help them book or consult a human stylist or colour analyst.",
    )


# ============================================================
# 10. BUILD GRAPH
# ============================================================

builder = StateGraph(ShopState)

builder.add_node("memory_extraction", memory_extraction)
builder.add_node("update_memory", update_memory)
builder.add_node("intent_classifier", intent_classifier)

builder.add_node("wardrobe", wardrobe_agent)
builder.add_node("styling", styling_agent)
builder.add_node("purchase", purchase_agent)
builder.add_node("booking", booking_agent)

builder.add_edge(START, "memory_extraction")
builder.add_edge("memory_extraction", "update_memory")
builder.add_edge("update_memory", "intent_classifier")

builder.add_conditional_edges(
    "intent_classifier",
    router,
    {
        "WARDROBE_UPLOAD": "wardrobe",
        "STYLING_ADVICE": "styling",
        "PURCHASE": "purchase",
        "BOOKING": "booking"
    }
)

builder.add_edge("wardrobe", END)
builder.add_edge("styling", END)
builder.add_edge("purchase", END)
builder.add_edge("booking", END)

app = builder.compile()


if __name__ == "__main__":
    if not api_key:
        print("=" * 60)
        print("[ERROR] OPENROUTER_API_KEY is missing or empty in .env")
        print("-> Please open your .env file and set your key:")
        print("   OPENROUTER_API_KEY=sk-or-v1-your-actual-key-here")
        print("=" * 60)
        exit(1)

    print(f"Running Mr.Shop graph with OpenRouter model: {model_name}...")
    result = app.invoke({
        "messages": [
            "I like oversized clothes and my budget is 4000"
        ],
        "intent": None,
        "memory_update": {},
        "ambient_memory": {
            "wardrobe": [],
            "preferences": {},
            "budget": None
        },
        "response": None
    })

    print("\nExecution Result:")
    print(result)
