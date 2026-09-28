"""HITL 재고 발주 승인 그래프 — interrupt / resume / checkpointer / thread_id.

강의(N044) 부록 A 코드를 그대로 이 도메인에 옮긴 것. 판정은 전부 규칙 기반(숫자 비교)이라
LLM 호출이 없다 — 이 과제의 목적은 "판정 품질"이 아니라 "멈췄다 이어가는 구조" 자체를
실습하는 것이기 때문.
"""

import sqlite3
from typing import TypedDict

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt, Command

AMOUNT_LIMIT = 1_000_000
QTY_MULTIPLIER = 2
MAX_RETRY = 3


class OrderState(TypedDict, total=False):
    id: str
    item: str
    amount: int
    qty: int
    avg_qty: int
    reason: str
    decision: str          # auto_approved | approved | modified_approved | rejected
    final_amount: int
    final_qty: int
    retry_count: int
    ignore_qty_rule: bool
    triggered: list
    log: str


def _check(state: OrderState, ignore_qty_rule: bool = False) -> list:
    triggered = []
    if state["amount"] > AMOUNT_LIMIT:
        triggered.append(f"발주액 {state['amount']:,}원 > 100만원 초과")
    if not ignore_qty_rule and state["qty"] > state["avg_qty"] * QTY_MULTIPLIER:
        triggered.append(f"수량 {state['qty']} > 평소({state['avg_qty']})의 {QTY_MULTIPLIER}배 초과")
    return triggered


def judge_and_wait(state: OrderState) -> OrderState:
    """노드 실행마다 interrupt()는 최대 한 번만 호출한다.

    "다시 판정"은 이 함수 안에서 while 루프로 돌지 않고, decision을 None으로 남겨
    그래프 엣지가 이 노드로 되돌아오게 한다(재개=단계 재실행이라는 강의 원칙을
    한 노드 안에서 여러 번 겹치지 않게 하기 위함).
    """
    ignore_qty_rule = state.get("ignore_qty_rule", False)
    triggered = _check(state, ignore_qty_rule=ignore_qty_rule)

    if not triggered:
        state["decision"] = "auto_approved"
        state["final_amount"] = state["amount"]
        state["final_qty"] = state["qty"]
        state["triggered"] = []
        state["log"] = "자동 처리: 멈춤 기준에 해당하지 않음"
        return state

    answer = interrupt({
        "요청": f"{state['item']} — {state['reason']}",
        "금액": f"{state['amount']:,}원",
        "수량": f"{state['qty']}개 (평소 {state['avg_qty']}개)",
        "멈춘 이유": " / ".join(triggered),
        "통과시키면": f"{state['amount']:,}원 규모 발주가 거래처로 즉시 전송됩니다",
    })

    action = answer.get("action")

    if action == "approve":
        state["decision"] = "approved"
        state["final_amount"] = state["amount"]
        state["final_qty"] = state["qty"]
        state["triggered"] = triggered
        state["log"] = "담당자 승인으로 그대로 실행"

    elif action == "approve_modified":
        state["decision"] = "modified_approved"
        state["final_amount"] = answer.get("new_amount", state["amount"])
        state["final_qty"] = answer.get("new_qty", state["qty"])
        state["triggered"] = triggered
        state["log"] = f"담당자가 금액/수량을 수정 후 승인 ({state['final_amount']:,}원 / {state['final_qty']}개)"

    elif action == "reject":
        state["decision"] = "rejected"
        state["triggered"] = triggered
        state["log"] = "담당자 반려로 실행되지 않음"

    elif action == "retry":
        retry_count = state.get("retry_count", 0) + 1
        state["retry_count"] = retry_count
        if retry_count >= MAX_RETRY:
            state["decision"] = "rejected"
            state["triggered"] = triggered
            state["log"] = f"재판정 상한({MAX_RETRY}회) 도달 — 자동 반려"
        else:
            # 이번 도메인의 "다시 판정" = 수량 기준을 이번 건에 한해 예외 적용해 재계산.
            # decision을 비워 두면 아래 route_after_judge가 이 노드로 되돌린다.
            state["ignore_qty_rule"] = True
            state["decision"] = None

    else:
        state["decision"] = "rejected"
        state["triggered"] = triggered
        state["log"] = f"알 수 없는 응답({action})으로 안전 반려"

    return state


def route_after_judge(state: OrderState) -> str:
    return "judge_and_wait" if state.get("decision") is None else "execute"


def execute(state: OrderState) -> OrderState:
    state["log"] = state.get("log", "") + " → 실행 완료"
    return state


def build_graph():
    g = StateGraph(OrderState)
    g.add_node("judge_and_wait", judge_and_wait)
    g.add_node("execute", execute)
    g.add_edge(START, "judge_and_wait")
    g.add_conditional_edges("judge_and_wait", route_after_judge, ["judge_and_wait", "execute"])
    g.add_edge("execute", END)
    return g


def compile_app(sqlite_path: str = "checkpoints.sqlite"):
    conn = sqlite3.connect(sqlite_path, check_same_thread=False)
    checkpointer = SqliteSaver(conn)
    return build_graph().compile(checkpointer=checkpointer)


def config_for(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}}
