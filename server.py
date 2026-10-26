
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
import json, os, mimetypes
import engine

BASE=os.path.dirname(__file__)
WEB=BASE
engine.init_db()

class H(BaseHTTPRequestHandler):
    def send_json(self,obj,status=200):
        b=json.dumps(obj).encode()
        self.send_response(status); self.send_header("Content-Type","application/json"); self.send_header("Content-Length",str(len(b))); self.end_headers(); self.wfile.write(b)
    def body_json(self):
        n=int(self.headers.get("Content-Length","0") or 0); data=self.rfile.read(n) if n else b"{}"
        return json.loads(data.decode() or "{}")
    def do_GET(self):
        p=urlparse(self.path).path
        if p=="/api/cases": return self.send_json(engine.get_cases())
        if p=="/api/audit": return self.send_json(engine.get_audit())
        if p=="/api/tickets": return self.send_json(engine.get_tickets())
        if p=="/api/kpis": return self.send_json(engine.kpis())
        if p.startswith("/api/cases/"):
            cid=p.split("/")[-1]; d=engine.get_case(cid); return self.send_json(d,200 if d else 404)
        file="index.html" if p=="/" else p.lstrip("/")
        fp=os.path.join(WEB,file)
        if not os.path.isfile(fp): self.send_error(404); return
        data=open(fp,"rb").read(); self.send_response(200); self.send_header("Content-Type",mimetypes.guess_type(fp)[0] or "application/octet-stream"); self.send_header("Content-Length",str(len(data))); self.end_headers(); self.wfile.write(data)
    def do_POST(self):
        p=urlparse(self.path).path
        try:
            x=self.body_json()
            if p=="/api/reviews":
                return self.send_json(engine.create_case(str(x.get("review_text","")),str(x.get("source","Web Form")),x.get("rating")))
            if p.startswith("/api/cases/") and p.endswith("/human"):
                cid=p.split("/")[3]
                d=engine.human_decision(cid,str(x.get("decision","")),str(x.get("reviewer_note","")),x.get("corrected_sentiment"),x.get("corrected_issues"),x.get("modified_action"))
                return self.send_json(d)
            return self.send_json({"error":"not found"},404)
        except Exception as e:
            return self.send_json({"error":str(e)},400)

if __name__=="__main__":
    port = int(os.environ.get("PORT", "10000"))
    host = "0.0.0.0"
    print(f"Voice360 running on {host}:{port}")
    ThreadingHTTPServer((host, port), H).serve_forever()
