"""NovaLM: a tiny domain-specific Transformer language-understanding model.

This model is trained from scratch on the NovaHR intent corpus. It does not use
Gemini/OpenAI, pretrained weights, or a hosted inference API. The model predicts
an HR intent; the deterministic router remains the safety fallback.
"""
import json, math, re
from pathlib import Path

BASE=Path(__file__).resolve().parent
MODEL_DIR=BASE/"models"
MODEL_PATH=MODEL_DIR/"novalm_intent.pt"
META_PATH=MODEL_DIR/"novalm_meta.json"

INTENT_LABELS=[
"create_employee","delete_employee","update_employee","assign_task","update_task",
"generate_payroll","get_payroll_report","approve_leave","reject_leave","apply_leave",
"cancel_leave","mark_attendance","check_out","get_team_attendance","get_leave_balance",
"get_payroll","get_attendance","get_tasks","get_policy","analyze_performance",
"team_performance","list_employees","get_employee","send_notification","get_notifications",
"mark_notifications_read","profile","department_summary"
]

TEMPLATES={
"create_employee":["add a new employee","create employee account","hire a new employee","onboard new staff","register new employee","add employee with email","create staff profile"],
"delete_employee":["remove employee","deactivate employee","terminate employee","delete staff account","disable an employee"],
"update_employee":["update employee profile","change employee details","edit employee salary","update staff information","change job title"],
"assign_task":["assign task to employee","give Rahul a task","create work for employee","assign new work","set a task for staff"],
"update_task":["mark task done","complete my task","update task status","finish task","change task to in progress"],
"generate_payroll":["generate payroll","process this month's payroll","run payroll","generate payslips","process salaries"],
"get_payroll_report":["show payroll report","salary report","department payroll summary","total payroll","payroll history report"],
"approve_leave":["approve leave","accept leave request","approve pending vacation","grant employee leave"],
"reject_leave":["reject leave","deny leave request","decline pending leave"],
"apply_leave":["apply for leave","request vacation","take sick leave","need leave tomorrow","request time off"],
"cancel_leave":["cancel my leave","withdraw leave request","cancel vacation"],
"mark_attendance":["mark attendance","check in today","punch in","log attendance","start my workday"],
"check_out":["check out","punch out","end my workday","log out from attendance"],
"get_team_attendance":["who is absent today","show team attendance","department attendance","who is present today","team absent employees"],
"get_leave_balance":["how many leaves do I have","show leave balance","remaining vacation","leaves left","available leave days"],
"get_payroll":["show my salary","show payslip","how much did I earn","my payroll","why was my salary deducted"],
"get_attendance":["show my attendance","attendance history","how many days present","am I absent","my attendance report"],
"get_tasks":["show my tasks","pending tasks","assigned work","todo list","show task list"],
"get_policy":["company leave policy","attendance rules","payroll policy","show company policy","what is the leave rule"],
"analyze_performance":["show my performance","performance score","analyze my performance","my work performance"],
"team_performance":["team performance","department performance","employee performance report"],
"list_employees":["list employees","show staff","employee directory","who works here","search employees"],
"get_employee":["employee profile","employee details","show employee information","staff details"],
"send_notification":["send notification to employee","notify staff","send a message to employee","alert employee"],
"get_notifications":["show my notifications","unread alerts","notifications","show alerts"],
"mark_notifications_read":["mark notifications read","clear notifications","read all alerts"],
"profile":["show my profile","my details","who am I","my information"],
"department_summary":["department summary","team overview","department workload","team summary"]}

def corpus():
    rows=[]
    for label,items in TEMPLATES.items():
        for text in items:
            rows.append((text,label))
            rows.append((text+" please",label)); rows.append(("can you "+text,label)); rows.append(("I want to "+text,label))
    return rows

def tokenize(text): return re.findall(r"[a-z0-9@._-]+", text.lower())[:64]

