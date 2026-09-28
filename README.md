# hitl-approval-agent

N044 "사람이 승인하는 에이전트 만들기" 실습과제 — 재고 자동 발주 승인 HITL(Human-in-the-Loop) 파이프라인.

LangGraph의 `interrupt`/`resume`/`checkpointer`/`thread_id` 네 부품으로 위험한 발주 건만 멈춰 사람 승인을 받고, 나머지는 자동 실행한다. 판정은 전부 규칙 기반(금액·수량 비교)이라 LLM 호출이 없다.

## 실행

```bash
uv venv .venv
uv pip install -r requirements.txt --python .venv
.venv/Scripts/streamlit run app.py   # Windows
# .venv/bin/streamlit run app.py     # macOS/Linux
```

## 구성

- `data.py` — 합성 발주 요청 10건
- `graph.py` — HITL 그래프 (판정 → 멈춤 → 승인/반려/수정/재판정 → 실행)
- `app.py` — Streamlit 승인 데모
- `REPORT.md` — 실행 결과·구조도·회고

승인 기준 2개(둘 다 규칙 기반): ① 발주액 1,000,000원 초과 ② 수량이 평소 주문량의 2배 초과.
