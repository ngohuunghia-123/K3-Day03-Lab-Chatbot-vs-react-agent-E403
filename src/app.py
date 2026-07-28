"""Core app của Mốc 3: Chatbot Baseline và ReAct Agent có guardrails."""

import ast
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from prompts import CHATBOT_BASELINE_PROMPT, MAX_ITERATIONS, REACT_SYSTEM_PROMPT, TIMEOUT_SECONDS
from providers import get_llm_provider
from tools import AVAILABLE_TOOLS

load_dotenv()

ACTION_PATTERN = re.compile(r"^Action:\s*([A-Za-z_][A-Za-z0-9_]*)\s*\[(.*)\]\s*$", re.IGNORECASE | re.DOTALL)


def load_test_cases():
    """Đọc bộ test case từ config/test_cases.json."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(base_dir, "config", "test_cases.json"), "r", encoding="utf-8") as file:
        return json.load(file)


def run_baseline_chatbot(user_query: str, provider) -> str:
    """Baseline: đúng một LLM call và không có quyền truy cập tool."""
    response = provider.generate(user_query, system_prompt=CHATBOT_BASELINE_PROMPT)
    print(f"\n💬 [BASELINE] {user_query}\n🤖 {response}")
    return response


def parse_action(response: str):
    """Parse ``Action: tool['arg']`` thành tên tool và list tham số."""
    for line in response.splitlines():
        match = ACTION_PATTERN.match(line.strip())
        if not match:
            continue
        tool_name, raw_args = match.groups()
        try:
            if not raw_args.strip():
                args = []
            else:
                try:
                    # Dạng chuẩn: tool['DH1001', 'sản phẩm lỗi']
                    args = list(ast.literal_eval(f"[{raw_args}]"))
                except (ValueError, SyntaxError):
                    # Một số model sinh dạng không nháy: tool[DH1001].
                    # Không evaluate code; chỉ tách token đơn giản thành string.
                    args = [part.strip().strip("\\\"'") for part in raw_args.split(",")]
        except (ValueError, SyntaxError, TypeError) as exc:
            raise ValueError(f"Tham số Action không hợp lệ: {exc}") from exc
        if not all(isinstance(arg, (str, int, float, bool)) for arg in args):
            raise ValueError("Tham số Action phải là kiểu nguyên thủy.")
        return tool_name, args
    return None


def execute_tool(tool_name: str, args: list) -> str:
    """Thực thi đúng một tool, bắt unknown tool/args/timeout thành Observation lỗi."""
    tool = AVAILABLE_TOOLS.get(tool_name)
    if tool is None:
        return f"LỖI TOOL: Không tồn tại tool '{tool_name}'. Tool hợp lệ: {', '.join(AVAILABLE_TOOLS)}"
    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(tool, *args)
            return str(future.result(timeout=TIMEOUT_SECONDS))
    except FuturesTimeoutError:
        return f"LỖI TOOL: Tool '{tool_name}' vượt quá timeout {TIMEOUT_SECONDS}s."
    except TypeError as exc:
        return f"LỖI TOOL: Tham số cho '{tool_name}' không hợp lệ: {exc}"
    except Exception as exc:  # Tool failure là Observation, không làm crash Agent.
        return f"LỖI TOOL: '{tool_name}' thất bại: {exc}"


def run_react_agent(user_query: str, provider, max_iterations: int = MAX_ITERATIONS):
    """Chạy vòng lặp Thought -> Action -> Observation với giới hạn bước."""
    transcript = [f"Question: {user_query}"]
    trace = []
    print(f"\n🤖 [REACT AGENT] {user_query}")

    for step in range(1, max_iterations + 1):
        prompt = "\n".join(transcript)
        response = provider.generate(prompt, system_prompt=REACT_SYSTEM_PROMPT)
        print(f"\n--- Step {step}/{max_iterations} ---\n{response}")

        final_match = re.search(r"Final Answer:\s*(.+)", response, re.IGNORECASE | re.DOTALL)
        if final_match:
            answer = final_match.group(1).strip()
            trace.append({"step": step, "llm": response, "type": "final"})
            return {"answer": answer, "trace": trace, "stopped": "final"}

        try:
            action = parse_action(response)
            if action is None:
                observation = "LỖI PARSE: Cần trả về đúng định dạng Action: tool['tham số'] hoặc Final Answer."
                trace.append({"step": step, "llm": response, "observation": observation})
            else:
                tool_name, args = action
                observation = execute_tool(tool_name, args)
                trace.append({"step": step, "llm": response, "action": tool_name, "args": args, "observation": observation})
        except ValueError as exc:
            observation = f"LỖI PARSE: {exc}"
            trace.append({"step": step, "llm": response, "observation": observation})

        print(f"👁️ Observation: {observation}")
        transcript.extend([response, f"Observation: {observation}"])

    fallback = "Mình chưa thể xác minh đầy đủ thông tin sau số bước cho phép. Vui lòng kiểm tra lại mã đơn hoặc liên hệ nhân viên hỗ trợ."
    print(f"🛡️ GUARDRAIL: {fallback}")
    return {"answer": fallback, "trace": trace, "stopped": "max_iterations"}


def run_agent_suite(test_cases, provider):
    """Chạy ReAct trên các case, ưu tiên case 3-5 để quan sát tool path."""
    results = []
    for case in test_cases:
        result = run_react_agent(case["question"], provider)
        results.append({"id": case["id"], **result})
    return results


if __name__ == "__main__":
    print("=" * 62)
    print("🏫 LAB 3 — MỐC 3: REACT LOOP & SAFEGUARDS")
    print("=" * 62)
    provider = get_llm_provider()
    print(f"🔌 Provider: {provider.__class__.__name__}")
    tests = load_test_cases()
    results = run_agent_suite(tests, provider)
    print("\n📊 TỔNG KẾT:")
    for result in results:
        print(f"Case {result['id']}: stopped={result['stopped']} | {result['answer']}")
