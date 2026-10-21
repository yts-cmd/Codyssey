import os
import sys
import json
from http.server import HTTPServer, SimpleHTTPRequestHandler
from dotenv import load_dotenv

load_dotenv()

# api/calculate.py의 handler 가져오기
sys.path.append(os.path.join(os.path.dirname(__file__), 'api'))
from calculate import generate_insurance_claim

class LocalDevHandler(SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/api/calculate':
            try:
                content_length = int(self.headers.get('Content-Length', 0))
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data.decode('utf-8'))

                result = generate_insurance_claim(data)

                self.send_response(200)
                self.send_header('Content-type', 'application/json; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(result, ensure_ascii=False).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                err_res = {"error": str(e), "message": f"오류 발생: {str(e)}"}
                self.wfile.write(json.dumps(err_res, ensure_ascii=False).encode('utf-8'))
        else:
            self.send_error(404, "Not Found")

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

if __name__ == '__main__':
    port = 8000
    server_address = ('', port)
    httpd = HTTPServer(server_address, LocalDevHandler)
    print(f"==================================================")
    print(f"🚀 클레임케어 AI 로컬 서버가 시작되었습니다!")
    print(f"👉 브라우저 주소창에 접속하세요: http://localhost:{port}")
    print(f"👉 종료하려면 터미널에서 Ctrl + C 를 누르세요.")
    print(f"==================================================")
    httpd.serve_forever()
