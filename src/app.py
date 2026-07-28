"""Ứng dụng lab: chạy Chatbot Baseline trên bộ test case của nhóm."""

import json
import os
import sys

from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from prompts import CHATBOT_BASELINE_PROMPT
from providers import get_llm_provider

load_dotenv()


def load_test_cases():
    """Đọc bộ 5 test case từ config/test_cases.json."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(base_dir, "config", "test_cases.json")
    with open(config_path, "r", encoding="utf-8") as file:
        return json.load(file)


def run_baseline_chatbot(user_query: str, provider) -> str:
    """Một LLM call duy nhất, không truyền registry và không gọi tool."""
    response = provider.generate(user_query, system_prompt=CHATBOT_BASELINE_PROMPT)
    print(f"\n💬 [BASELINE] {user_query}\n🤖 {response}")
    return response


def run_baseline_suite(test_cases, provider):
    """Chạy baseline trên toàn bộ test case để Role 5 ghi nhận kết quả."""
    print(f"\n📋 Chạy Baseline trên {len(test_cases)} test cases (tool_calls=0)")
    results = []
    for case in test_cases:
        response = run_baseline_chatbot(case["question"], provider)
        results.append({"id": case["id"], "question": case["question"], "response": response})
    return results


if __name__ == "__main__":
    print("=" * 58)
    print("🏫 LAB 3 — MỐC 2: CHATBOT BASELINE & TOOL SPECS")
    print("=" * 58)
    provider = get_llm_provider()
    model_name = getattr(provider, "model_name", "Offline Mock Mode")
    print(f"🔌 Provider: {provider.__class__.__name__} (Model: {model_name})")

    tests = load_test_cases()
    print(f"✅ Đã tải {len(tests)} test cases")
    run_baseline_suite(tests, provider)
