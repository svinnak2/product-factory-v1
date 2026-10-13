"""Provider-neutral OpenAI-compatible chat-completions adapter using only Python stdlib."""
import json, os, urllib.request
from .base import ModelAdapter

class OpenAICompatibleAdapter(ModelAdapter):
    def __init__(self):
        self.endpoint=os.environ.get("AI_PDLC_MODEL_ENDPOINT")
        self.key=os.environ.get("AI_PDLC_MODEL_API_KEY")
        self.model=os.environ.get("AI_PDLC_MODEL_NAME")
        self.timeout=int(os.environ.get("AI_PDLC_MODEL_TIMEOUT","120"))
        missing=[n for n,v in [("AI_PDLC_MODEL_ENDPOINT",self.endpoint),("AI_PDLC_MODEL_API_KEY",self.key),("AI_PDLC_MODEL_NAME",self.model)] if not v]
        if missing: raise RuntimeError("Missing model runtime configuration: "+", ".join(missing))
    def generate(self, *, system, user):
        body={"model":self.model,"messages":[{"role":"system","content":system},{"role":"user","content":user}],
              "temperature":0,"response_format":{"type":"json_object"}}
        req=urllib.request.Request(self.endpoint,data=json.dumps(body).encode(),headers={
            "Authorization":f"Bearer {self.key}","Content-Type":"application/json"})
        with urllib.request.urlopen(req,timeout=self.timeout) as r: data=json.load(r)
        raw=data["choices"][0]["message"]["content"]
        return json.loads(raw)
