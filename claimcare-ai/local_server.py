import os
import sys
import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

# 프로젝트 루트 경로
BASE_DIR = Path(__file__).resolve().parent

# calculate 모듈 핸들러 로드
sys.path.append(str(BASE_DIR))
try:
    from api.calculate import generate_insurance_claim
except ImportError:
    generate_insurance_claim = None

class ThreadedAppHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(BASE_DIR), **kwargs)

    def do_POST(self):
        if self.path.startswith("/api/calculate"):
            try:
                content_length = int(self.headers.get("Content-Length", 0))
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data.decode("utf-8"))

                if not generate_insurance_claim:
                    raise RuntimeError("api/calculate.py 모듈을 불러올 수 없습니다.")

                result = generate_insurance_claim(data)

                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type")
                self.end_headers()
                self.wfile.write(json.dumps(result, ensure_ascii=False).encode("utf-8"))

            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                err_res = {"error": str(e), "message": f"분석 오류: {str(e)}"}
                self.wfile.write(json.dumps(err_res, ensure_ascii=False).encode("utf-8"))
        else:
            self.send_error(404, "Not Found")

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

if __name__ == "__main__":
    PORT = 8000
    server = ThreadingHTTPServer(("", PORT), ThreadedAppHandler)
    print("=" * 60)
    print("🚀 [멀티스레드 고속 모드] 클레임케어 AI 서버 실행 중")
    print(f"👉 브라우저 접속: http://localhost:{PORT}")
    print("=" * 60)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n서버를 종료합니다.")
        server.server_close()