import os
import re
import json
import argparse
from datetime import datetime
import requests
from dotenv import load_dotenv
from google import genai

# 1. 환경 변수 로드 (.env)
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
KAKAO_REST_API_KEY = os.getenv("KAKAO_REST_API_KEY")

# 오류 추적 및 리포트 저장용 리스트
errors = []

def check_api_keys():
    """API 키 미설정 시 즉시 종료 및 안내"""
    missing_keys = []
    if not GEMINI_API_KEY:
        missing_keys.append("GEMINI_API_KEY")
    if not KAKAO_REST_API_KEY:
        missing_keys.append("KAKAO_REST_API_KEY")
    
    if missing_keys:
        print(f"[오류] 필수 API 키가 설정되지 않았습니다: {', '.join(missing_keys)}")
        print("프로젝트 루트의 .env 파일에 키를 설정해주세요.")
        print('예시:\nGEMINI_API_KEY="AIzaSy..."\nKAKAO_REST_API_KEY="abc123..."')
        exit(1)

def validate_date(date_str):
    """YYYY-MM-DD 날짜 형식 정규식 검증"""
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        return False
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False

def get_recommendation_from_gemini(client, travel_date, is_retry=False):
    """1단계: Gemini LLM 연동 - 날씨/행사/도시 추천 (JSON 구조화)"""
    prompt = f"""
당신은 대한민국 국내 여행 전문가입니다.
사용자가 입력한 여행 날짜는 '{travel_date}'입니다.
해당 시기에 여행하기 가장 좋은 대한민국 국내 도시 1곳을 추천하고 반드시 아래 JSON 형식으로만 답변하세요.

JSON 스키마:
{{
  "recommended_city": "도시명 (예: 제주, 강릉, 경주)",
  "weather": "해당 시기 일반적 날씨 요약",
  "events": ["행사 또는 축제 후보 1~3개"],
  "reason": "추천 근거 2~4문장"
}}
"""
    try:
        response = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=prompt,
            config={
                "response_mime_type": "application/json"
            }
        )
        text = response.text.strip()
        parsed_json = json.loads(text)
        return parsed_json
    except Exception as e:
        if not is_retry:
            print("  - LLM JSON 파싱 실패, 1회 재시도합니다...")
            return get_recommendation_from_gemini(client, travel_date, is_retry=True)
        else:
            err_obj = {"step": "llm_recommendation", "type": "PARSE_ERROR", "message": str(e)}
            errors.append(err_obj)
            return {
                "recommended_city": "제주",
                "weather": "정보 확인 불가",
                "events": [],
                "reason": "기본 추천 지역으로 대체되었습니다."
            }

def search_restaurants_kakao(city_name):
    """2단계: 카카오 로컬 API 연동 - 맛집 5곳 검색"""
    url = "https://dapi.kakao.com/v2/local/search/keyword.json"
    headers = {"Authorization": f"KakaoAK {KAKAO_REST_API_KEY}"}
    params = {
        "query": f"{city_name} 맛집",
        "category_group_code": "FD6",  # 음식점 카테고리
        "size": 5
    }

    restaurants = []
    try:
        res = requests.get(url, headers=headers, params=params, timeout=5)
        if res.status_code in [401, 403]:
            print("  - 오류: 카카오 인증 실패(401/403). API 키를 확인하세요.")
            errors.append({"step": "place_search", "type": "AUTH_ERROR", "message": f"HTTP {res.status_code}"})
            return restaurants

        res.raise_for_status()
        data = res.json()
        documents = data.get("documents", [])

        if not documents:
            print("  - 검색 결과 0건. 다음 단계로 진행합니다.")
            errors.append({"step": "place_search", "type": "EMPTY_RESULT", "message": f"0 results for {city_name} 맛집"})
            return restaurants

        for doc in documents:
            restaurants.append({
                "name": doc.get("place_name", ""),
                "address": doc.get("road_address_name") or doc.get("address_name", ""),
                "category": doc.get("category_name", ""),
                "url": doc.get("place_url", ""),
                "x": float(doc.get("x", 0)),
                "y": float(doc.get("y", 0))
            })
        print(f"  - 맛집 {len(restaurants)}곳 검색 완료")
        return restaurants

    except Exception as e:
        print(f"  - 맛집 검색 중 통신 오류 발생: {e}")
        errors.append({"step": "place_search", "type": "REQUEST_ERROR", "message": str(e)})
        return restaurants

