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

def load_clauses_db() -> dict:
    base_dir = Path(__file__).resolve().parent.parent
    db_path = base_dir / "clauses_db.json"
    if not db_path.exists():
        db_path = Path("clauses_db.json")

    if db_path.exists():
        with open(db_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

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
    generation = data.get("generation", "1~2세대 표준화 실손")
    copay_cost = int(data.get("copayCost", 0))
    non_covered_cost = int(data.get("nonCoveredCost", 0))
    symptoms = data.get("symptoms", "")

    # 1. 로컬 약관 DB 로드
    db = load_clauses_db()
    gen_key = "1_2세대"
    if "4세대" in generation:
        gen_key = "4세대"
    elif "3세대" in generation:
        gen_key = "3세대"
    matched_clause = db.get("generations", {}).get(gen_key, {})

    # 2. Gemini 멀티모달 프롬프트 구성
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

        prompt = f"""당신은 병원 진료비 영수증/진료비 세부내역서/약국 영수증 전문 대한민국 손해사정 심사관 AI입니다.
첨부된 {len(images)}장의 서류 이미지들을 상호 대조하고, 내부 데이터베이스 약관 기준을 적용하여 정밀 심사 및 계산을 수행하세요.

[내부 DB 약관 기준: {matched_clause.get('name', generation)}]
{json.dumps(matched_clause, ensure_ascii=False, indent=2)}

★ [손해사정 실무 심사 및 계산 핵심 원칙 - 엄격 준수] ★
1. 진료 일자별(Day-by-Day) 독립 공제:
   - 외래 통원은 여러 날짜의 영수증 금액을 단순 합산하여 1회만 공제하면 절대 안 됩니다.
   - 영수증 상의 '진료 일자'별로 그룹화하여, 방문 일자마다 각각 1회씩 통원 자기부담금(병원급 15,000원, 의원 10,000원 등)을 독립 차감하세요.
2. 보상 제외 항목 엄격 분리:
   - 영수증 내 '제증명료', '진료확인서/진단서/소견서 발급비'(예: 3,000원 등)는 의료비가 아니므로 보상 대상 금액에서 전액 제외하세요.
3. 원외처방 약제비 분리 심사:
   - 약국 영수증 조제비는 병원비와 합산하지 말고 별도로 심사하세요.
   - 약제비 발생금액이 1일 최소 공제금액(8,000원) 미만(예: 6,400원)인 경우 지급 보험금은 0원(청구 실익 없음)으로 계산하세요.
4. 환자 실부담액 정합성:
   - 총 발생비용 = 모든 영수증 총액
   - 예상 지급 보험금 = 각 일자별 (보상대상액 - 일자별 공제금)의 합계
   - 공제 자기부담금 = 총 발생비용 - 예상 지급 보험금 (보상제외 서류비, 일자별 공제금, 약제비 공제 미달분 포함)

반드시 아래 JSON 형식으로만 응답하세요 (백틱 없이 JSON만 출력):
{{
  "ocr_detected": {{
    "copay_cost": 106100,
    "non_covered_cost": 291000,
    "symptoms": "요추 추간판탈출증/요통(MRI 검사), 신경차단술 주사치료, 약국 처방"
  }},
  "summary": {{
    "total_cost": 406500,
    "deductible_amount": 39400,
    "expected_payout": 367100,
    "payout_ratio": 90
  }},
  "calculation_basis": "일자별 독립 공제 및 보상 제외 항목 정밀 산출 내역 요약 (예: 10/19 병원 207,000원 - 공제 15,000원 = 192,000원 / 10/19 약국 6,400원 공제 8,000원 미달 부지급 / 10/20 병원 193,100원 중 서류비 3,000원 제외 후 190,100원 - 공제 15,000원 = 175,100원 -> 최종 지급액 367,100원)",
  "required_documents": [
    "진료비 계산서·영수증 원본",
    "진료비 세부내역서",
    "질병분류기호(M코드) 기재된 처방전 또는 진료확인서",
    "MRI 판독결과지"
  ],
  "advisor_tips": [
    "제증명서 발급비용(3,000원)은 실손의료비 약관상 보상 제외 항목입니다.",
    "약국 조제비(6,400원)는 통원 약제비 최소 공제금액(8,000원) 미만으로 지급 대상에서 제외되었습니다.",
    "통원 진료는 방문 일자별로 각각 15,000원씩 독립 공제되었습니다."
  ]
}}
"""
        contents_parts.append(prompt)
        response = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=contents_parts
        )
    else:
        # 사진 없는 수동 입력 시
        prompt = f"""당신은 대한민국 실손보험 손해사정 심사 AI입니다.
가입실손: {generation}, 급여: {copay_cost}원, 비급여: {non_covered_cost}원, 증상: {symptoms}
약관 DB 기준({matched_clause.get('name', generation)})에 근거하여 예상 지급액과 공제액을 정량 계산하고 JSON으로만 응답하세요:
{{
  "ocr_detected": null,
  "summary": {{
    "total_cost": {copay_cost + non_covered_cost},
    "deductible_amount": 15000,
    "expected_payout": {max(0, copay_cost + non_covered_cost - 15000)},
    "payout_ratio": 90
  }},
  "calculation_basis": "약관 DB 기준 산출 설명",
  "required_documents": ["진료비 영수증", "진료비 세부내역서"],
  "advisor_tips": ["청구 시 유의사항"]
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