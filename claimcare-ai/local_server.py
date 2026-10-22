import os
import sys
import json
import importlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))

class DynamicAppHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(BASE_DIR), **kwargs)

    def do_POST(self):
        if self.path.startswith("/api/calculate"):
            try:
                content_length = int(self.headers.get("Content-Length", 0))
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data.decode("utf-8"))

                # [핵심] calculate 모듈을 매번 강제로 새로고침하여 캐시 잔여 차단
                if "api.calculate" in sys.modules:
                    calc_module = importlib.reload(sys.modules["api.calculate"])
                else:
                    calc_module = importlib.import_module("api.calculate")

                result = calc_module.generate_insurance_claim(data)

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
    server = ThreadingHTTPServer(("", PORT), DynamicAppHandler)
    print("=" * 60)
    print("🚀 [동적 리로드 적용] 클레임케어 AI 서버 실행 중")
    print(f"👉 브라우저 접속: http://localhost:{PORT}")
    print("=" * 60)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n서버 종료")
        server.server_close()