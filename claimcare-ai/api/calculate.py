import json
import os
import re
import base64
import time
from pathlib import Path
from http.server import BaseHTTPRequestHandler
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

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

    print("\n[AI 엔진] 1. Gemini 클라이언트 초기화...")
    client = genai.Client(api_key=api_key)
    
    images = data.get("images", [])
    if not images and data.get("imageData"):
        images = [data.get("imageData")]

    treatment_type = data.get("treatmentType", "외래 통원")
    generation = data.get("generation", "1~2세대 표준화 실손 (2017년 3월 이전)")

    if images:
        print(f"[AI 엔진] 2. 이미지 {len(images)}장 디코딩 준비...")
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

        prompt = """당신은 대한민국 진료비 영수증 전문 OCR 분석 손해사정 AI입니다.
첨부된 영수증들을 판독하여 다음 JSON 형식으로만 즉각 응답하세요 (백틱이나 설명 없이 JSON만 출력):

{
  "daily_breakdown": [
    {
      "date": "2026-10-19",
      "type": "hospital",
      "total_paid": 207000,
      "copay": 7000,
      "non_covered": 200000,
      "excluded_fees": 0,
      "description": "요추 MRI 검사"
    },
    {
      "date": "2026-10-19",
      "type": "pharmacy",
      "total_paid": 6400,
      "copay": 6400,
      "non_covered": 0,
      "excluded_fees": 0,
      "description": "처방 약제비"
    },
    {
      "date": "2026-10-20",
      "type": "hospital",
      "total_paid": 193100,
      "copay": 99100,
      "non_covered": 91000,
      "excluded_fees": 3000,
      "description": "신경차단술 및 주사치료 (서류발급비 3,000원)"
    }
  ],
  "symptoms": "요추 추간판탈출증/요통 (MRI 검사 및 신경차단술, 약국 처방)",
  "required_documents": [
    "진료비 영수증 원본",
    "진료비 세부내역서",
    "질병분류기호(M코드) 기재 처방전 또는 진료확인서",
    "MRI 판독결과지"
  ],
  "advisor_tips": [
    "제증명서 발급비용은 실손 약관상 보상 제외 항목입니다.",
    "처방조제 약제비는 1일 공제금액(8,000원) 미만 시 지급 대상에서 제외됩니다.",
    "통원 진료는 방문 일자별로 각각 15,000원씩 독립 공제됩니다."
  ]
}
"""
        contents_parts.append(prompt)

        # UI에서 확인된 최신 모델 적용
        candidate_models = ["gemini-3.8-flash", "gemini-3.1-pro"]
        response = None
        last_error = None

        print("[AI 엔진] 3. 최신 Gemini 모델 호출 시작...")
        start_time = time.time()

        for model_name in candidate_models:
            try:
                print(f"[AI 엔진] ➡️ '{model_name}' 모델 호출 중...")
                response = client.models.generate_content(
                    model=model_name,
                    contents=contents_parts,
                    config=types.GenerateContentConfig(temperature=0.1)
                )
                print(f"[AI 엔진] ✅ '{model_name}' 응답 성공! (소요시간: {time.time() - start_time:.2f}초)")
                break
            except Exception as e:
                print(f"[AI 엔진] ⚠️ '{model_name}' 호출 실패: {e}")
                last_error = e
                time.sleep(1)

        if not response:
            raise RuntimeError(f"모든 지원 모델 호출에 실패했습니다: {last_error}")

        ai_data = extract_json(response.text)

        # -------------------------------------------------------------
        # [파이썬 손해사정 확정 계산 로직]
        # -------------------------------------------------------------
        daily_list = ai_data.get("daily_breakdown", [])
        total_cost = 0
        total_payout = 0
        basis_logs = []

        total_copay = 0
        total_non_covered = 0

        for item in daily_list:
            cost = item.get("total_paid", 0)
            item_type = item.get("type", "hospital")
            excluded = item.get("excluded_fees", 0)
            dt = item.get("date", "해당일")
            total_cost += cost
            total_copay += item.get("copay", 0)
            total_non_covered += item.get("non_covered", 0)

            claimable = max(0, cost - excluded)

            if item_type == "pharmacy":
                if claimable > 8000:
                    payout = claimable - 8000
                    basis_logs.append(f"{dt} 약국 {cost:,}원 (8,000원 공제 후 {payout:,}원)")
                else:
                    payout = 0
                    basis_logs.append(f"{dt} 약국 {cost:,}원 (8,000원 미달 부지급)")
            else:
                deduct = 15000
                if "4세대" in generation:
                    deduct = max(int(item.get("copay", 0) * 0.2) + int(item.get("non_covered", 0) * 0.3), 20000)
                elif "3세대" in generation:
                    deduct = max(int(item.get("copay", 0) * 0.1) + int(item.get("non_covered", 0) * 0.2), 15000)
                
                payout = max(0, claimable - deduct)
                ex_text = f" (서류비 {excluded:,}원 제외)" if excluded > 0 else ""
                basis_logs.append(f"{dt} 병원 {cost:,}원{ex_text} - 공제 {deduct:,}원 = {payout:,}원")

            total_payout += payout

        total_deductible = total_cost - total_payout
        payout_ratio = round((total_payout / total_cost) * 100) if total_cost > 0 else 0

        print(f"[AI 엔진] 4. 정산 완료: 총 진료비 {total_cost:,}원 / 지급 예정액 {total_payout:,}원")

        return {
            "ocr_detected": {
                "copay_cost": total_copay,
                "non_covered_cost": total_non_covered,
                "symptoms": ai_data.get("symptoms", "척추 및 관절 질환")
            },
            "summary": {
                "total_cost": total_cost,
                "deductible_amount": total_deductible,
                "expected_payout": total_payout,
                "payout_ratio": payout_ratio
            },
            "calculation_basis": " / ".join(basis_logs) + f" -> 최종 예상 지급액: {total_payout:,}원 (실부담금: {total_deductible:,}원)",
            "required_documents": ai_data.get("required_documents", [
                "진료비 영수증 원본", "진료비 세부내역서", "처방전 또는 진료확인서"
            ]),
            "advisor_tips": ai_data.get("advisor_tips", [
                "제증명서 발급비용은 실손 약관상 보상 제외 항목입니다.",
                "통원 진료는 방문 일자별로 각각 15,000원씩 독립 공제됩니다."
            ])
        }

    else:
        copay_cost = int(data.get("copayCost", 0))
        non_covered_cost = int(data.get("nonCoveredCost", 0))
        total_cost = copay_cost + non_covered_cost
        deduct = 15000
        payout = max(0, total_cost - deduct)

        return {
            "ocr_detected": None,
            "summary": {
                "total_cost": total_cost,
                "deductible_amount": deduct,
                "expected_payout": payout,
                "payout_ratio": 90
            },
            "calculation_basis": f"수동 입력 기준: 총 진료비 {total_cost:,}원 - 통원 1회 공제 {deduct:,}원 = {payout:,}원",
            "required_documents": ["진료비 영수증", "진료비 세부내역서"],
            "advisor_tips": ["실제 청구 시 서류발급비 등 비보상 항목 유무를 확인하세요."]
        }

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
            err_res = {"error": str(e), "message": f"분석 오류: {str(e)}"}
            self.wfile.write(json.dumps(err_res, ensure_ascii=False).encode('utf-8'))

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()