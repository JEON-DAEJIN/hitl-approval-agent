"""재고 자동 발주 승인 — 합성 발주 요청 10건.

강의(N044) 3장의 환불 R1~R5 표와 같은 형식: 건 / 수치 / 사유 / 정답(사람이 봐야 하나).
승인 기준 2개(둘 다 규칙 기반, LLM 호출 없음):
  ① 발주액이 1,000,000원을 초과하면 멈춘다
  ② 수량이 평소 주문량(avg_qty)의 2배를 초과하면 멈춤다
"""

REQUESTS = [
    {"id": "P1", "item": "A4 복사용지", "amount": 180_000, "qty": 20, "avg_qty": 20, "reason": "정기 소모품 재발주", "expected": "아니오"},
    {"id": "P2", "item": "사무용 의자", "amount": 850_000, "qty": 10, "avg_qty": 10, "reason": "분기 정기 교체", "expected": "아니오"},
    {"id": "P3", "item": "노트북", "amount": 4_200_000, "qty": 3, "avg_qty": 3, "reason": "신규 입사자용", "expected": "예"},
    {"id": "P4", "item": "포장 박스", "amount": 320_000, "qty": 500, "avg_qty": 200, "reason": "이벤트 특수 물량 대비", "expected": "예"},
    {"id": "P5", "item": "모니터", "amount": 1_050_000, "qty": 5, "avg_qty": 5, "reason": "정기 교체", "expected": "예"},
    {"id": "P6", "item": "커피 원두", "amount": 210_000, "qty": 30, "avg_qty": 15, "reason": "탕비실 소모품", "expected": "예"},
    {"id": "P7", "item": "마우스", "amount": 90_000, "qty": 15, "avg_qty": 15, "reason": "소모품 정기 보충", "expected": "아니오"},
    {"id": "P8", "item": "택배 봉투", "amount": 60_000, "qty": 1000, "avg_qty": 400, "reason": "성수기 대비 대량 발주", "expected": "예"},
    {"id": "P9", "item": "서버 부품", "amount": 2_300_000, "qty": 2, "avg_qty": 2, "reason": "장애 대응 긴급 교체", "expected": "예"},
    {"id": "P10", "item": "볼펜", "amount": 45_000, "qty": 50, "avg_qty": 50, "reason": "정기 소모품", "expected": "아니오"},
]