def generate_final_report(client, travel_date, rec_data, restaurants):
    """3단계: Gemini LLM 연동 - 최종 마크다운 리포트 생성"""
    restaurants_text = ""
    if restaurants:
        for r in restaurants:
            restaurants_text += f"- **{r['name']}** ({r['category']}): {r['address']} [상세보기]({r['url']})\n"
    else:
        restaurants_text = "- 데이터 없음 (장소 검색 결과 0건 또는 호출 실패)\n"

    prompt = f"""
당신은 여행 플래너입니다. 아래 정보를 바탕으로 깔끔한 Markdown 형식의 여행 리포트를 작성하세요.

[여행 정보]
- 여행 일자: {travel_date}
- 추천 지역: {rec_data.get('recommended_city')}
- 날씨 요약: {rec_data.get('weather')}
- 행사/축제: {', '.join(rec_data.get('events', []))}
- 추천 이유: {rec_data.get('reason')}

[맛집 리스트]
{restaurants_text}

[작성 규칙]
리포트의 제목은 '# {travel_date} 국내 여행 추천 리포트'로 시작할 것.
반드시 아래 섹션을 마크다운 헤더(##)로 포함할 것:
## 추천 지역
## 추천 이유
## 날씨 요약
## 행사/축제
## 맛집 추천
## 1일 일정 제안 (오전 / 오후 / 저녁 코스 제안)
## 오류 요약 (오류가 없으면 '특이사항 없음' 표기)
"""
    try:
        response = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=prompt,
        )
        return response.text
    except Exception as e:
        errors.append({"step": "llm_report", "type": "GEN_ERROR", "message": str(e)})
        return f"# {travel_date} 국내 여행 추천 리포트\n\n리포트 생성 중 오류가 발생했습니다: {e}"

def main():
    parser = argparse.ArgumentParser(description="날짜 기반 AI 국내 여행 추천 프로그램")
    parser.add_argument("-date", "--date", required=True, help="여행 날짜 (형식: YYYY-MM-DD)")
    args = parser.parse_args()

    # CLI 날짜 검증
    if not validate_date(args.date):
        print("[입력 오류] 올바른 날짜 형식이 아닙니다.")
        print("사용법: python travel_planner.py --date \"YYYY-MM-DD\" (예: 2026-11-20)")
        return

    # API 키 확인
    check_api_keys()

    # results 폴더 준비
    results_dir = "results"
    os.makedirs(results_dir, exist_ok=True)

    client = genai.Client(api_key=GEMINI_API_KEY)

    # [1/3] 1차 추천 생성 (LLM)
    print("[1/3] 1차 추천 생성 중(LLM)...")
    rec_data = get_recommendation_from_gemini(client, args.date)
    city = rec_data.get("recommended_city", "제주")
    print(f"  - recommended_city: \"{city}\"")

    # [2/3] 맛집 검색 (카카오 로컬 API)
    print("[2/3] 맛집 검색 중(지도/장소 API)...")
    restaurants = search_restaurants_kakao(city)

    # [3/3] 최종 리포트 생성 (LLM)
    print("[3/3] 최종 리포트 생성 중(LLM)...")
    final_report = generate_final_report(client, args.date, rec_data, restaurants)
    print("  - 리포트 생성 완료")

    # 결과 파일 저장 (JSON 및 MD)
    json_path = os.path.join(results_dir, f"{args.date}_raw_data.json")
    raw_payload = {
        "date": args.date,
        "recommendation": rec_data,
        "restaurants": restaurants,
        "errors": errors
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(raw_payload, f, ensure_ascii=False, indent=2)

    md_path = os.path.join(results_dir, f"{args.date}_travel_plan.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(final_report)

    print(f"\n완료! {md_path} 를 확인하세요.")

if __name__ == "__main__":
    main()