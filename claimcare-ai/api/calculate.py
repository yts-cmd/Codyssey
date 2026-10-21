import json
import os
import re
from http.server import BaseHTTPRequestHandler
from google import genai
from dotenv import load_dotenv

load_dotenv()

def extract_json(text: str) -> dict:
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        clean_text = match.group(0)
    else:
        clean_text = text.replace("`json", "").replace("`", "").strip()
    return json.loads(clean_text)

def generate_insurance_claim(data: dict) -> dict:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY가 환경변수에 설정되지 않았습니다.")

    client = genai.Client(api_key=api_key)
    
    treatment_type = data.get("treatmentType", "외래 통원")
    generation = data.get("generation", "4세대")
    copay_cost = int(data.get("copayCost", 0))       # 급여 본인부담금
    non_covered_cost = int(data.get("nonCoveredCost", 0)) # 비급여 진료비
    symptoms = data.get("symptoms", "허리 통증 및 도수치료")
    
    total_cost = copay_cost + non_covered_cost

    prompt = f"""당신은 대한민국 실손의료보험 및 보상 청구 전문 손해사정 AI 어드바이저입니다.
사용자가 병원 진료 후 청구할 내역은 다음과 같습니다:

[환자 진료 및 비용 정보]
- 진료 구분: {treatment_type}
- 가입 실손보험: {generation}
- 급여 본인부담금: {copay_cost:,}원
- 비급여 발생금액: {non_covered_cost:,}원
- 총 발생 의료비: {total_cost:,}원
- 진단 및 치료 내용: {symptoms}

위 정보를 바탕으로 대한민국 실손보험 표준 약관에 근거하여 예상 지급 보험금과 공제 자기부담금을 정밀하게 계산하고,
반드시 아래 JSON 포맷으로만 응답하세요. 백틱이나 부가 설명 없이 오직 JSON만 출력해야 합니다.

{{
  "summary": {{
    "total_cost": {total_cost},
    "deductible_amount": 0,
    "expected_payout": 0,
    "payout_ratio": 0
  }},
  "calculation_basis": "급여 공제 및 비급여 공제 상세 계산 근거를 친절하고 명확하게 서술",
  "required_documents": [
    "필수 제출 서류 1 (예: 진료비 계산서·영수증)",
    "필수 제출 서류 2 (예: 진료비 세부내역서 - 비급여 항목 확인용)",
    "필수 제출 서류 3 (예: 질병분류기호가 기재된 통원확인서 또는 처방전)"
  ],
  "advisor_tips": [
    "청구 시 유의사항 및 보험금 수령 꿀팁 1",
    "비급여 치료(도수치료 등) 심사 기준 관련 팁 2"
  ]
}}
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
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
            err_res = {"error": str(e), "message": "보험금 분석 처리 중 오류가 발생했습니다."}
            self.wfile.write(json.dumps(err_res, ensure_ascii=False).encode('utf-8'))

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
