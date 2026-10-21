import os
import re
import json
import argparse
from datetime import datetime
import requests
from dotenv import load_dotenv
from google import genai

# 환경변수 로드
load_dotenv()

raw_gemini_key = os.getenv("GEMINI_API_KEY", "")
GEMINI_API_KEY = raw_gemini_key.strip('"').strip("'").strip()

raw_kakao_key = os.getenv("KAKAO_REST_API_KEY", "")
KAKAO_REST_API_KEY = raw_kakao_key.strip('"').strip("'").strip()

# Gemini 클라이언트 초기화
client = genai.Client(api_key=GEMINI_API_KEY)


def validate_date(date_str: str) -> str:
    """YYYY-MM-DD 형식 검증"""
    pattern = r"^\d{4}-\d{2}-\d{2}$"
    if not re.match(pattern, date_str):
        raise argparse.ArgumentTypeError(
            f"[입력 오류] 올바른 날짜 형식이 아닙니다: '{date_str}'. 'YYYY-MM-DD' 형식으로 입력하세요."
        )
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"[입력 오류] 유효하지 않은 달력 날짜입니다: '{date_str}'"
        )
    return date_str


def get_recommendations_from_gemini(date_str: str, max_retries: int = 1) -> dict:
    """[보너스 1] 2~3개 복수 추천 지역 및 여행 테마 도출"""
    prompt = f"""
당신은 대한민국 국내 여행 전문가입니다.
여행 날짜: {date_str}

이 시기(계절감, 날씨, 지역 축제 등)에 가장 방문하기 좋은 국내 여행지 2~3곳을 선정해주세요.
반드시 아래 JSON 형식으로만 응답하고, 마크다운 코드블록(```json 등) 없이 순수 JSON 텍스트만 출력하세요:

{{
  "recommended_cities": [
    {{
      "city_name": "도시명 (예: 강릉, 제주, 여수 등)",
      "weather_summary": "해당 시기 날씨 및 기온 요약",
      "seasonal_highlights": "제철 볼거리, 단풍/꽃/바다 또는 제철 먹거리",
      "festivals": "해당 월/시기 주요 행사 또는 축제",
      "reason": "추천 사유 1~2줄"
    }}
  ]
}}
"""
    for attempt in range(max_retries + 1):
        try:
            response = client.models.generate_content(
                model="gemini-3.8-flash",
                contents=prompt,
            )
            raw_text = response.text.strip()
            # 코드블록 감싸진 경우 제거
            if raw_text.startswith("```"):
                raw_text = re.sub(r"^```(?:json)?\n", "", raw_text)
                raw_text = re.sub(r"\n```$", "", raw_text)
            
            data = json.loads(raw_text)
            if "recommended_cities" in data and isinstance(data["recommended_cities"], list):
                return data
            raise ValueError("JSON 구조에 'recommended_cities' 리스트가 없습니다.")
        except Exception as e:
            if attempt < max_retries:
                print("  - LLM JSON 파싱 실패, 1회 재시도합니다...")
            else:
                print(f"  - LLM 호출 실패: {e}. 기본 추천 목록을 적용합니다.")
                return {
                    "recommended_cities": [
                        {
                            "city_name": "강릉",
                            "weather_summary": "선선하고 맑은 늦가을 날씨",
                            "seasonal_highlights": "안목해변 커피거리 및 경포호 산책",
                            "festivals": "강릉 커피축제 및 해안 산책로 행사",
                            "reason": "동해 바다와 커피, 초당순두부 등 미식을 함께 즐기기 좋은 시기"
                        },
                        {
                            "city_name": "경주",
                            "weather_summary": "쾌적하고 일교차가 큰 가을 날씨",
                            "seasonal_highlights": "보문단지 및 불국사 가을 풍경, 황리단길",
                            "festivals": "경주 신라문화유산 야간 개장",
                            "reason": "역사 유적지와 트렌디한 골목 카페를 함께 만끽할 수 있는 최적의 계절"
                        }
                    ]
                }


def search_kakao_restaurants(city_name: str, count: int = 4) -> list:
    """[보너스 1] 카카오 로컬 검색 API 연동 (도시별 맛집 반복 검색)"""
    url = "https://dapi.kakao.com/v2/local/search/keyword.json"
    headers = {"Authorization": f"KakaoAK {KAKAO_REST_API_KEY}"}
    params = {
        "query": f"{city_name} 맛집",
        "category_group_code": "FD6",  # 음식점 코드
        "size": count,
        "sort": "accuracy"
    }

    try:
        res = requests.get(url, headers=headers, params=params, timeout=5)
        if res.status_code == 200:
            places = res.json().get("documents", [])
            results = []
            for p in places:
                results.append({
                    "place_name": p.get("place_name"),
                    "category_name": p.get("category_name"),
                    "road_address_name": p.get("road_address_name") or p.get("address_name"),
                    "place_url": p.get("place_url"),
                    "x": p.get("x"),
                    "y": p.get("y")
                })
            return results
        elif res.status_code in (401, 403):
            print(f"  - 오류: [{city_name}] 카카오 인증 실패(401/403).")
            return []
        else:
            print(f"  - 오류: [{city_name}] 카카오 API 응답 상태 {res.status_code}")
            return []
    except Exception as e:
        print(f"  - 오류: [{city_name}] 맛집 검색 통신 실패: {e}")
        return []