def train(epochs=18):
    try:
        import torch
        import torch.nn as nn
    except ImportError as e:
        raise RuntimeError("PyTorch is required. Install requirements.txt first.") from e
    rows=corpus(); vocab={"<pad>":0,"<unk>":1}
    for text,_ in rows:
        for tok in tokenize(text): vocab.setdefault(tok,len(vocab))
    labels={x:i for i,x in enumerate(INTENT_LABELS)}
    X=torch.tensor([[vocab.get(t,1) for t in tokenize(text)]+[0]*(12-len(tokenize(text))) for text,_ in rows],dtype=torch.long)
    X=X[:,:12]; y=torch.tensor([labels[label] for _,label in rows],dtype=torch.long)
    class NovaLM(nn.Module):
        def __init__(self,vocab_size,nlabels):
            super().__init__(); self.emb=nn.Embedding(vocab_size,96,padding_idx=0); self.pos=nn.Parameter(torch.randn(1,12,96)*.02)
            layer=nn.TransformerEncoderLayer(d_model=96,nhead=4,dim_feedforward=192,dropout=.1,batch_first=True,activation="gelu")
            self.enc=nn.TransformerEncoder(layer,2); self.norm=nn.LayerNorm(96); self.head=nn.Linear(96,nlabels)
        def forward(self,x):
            z=self.emb(x)+self.pos; z=self.enc(z,src_key_padding_mask=x.eq(0)); z=self.norm(z[:,0]); return self.head(z)
    torch.manual_seed(42); model=NovaLM(len(vocab),len(labels)); opt=torch.optim.AdamW(model.parameters(),lr=3e-3,weight_decay=1e-4); loss_fn=nn.CrossEntropyLoss()
    model.train()
    for epoch in range(epochs):
        opt.zero_grad(); logits=model(X); loss=loss_fn(logits,y); loss.backward(); opt.step()
    MODEL_DIR.mkdir(exist_ok=True); torch.save(model.state_dict(),MODEL_PATH)
    META_PATH.write_text(json.dumps({"vocab":vocab,"labels":labels,"model":"NovaLM-1","epochs":epochs},indent=2))
    return {"model":"NovaLM-1","samples":len(rows),"vocab":len(vocab),"intents":len(labels),"loss":round(float(loss.item()),4),"path":str(MODEL_PATH)}

_CACHE=None
def predict_intent(text):
    global _CACHE
    if not MODEL_PATH.exists() or not META_PATH.exists(): return None
    try:
        import torch
        import torch.nn as nn
        meta=json.loads(META_PATH.read_text()); vocab=meta["vocab"]; labels={int(v):k for k,v in meta["labels"].items()}
        class NovaLM(nn.Module):
            def __init__(self,vocab_size,nlabels):
                super().__init__(); self.emb=nn.Embedding(vocab_size,96,padding_idx=0); self.pos=nn.Parameter(torch.zeros(1,12,96)); layer=nn.TransformerEncoderLayer(d_model=96,nhead=4,dim_feedforward=192,dropout=.0,batch_first=True,activation="gelu"); self.enc=nn.TransformerEncoder(layer,2); self.norm=nn.LayerNorm(96); self.head=nn.Linear(96,nlabels)
            def forward(self,x): return self.head(self.norm(self.enc(self.emb(x)+self.pos,src_key_padding_mask=x.eq(0))[:,0]))
        if _CACHE is None:
            model=NovaLM(len(vocab),len(labels)); model.load_state_dict(torch.load(MODEL_PATH,map_location="cpu")); model.eval(); _CACHE=(model,vocab,labels)
        model,vocab,labels=_CACHE; toks=tokenize(text); ids=[vocab.get(t,1) for t in toks]+[0]*(12-len(toks)); ids=torch.tensor([ids[:12]])
        with torch.no_grad(): probs=torch.softmax(model(ids),dim=-1)[0]; conf,idx=torch.max(probs,0)
        return {"intent":labels[int(idx)],"confidence":float(conf)}
    except Exception:
        return None

def status():
    return {"model":"NovaLM-1","trained":MODEL_PATH.exists(),"checkpoint":str(MODEL_PATH),"description":"Small Transformer trained from scratch on NovaHR HR-domain utterances."}
