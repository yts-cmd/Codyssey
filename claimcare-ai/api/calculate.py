import json
import os
import re
import base64
from pathlib import Path
from http.server import BaseHTTPRequestHandler
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

# 로컬 약관 데이터베이스 로드 함수
def load_clauses_db() -> dict:
    # api/calculate.py 위치 기준 상위 폴더의 clauses_db.json 탐색
    base_dir = Path(__file__).resolve().parent.parent
    db_path = base_dir / "clauses_db.json"
    
    # 배포 환경 또는 경로 대비 예외 처리
    if not db_path.exists():
        db_path = Path("clauses_db.json")

    if db_path.exists():
        with open(db_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

# 1차 로컬 DB 검색 및 정량 약관 산출기
def query_local_clause(db: dict, generation: str, treatment_type: str, copay_cost: int, non_covered_cost: int) -> dict:
    gen_key = "4세대"
    if "3세대" in generation:
        gen_key = "3세대"
    elif "1~2세대" in generation or "2세대" in generation or "1세대" in generation:
        gen_key = "1_2세대"

    gen_info = db.get("generations", {}).get(gen_key, {})
    
    # 1차 공제 규칙 매칭
    is_special = "도수치료" in treatment_type or "체외충격파" in treatment_type
    
    if gen_key == "4세대":
        # 4세대: 급여 20%, 비급여 30% (통원 최소공제 적용)
        copay_deduct = max(int(copay_cost * 0.20), 10000) if copay_cost > 0 else 0
        non_covered_deduct = max(int(non_covered_cost * 0.30), 30000) if non_covered_cost > 0 else 0
        deductible_total = copay_deduct + non_covered_deduct
    elif gen_key == "3세대":
        # 3세대: 급여 10~20%, 비급여 20% (도수치료 특약은 30% 또는 2만원 중 큰 금액)
        copay_deduct = max(int(copay_cost * 0.10), 10000) if copay_cost > 0 else 0
        if is_special:
            non_covered_deduct = max(int(non_covered_cost * 0.30), 20000) if non_covered_cost > 0 else 0
        else:
            non_covered_deduct = max(int(non_covered_cost * 0.20), 15000) if non_covered_cost > 0 else 0
        deductible_total = copay_deduct + non_covered_deduct
    else:
        # 1~2세대: 고정 공제 위주 (통원 1만~1.5만)
        deductible_total = min(15000, copay_cost + non_covered_cost) if (copay_cost + non_covered_cost) > 0 else 0

    total_cost = copay_cost + non_covered_cost
    expected_payout = max(0, total_cost - deductible_total)

    # 필요 서류 매핑
    docs = list(db.get("required_documents_guide", {}).get("기본_통원", []))
    if is_special or non_covered_cost > 0:
        docs.extend(db.get("required_documents_guide", {}).get("비급여특약_추가", []))
    if "입원" in treatment_type:
        docs.extend(db.get("required_documents_guide", {}).get("입원_추가", []))

    return {
        "clause_matched": gen_info,
        "pre_calculated": {
            "total_cost": total_cost,
            "deductible_amount": deductible_total,
            "expected_payout": expected_payout
        },
        "standard_documents": docs
    }

def extract_json(text: str) -> dict:
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        clean_text = match.group(0)
    else:
        clean_text = text.replace("```json", "").replace("```", "").strip()
    return json.loads(clean_text)

def generate_insurance_claim(data: dict) -> dict:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY가 환경변수에 설정되지 않았습니다.")

    client = genai.Client(api_key=api_key)
    
    images = data.get("images", [])
    if not images and data.get("imageData"):
        images = [data.get("imageData")]

    treatment_type = data.get("treatmentType", "외래 통원")
    generation = data.get("generation", "4세대")
    copay_cost = int(data.get("copayCost", 0))
    non_covered_cost = int(data.get("nonCoveredCost", 0))
    symptoms = data.get("symptoms", "")

    # [단계 1] 로컬 JSON DB에서 1차 약관 데이터 검색 및 기준 산출
    db = load_clauses_db()
    local_review = query_local_clause(db, generation, treatment_type, copay_cost, non_covered_cost)

    # [단계 2] Gemini API를 활용한 2차 심층 검토 (영수증 OCR 판독 + 로컬 약관 기준 교차 검증)
    if images:
        contents_parts = []
        for img_str in images:
            mime_type = "image/jpeg"
            if "," in img_str:
                header, base64_str = img_str.split(",", 1)
                if "png" in header:
                    mime_type = "image/png"
            else:
                base64_str = img_str

            contents_parts.append(
                types.Part.from_bytes(
                    data=base64.b64decode(base64_str),
                    mime_type=mime_type,
                )
            )

        prompt = f"""당신은 병원 진료비 영수증 전문 다중 문서 OCR 및 실손보험 보상 심사 손해사정 AI입니다.
우선 내부 데이터베이스에서 검색된 [해당 약관 기준]을 엄격히 준수하여 최종 심사를 진행하세요.

[로컬 DB에서 검색된 약관 기준 및 1차 산출치]
- 적용 상품: {local_review['clause_matched'].get('name', generation)}
- 약관 공제 규칙: {json.dumps(local_review['clause_matched'].get('deductible_rule', {}), ensure_ascii=False)}
- 비급여 특약 기준: {json.dumps(local_review['clause_matched'].get('special_treatments', {}), ensure_ascii=False)}
- 1차 계산 예상치: 총진료비 {local_review['pre_calculated']['total_cost']}원, 자기부담금 {local_review['pre_calculated']['deductible_amount']}원, 예상환급금 {local_review['pre_calculated']['expected_payout']}원

[지침]
1. 첨부된 {len(images)}장의 서류(영수증/세부내역서)에서 실제 급여 본인부담금과 비급여 발생금액 총합, 진단 치료명을 정밀 판독(OCR)하세요.
2. 판독된 금액이 사용자의 입력값과 차이가 있다면 영수증 실금액을 우선하여 위의 [로컬 DB 약관 기준]에 따라 자기부담금과 환급금을 재조정하세요.
3. 반드시 아래 JSON 형식으로만 응답하세요 (백틱 없이 JSON만 출력):

{{
  "ocr_detected": {{
    "copay_cost": 25000,
    "non_covered_cost": 120000,
    "symptoms": "요통, 방사선 검사, 도수치료"
  }},
  "summary": {{
    "total_cost": 145000,
    "deductible_amount": 39000,
    "expected_payout": 106000,
    "payout_ratio": 73
  }},
  "calculation_basis": "로컬 약관 DB ({generation})의 공제율과 영수증상 급여/비급여 실금액을 대조하여 산출했습니다.",
  "required_documents": {json.dumps(local_review['standard_documents'], ensure_ascii=False)},
  "advisor_tips": [
    "약관 DB 조회 결과 확인된 보상 한도 유의사항",
    "보험사 현장 심사 방어 팁"
  ]
}}
"""
        contents_parts.append(prompt)
        response = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=contents_parts
        )
    else:
        # 사진 없이 숫자로만 직접 입력한 경우: 로컬 DB 기준을 바탕으로 AI 심사 멘트 생성
        prompt = f"""당신은 대한민국 실손의료보험 손해사정 AI 어드바이저입니다.
내부 약관 DB를 검색하여 산출된 결과는 다음과 같습니다:
- 대상 약관: {local_review['clause_matched'].get('name', generation)}
- 총 진료비: {local_review['pre_calculated']['total_cost']:,}원
- 1차 계산 자기부담금: {local_review['pre_calculated']['deductible_amount']:,}원
- 1차 예상 환급금: {local_review['pre_calculated']['expected_payout']:,}원
- 진단 및 치료 내용: {symptoms}

위 약관 기준을 바탕으로 산출 근거와 손해사정사 관점의 청구 조언을 작성하여 아래 JSON으로만 응답하세요:
{{
  "ocr_detected": null,
  "summary": {{
    "total_cost": {local_review['pre_calculated']['total_cost']},
    "deductible_amount": {local_review['pre_calculated']['deductible_amount']},
    "expected_payout": {local_review['pre_calculated']['expected_payout']},
    "payout_ratio": 70
  }},
  "calculation_basis": "약관 DB 기준 상세 계산 설명",
  "required_documents": {json.dumps(local_review['standard_documents'], ensure_ascii=False)},
  "advisor_tips": [
    "청구 시 유의점", "필수 확인 사항"
  ]
}}
"""
        response = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=prompt
        )

    return extract_json(response.text)

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            result = generate_insurance_claim(data)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.end_headers()
            self.wfile.write(json.dumps(result, ensure_ascii=False).encode('utf-8'))

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            err_res = {"error": str(e), "message": f"오류 발생: {str(e)}"}
            self.wfile.write(json.dumps(err_res, ensure_ascii=False).encode('utf-8'))

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
