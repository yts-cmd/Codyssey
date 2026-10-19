# ✈️ AI 기반 국내 여행 일정 추천 플래너 (Travel Planner)

날짜(YYYY-MM-DD)를 입력받아 Google Gemini LLM과 카카오 로컬(지도) API를 결합하여 맞춤형 여행 리포트를 자동 생성하는 CLI 프로그램입니다.

---

## 📌 주요 기능
1. **CLI 날짜 입력 및 정규식 검증**: `argparse`와 정규식을 통해 `YYYY-MM-DD` 형식 유효성 검사
2. **1차 여행지 추천 (Gemini LLM)**: 입력 시기에 적합한 국내 여행지, 날씨 요약, 축제 정보, 추천 근거 추출 (JSON 포맷 강제)
3. **2차 맛집 연동 (Kakao Local API)**: 추천 지역 기반 상위 맛집 5곳의 상세 정보(상호명, 카테고리, 도로명주소, URL, 좌표) 수집
4. **3차 최종 리포트 자동 생성 (Gemini LLM)**: 1~2단계 데이터를 종합하여 1일 추천 일정(오전/오후/저녁)이 포함된 구조화된 Markdown 리포트 생성
5. **결과물 자동 저장**: `results/` 디렉토리에 원본 데이터(`.json`) 및 최종 리포트(`.md`) 자동 저장
6. **예외 처리 및 오류 추적**: API 인증/통신 오류 및 파싱 실패 시 기본값 대체 처리 및 파이프라인 완주 보장

---

## 🛠 기술 스택
- **Language**: Python 3.10+
- **AI Model**: Google Gemini (`gemini-3.8-flash`) via `google-genai`
- **Map/Place API**: Kakao Local Search API
- **Libraries**: `requests`, `python-dotenv`

---

## 📂 디렉토리 구조
```text
travel-planner/
├── .env                  # API 키 설정 (보안상 Git 제외)
├── .gitignore            # Git 추적 제외 설정
├── README.md             # 프로젝트 설명서
├── travel_planner.py     # 메인 실행 스크립트
└── results/              # 생성 결과 저장 디렉토리 (Git 제외)
    ├── 2026-11-15_raw_data.json
    └── 2026-11-15_travel_plan.md