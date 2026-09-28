"""HITL 재고 발주 승인 데모 — 담당자가 10초 안에 판단하는 승인 화면.

실행: streamlit run app.py
"""

import streamlit as st
from langgraph.types import Command

from data import REQUESTS
from graph import compile_app, config_for

st.set_page_config(page_title="재고 발주 승인 (HITL)", layout="centered")


@st.cache_resource
def get_app():
    return compile_app("checkpoints.sqlite")


app = get_app()


def status_of(req_id: str):
    state = app.get_state(config_for(req_id))
    if not state.values:
        return "미실행", state
    if state.next:
        return "대기중(사람 승인 필요)", state
    return state.values.get("decision", "완료"), state


st.title("📦 재고 자동 발주 승인 (HITL)")
st.caption("멈춤 기준: ① 발주액 100만원 초과 ② 수량이 평소의 2배 초과 — 둘 다 규칙 기반, LLM 호출 없음")

if st.button("1) 전체 요청 판정 실행", type="primary"):
    for req in REQUESTS:
        cfg = config_for(req["id"])
        state = app.get_state(cfg)
        if not state.values:
            app.invoke(
                {"id": req["id"], "item": req["item"], "amount": req["amount"],
                 "qty": req["qty"], "avg_qty": req["avg_qty"], "reason": req["reason"]},
                config=cfg,
            )
    st.rerun()

st.divider()
st.subheader("현황판")

rows = []
for req in REQUESTS:
    label, _ = status_of(req["id"])
    rows.append({"건": req["id"], "품목": req["item"], "금액": f"{req['amount']:,}원",
                 "수량": f"{req['qty']}/{req['avg_qty']}", "상태": label})
st.dataframe(rows, hide_index=True, width="stretch")

st.divider()
st.subheader("승인 대기 목록")

pending = []
for req in REQUESTS:
    label, state = status_of(req["id"])
    if label == "대기중(사람 승인 필요)":
        pending.append((req, state))

if not pending:
    st.info("대기 중인 건이 없습니다. 위 버튼으로 먼저 판정을 실행하세요.")

for req, state in pending:
    task = state.tasks[0]
    payload = task.interrupts[0].value
    with st.container(border=True):
        st.markdown(f"### {req['id']} · {payload['요청']}")
        st.write(f"**금액**: {payload['금액']}")
        st.write(f"**수량**: {payload['수량']}")
        st.warning(f"**멈춘 이유**: {payload['멈춘 이유']}")
        st.write(f"**통과시키면**: {payload['통과시키면']}")

        c1, c2, c3, c4 = st.columns(4)
        cfg = config_for(req["id"])

        if c1.button("승인", key=f"approve_{req['id']}"):
            app.invoke(Command(resume={"action": "approve"}), config=cfg)
            st.rerun()

        if c2.button("수정 후 승인", key=f"modify_{req['id']}"):
            st.session_state[f"show_modify_{req['id']}"] = True

        if c3.button("반려", key=f"reject_{req['id']}"):
            app.invoke(Command(resume={"action": "reject"}), config=cfg)
            st.rerun()

        if c4.button("다시 판정", key=f"retry_{req['id']}"):
            app.invoke(Command(resume={"action": "retry"}), config=cfg)
            st.rerun()

        if st.session_state.get(f"show_modify_{req['id']}"):
            new_amount = st.number_input("수정 금액", value=req["amount"], key=f"amt_{req['id']}")
            new_qty = st.number_input("수정 수량", value=req["qty"], key=f"qty_{req['id']}")
            if st.button("수정값으로 승인 확정", key=f"confirm_modify_{req['id']}"):
                app.invoke(
                    Command(resume={"action": "approve_modified", "new_amount": int(new_amount), "new_qty": int(new_qty)}),
                    config=cfg,
                )
                st.session_state[f"show_modify_{req['id']}"] = False
                st.rerun()

st.divider()
st.subheader("지표 (개입률 · 놓침 · 헛멈춤)")

all_states = [(req, status_of(req["id"])[1]) for req in REQUESTS]
processed = [(req, state) for req, state in all_states if state.values]
resolved = [(req, state) for req, state in processed if not state.next]

if resolved:
    total = len(resolved)
    flagged = sum(1 for _, state in resolved if state.values.get("decision") != "auto_approved")

    miss = sum(1 for req, state in resolved if req["expected"] == "예" and state.values.get("decision") == "auto_approved")
    fp = sum(1 for req, state in resolved if req["expected"] == "아니오" and state.values.get("decision") != "auto_approved")

    c1, c2, c3 = st.columns(3)
    c1.metric("개입률", f"{flagged}/{total}")
    c2.metric("놓침 (Miss)", miss)
    c3.metric("헛멈춤 (False Positive)", fp)
else:
    st.caption("판정을 먼저 실행하고, 대기 건을 처리하면 여기 지표가 채워집니다.")
