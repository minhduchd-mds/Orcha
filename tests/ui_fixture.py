"""Isolated UI fixture. Model responses are fake; external MCP execution is blocked."""
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT=Path(__file__).resolve().parents[1]


def main():
    with tempfile.TemporaryDirectory(prefix='orcha-ui-') as directory:
        os.environ['ORCHA_DATA_DIR']=directory
        sys.path.insert(0,str(ROOT/'app'))
        import studio_server_v70 as app
        import mcp_transport
        import workflow_engine
        workflow_engine.ensure()
        mcp_transport.call=lambda *_args,**_kwargs:{'isError':True,'content':[{'type':'text','text':'UI fixture blocks external tool execution'}]}
        class Ollama(BaseHTTPRequestHandler):
            def respond(self,obj):
                raw=json.dumps(obj).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
            def do_GET(self):self.respond({'models':[{'name':'qwen3:0.6b-q4_K_M'},{'name':'orcha-v3:latest'},{'name':'moondream:1.8b-v2-q2_K'}]})
            def do_POST(self):
                body=json.loads(self.rfile.read(int(self.headers.get('Content-Length',0))));prompt=body.get('messages',[{}])[-1].get('content','')
                answer='[]' if 'tool planner' in prompt else 'Kết quả kiểm thử giao diện Orcha. Đây là dữ liệu giả lập.'
                if 'JSON' in prompt and 'tool planner' not in prompt:answer=json.dumps({'summary':'Fixture analysis','components':[{'type':'button','label':'Save','evidence':'Fixture'}],'issues':[],'tokens':{},'flow':{}})
                self.respond({'message':{'content':answer}})
            def log_message(self,*args):pass
        fake=ThreadingHTTPServer(('127.0.0.1',0),Ollama);threading.Thread(target=fake.serve_forever,daemon=True).start()
        server=ThreadingHTTPServer(('127.0.0.1',11437),app.H70);server.ollama=f'http://127.0.0.1:{fake.server_port}';server.profile='balanced';server.model='orcha-v3';server.model_mode='auto'
        print('UI fixture ready: http://127.0.0.1:11437 (temporary storage, fake model)',flush=True)
        try:server.serve_forever()
        finally:server.server_close();fake.shutdown();fake.server_close()

if __name__=='__main__':main()