def generate_final_report(date_str: str, cities_data: list) -> str:
    """[보너스 1] 복수 지역 및 수집된 맛집을 종합하여 마크다운 리포트 생성"""
    context_text = f"여행 일자: {date_str}\n\n"
    for item in cities_data:
        city_info = item["city_info"]
        restaurants = item["restaurants"]
        context_text += f"### 추천 도시: {city_info.get('city_name')}\n"
        context_text += f"- 날씨 요약: {city_info.get('weather_summary')}\n"
        context_text += f"- 계절 하이라이트: {city_info.get('seasonal_highlights')}\n"
        context_text += f"- 축제/행사: {city_info.get('festivals')}\n"
        context_text += f"- 추천 사유: {city_info.get('reason')}\n"
        context_text += "- 카카오 API 검색 맛집:\n"
        for r in restaurants:
            context_text += f"  * [{r['place_name']}]({r['place_url']}) - {r['category_name']} ({r['road_address_name']})\n"
        context_text += "\n"

    prompt = f"""
당신은 여행 리포트 작성을 전문으로 하는 AI 컨설턴트입니다.
아래 제공된 [수집 데이터]를 기반으로, 가독성이 뛰어나고 매력적인 국내 여행 추천 리포트를 마크다운(.md) 형식으로 작성해주세요.

[수집 데이터]
{context_text}

[작성 요구사항]
1. 제목은 `# {date_str} 맞춤형 국내 추천 여행 리포트`로 시작하세요.
2. 각 추천 도시별로 소제목(##)을 구분하여 날씨, 즐길거리, 맛집 리스트를 일목요연하게 정리하세요.
3. 맛집은 카카오 지도 링크(`[상호명](URL)`)와 주소를 포함해 클릭할 수 있게 작성하세요.
4. 각 도시마다 오전/오후/저녁으로 이어지는 '추천 1일 당일치기 코스'를 현실적인 동선으로 제안하세요.
5. 마지막에는 두 도시 중 취향에 따라 선택할 수 있는 '선택 팁(여행자 성향별 추천)'을 덧붙여주세요.
"""
    try:
        response = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=prompt,
        )
        return response.text
    except Exception as e:
        return f"# {date_str} 국내 여행 추천 리포트\n\n리포트 생성 중 오류가 발생했습니다: {e}"


def main():
    parser = argparse.ArgumentParser(description="날짜 기반 AI 국내 여행 플래너 (복수 지역 & 캐싱 지원)")
    parser.add_argument("--date", type=validate_date, required=True, help="여행 날짜 (YYYY-MM-DD)")
    parser.add_argument("--force", action="store_true", help="캐시를 무시하고 API 새로 호출")
    args = parser.parse_args()

    travel_date = args.date
    results_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
    os.makedirs(results_dir, exist_ok=True)

    json_path = os.path.join(results_dir, f"{travel_date}_raw_data.json")
    md_path = os.path.join(results_dir, f"{travel_date}_travel_plan.md")

    # [보너스 2] 결과 캐싱 확인
    if os.path.exists(json_path) and not args.force:
        print(f"✨ [캐시 감지] '{travel_date}' 기존 수집 데이터가 존재합니다.")
        print(f"  - API 호출을 건너뛰고 캐시 파일({json_path})에서 데이터를 로드합니다.")
        with open(json_path, "r", encoding="utf-8") as f:
            combined_data = json.load(f)
    else:
        # [보너스 1] 1단계: 2~3개 복수 추천 지역 추출
        print(f"[1/3] 1차 추천 생성 중(LLM, 2~3개 도시 선정)...")
        rec_data = get_recommendations_from_gemini(travel_date)
        cities = rec_data.get("recommended_cities", [])
        city_names = [c.get("city_name") for c in cities]
        print(f"  - 추천 도시 목록: {', '.join(city_names)}")

        # [보너스 1] 2단계: 각 지역별 맛집 루프 검색 (API 요청 관리)
        print(f"[2/3] 지역별 맛집 검색 중(Kakao Local API)...")
        combined_data = {
            "travel_date": travel_date,
            "generated_at": datetime.now().isoformat(),
            "cities": []
        }
        for city_info in cities:
            c_name = city_info.get("city_name")
            print(f"  - [{c_name}] 맛집 데이터 수집 중...")
            restaurants = search_kakao_restaurants(c_name, count=4)
            print(f"    -> {len(restaurants)}곳 검색 완료")
            combined_data["cities"].append({
                "city_info": city_info,
                "restaurants": restaurants
            })

        # 원본 데이터 JSON 저장 (캐시 파일로 활용)
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(combined_data, f, ensure_ascii=False, indent=2)
        print(f"  - 원본 데이터 JSON 저장 완료: {json_path}")

    # 3단계: 최종 리포트 생성 (LLM)
    print(f"[3/3] 최종 리포트 생성 중(LLM)...")
    report_md = generate_final_report(travel_date, combined_data["cities"])

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(report_md)
    print(f"  - 리포트 생성 완료")

    print(f"\n완료! {md_path} 를 확인하세요.")


if __name__ == "__main__":
    main()