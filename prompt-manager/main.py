# 나만의 프롬프트 관리 프로그램

# 기본 카테고리 목록
CATEGORIES = ["텍스트 생성", "이미지 생성", "영상 생성", "페르소나", "자동화", "기타"]

# 기본 프롬프트 데이터 (최소 3개 등록)
prompts = [
    {
        "title": "블로그 글 작성 도우미",
        "content": "주어진 주제에 대해 SEO에 최적화된 블로그 글을 서론, 본론, 결론 구조로 작성해줘.",
        "category": "텍스트 생성",
        "favorite": True
    },
    {
        "title": "제품 썸네일 생성",
        "content": "쇼핑몰 상세페이지에 어울리는 미니멀하고 고급스러운 제품 썸네일 이미지를 묘사해줘.",
        "category": "이미지 생성",
        "favorite": False
    },
    {
        "title": "IT 컨설턴트 페르소나",
        "content": "너는 15년 차 IT 전략 컨설턴트야. 기업의 클라우드 전환 전략에 대해 전문적으로 조언해줘.",
        "category": "페르소나",
        "favorite": False
    }
]

def show_menu():
    """메인 메뉴 출력 함수"""
    print("\n=== 나만의 프롬프트 관리 ===")
    print("1. 프롬프트 추가")
    print("2. 프롬프트 목록")
    print("3. 카테고리별 조회")
    print("4. 프롬프트 검색")
    print("5. 프롬프트 상세 보기")
    print("6. 즐겨찾기 관리")
    print("7. 즐겨찾기 목록")
    print("0. 종료")
    print("===========================")

def add_prompt():
    """새로운 프롬프트 등록 함수"""
    print("\n=== 프롬프트 추가 ===")
    
    while True:
        title = input("제목: ").strip()
        if title:
            break
        print("[경고] 제목은 비어 있을 수 없습니다. 다시 입력해 주세요.")

    while True:
        content = input("내용: ").strip()
        if content:
            break
        print("[경고] 내용은 비어 있을 수 없습니다. 다시 입력해 주세요.")

    print("\n카테고리 선택:")
    for idx, cat in enumerate(CATEGORIES, 1):
        print(f"{idx}) {cat}")

    while True:
        cat_choice = input("선택: ").strip()
        if cat_choice.isdigit() and 1 <= int(cat_choice) <= len(CATEGORIES):
            category = CATEGORIES[int(cat_choice) - 1]
            break
        print("[경고] 올바른 카테고리 번호를 선택해 주세요.")

    new_item = {
        "title": title,
        "content": content,
        "category": category,
        "favorite": False
    }
    prompts.append(new_item)
    print("\n프롬프트가 성공적으로 추가되었습니다!")

def show_list():
    """저장된 전체 프롬프트 목록 출력 함수"""
    print("\n=== 프롬프트 목록 ===")
    if not prompts:
        print("등록된 프롬프트가 없습니다.")
        return

    for idx, p in enumerate(prompts, 1):
        fav_mark = " ★" if p["favorite"] else ""
        print(f"{idx}. [{p['category']}] {p['title']}{fav_mark}")
        
    print(f"\n총 {len(prompts)}개의 프롬프트")

def show_by_category():
    """선택한 카테고리의 프롬프트만 조회하는 함수"""
    print("\n=== 카테고리별 조회 ===")
    for idx, cat in enumerate(CATEGORIES, 1):
        print(f"{idx}) {cat}")

    while True:
        choice = input("선택: ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(CATEGORIES):
            selected_cat = CATEGORIES[int(choice) - 1]
            break
        print("[경고] 올바른 번호를 선택해 주세요.")

    filtered = [p for p in prompts if p["category"] == selected_cat]

    print(f"\n[{selected_cat}] 카테고리 프롬프트:")
    if not filtered:
        print("해당 카테고리에 등록된 프롬프트가 없습니다.")
        return

    for idx, p in enumerate(filtered, 1):
        fav_mark = " ★" if p["favorite"] else ""
        print(f"{idx}. {p['title']}{fav_mark}")

    print(f"\n총 {len(filtered)}개의 프롬프트")

def search_prompt():
    """키워드로 제목 및 내용을 검색하는 함수"""
    print("\n=== 프롬프트 검색 ===")
    keyword = input("검색어: ").strip()

    if not keyword:
        print("[경고] 검색어를 입력해 주세요.")
        return

    results = [p for p in prompts if keyword in p["title"] or keyword in p["content"]]

    print("\n검색 결과:")
    if not results:
        print("일치하는 프롬프트가 없습니다.")
        return

    for idx, p in enumerate(results, 1):
        fav_mark = " ★" if p["favorite"] else ""
        print(f"{idx}. [{p['category']}] {p['title']}{fav_mark}")

    print(f"\n{len(results)}개의 프롬프트를 찾았습니다.")

def show_detail():
    """프롬프트의 상세 내용을 확인하는 함수"""
    print("\n=== 프롬프트 상세 보기 ===")
    if not prompts:
        print("등록된 프롬프트가 없습니다.")
        return

    num_input = input("번호 입력: ").strip()
    if not num_input.isdigit() or not (1 <= int(num_input) <= len(prompts)):
        print("[경고] 유효한 프롬프트 번호를 입력해 주세요.")
        return

    target = prompts[int(num_input) - 1]
    fav_status = "★ (즐겨찾기)" if target["favorite"] else "☆ (미등록)"

    print(f"\n제목: {target['title']}")
    print(f"카테고리: {target['category']}")
    print(f"즐겨찾기: {fav_status}")
    print("내용:")
    print(target["content"])

def toggle_favorite():
    """프롬프트의 즐겨찾기 상태를 토글(추가/해제)하는 함수"""
    print("\n=== 즐겨찾기 관리 ===")
    if not prompts:
        print("등록된 프롬프트가 없습니다.")
        return

    num_input = input("프롬프트 번호 입력: ").strip()
    if not num_input.isdigit() or not (1 <= int(num_input) <= len(prompts)):
        print("[경고] 유효한 프롬프트 번호를 입력해 주세요.")
        return

    target = prompts[int(num_input) - 1]
    target["favorite"] = not target["favorite"]

    if target["favorite"]:
        print(f"\n'{target['title']}' 프롬프트를 즐겨찾기에 추가했습니다!")
    else:
        print(f"\n'{target['title']}' 프롬프트를 즐겨찾기에서 해제했습니다.")

def show_favorites():
    """즐겨찾기 등록된 프롬프트 목록만 출력하는 함수"""
    print("\n=== 즐겨찾기 목록 ===")
    fav_list = [p for p in prompts if p["favorite"]]

    if not fav_list:
        print("즐겨찾기에 등록된 프롬프트가 없습니다.")
        return

    for idx, p in enumerate(fav_list, 1):
        print(f"{idx}. [{p['category']}] {p['title']}")

    print(f"\n총 {len(fav_list)}개의 즐겨찾기")

def main():
    while True:
        show_menu()
        choice = input("선택: ").strip()

        if choice == "1":
            add_prompt()
        elif choice == "2":
            show_list()
        elif choice == "3":
            show_by_category()
        elif choice == "4":
            search_prompt()
        elif choice == "5":
            show_detail()
        elif choice == "6":
            toggle_favorite()
        elif choice == "7":
            show_favorites()
        elif choice == "0":
            print("프로그램을 종료합니다. 이용해 주셔서 감사합니다.")
            break
        else:
            print("[오류] 잘못된 번호입니다. 다시 입력해 주세요.")

if __name__ == "__main__":
    main()