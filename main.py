from fastapi import FastAPI, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, FileResponse
import json, os, pdfkit
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from agent import TrendAgent
import markdown  # 상단에 추가 필수

app = FastAPI()
templates = Jinja2Templates(directory="templates")
agent = TrendAgent()
DATA_FILE = "interests.json"

# --- 데이터 관리 함수 ---
def load_data():
    if not os.path.exists(DATA_FILE) or os.stat(DATA_FILE).st_size == 0:
        return {"email": "", "interests": {}}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# --- 📧 뉴스레터 자동 발송 스케줄러 설정 ---
def send_daily_newsletter():
    data = load_data()
    user_email = data.get("email")
    interests = data.get("interests", {})
    
    if not user_email or not interests:
        print(f"[{datetime.now()}] 발송 실패: 이메일 정보나 관심사가 없습니다.")
        return
    
    print(f"[{datetime.now()}] >>> {user_email}님께 자동 뉴스레터 발송 시뮬레이션 시작!")
    for topic in interests.keys():
        print(f" - {topic} 주제에 대한 최신 리포트 분석 및 전송 준비 완료")
    print(">>> 발송 완료!")

scheduler = BackgroundScheduler()

# 💡 테스트 설정 가이드:
# 현재 시간이 16시 25분이라면 아래를 hour=16, minute=26 으로 수정하세요.
scheduler.add_job(
    send_daily_newsletter, 
    'cron', 
    hour=16,    # <--- 여기를 현재 시간(시)으로 수정
    minute=30   # <--- 여기를 현재 시간 + 1~2분(분)으로 수정
)
scheduler.start()

# --- 라우팅 ---

@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "data": load_data()})

@app.post("/set_email")
async def set_email(email: str = Form(...)):
    data = load_data()
    data["email"] = email
    save_data(data)
    return RedirectResponse(url="/", status_code=303)

@app.post("/add")
async def add(interest: str = Form(...)):
    data = load_data()
    if interest not in data["interests"]:
        data["interests"][interest] = []
        save_data(data)
    return RedirectResponse(url="/", status_code=303)

@app.get("/analyze/{topic}")
async def analyze(request: Request, topic: str):
    report_md = agent.search_and_analyze(topic)
    data = load_data()
    new_entry = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"), 
        "report": report_md, 
        "chats": []
    }
    if topic not in data["interests"]:
        data["interests"][topic] = []
    data["interests"][topic].insert(0, new_entry)
    save_data(data)
    return RedirectResponse(url=f"/history/{topic}/0")

@app.get("/history/{topic}/{index}")
async def view_history(request: Request, topic: str, index: int):
    data = load_data()
    try:
        target_entry = data["interests"][topic][index]
        return templates.TemplateResponse("report.html", {
            "request": request, 
            "topic": topic, 
            "report": target_entry["report"], 
            "chats": target_entry.get("chats", []), 
            "index": index
        })
    except:
        return RedirectResponse(url="/")

@app.post("/chat/{topic}")
async def chat_with_report(topic: str, request: Request):
    body = await request.json()
    user_query = body.get("query")
    data = load_data()
    target_entry = data["interests"][topic][0]
    prompt = f"리포트 내용:\n{target_entry['report']}\n\n질문: {user_query}"
    response = agent.genai_client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
    answer = response.text
    target_entry["chats"].append({"user": user_query, "ai": answer, "time": datetime.now().strftime("%H:%M")})
    save_data(data)
    return {"answer": answer}

@app.post("/delete_topic/{topic}")
async def delete_topic(topic: str):
    data = load_data()
    if topic in data["interests"]:
        del data["interests"][topic]
        save_data(data)
    return RedirectResponse(url="/", status_code=303)

@app.post("/delete_history/{topic}/{index}")
async def delete_history(topic: str, index: int):
    data = load_data()
    if topic in data["interests"]:
        data["interests"][topic].pop(index)
        save_data(data)
    return RedirectResponse(url="/", status_code=303)

@app.get("/download_pdf/{topic}/{index}")
async def download_pdf(topic: str, index: int):
    data = load_data()
    try:
        target = data["interests"][topic][index]
    except (KeyError, IndexError):
        return {"error": "리포트를 찾을 수 없습니다."}
        
    report_md = target["report"]
    
    # 1. 마크다운 기호를 제거하고 HTML 태그로 변환
    # 이 과정에서 ## 는 <h2>로, **는 <strong>으로 바뀝니다.
    report_html = markdown.markdown(report_md, extensions=['extra'])
    
    pdf_filename = f"report_{topic}_{index}.pdf"
    
    # 2. wkhtmltopdf 경로 설정 (설치된 경로로 꼭 확인하세요!)
    path_wkhtmltopdf = r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'
    config = pdfkit.configuration(wkhtmltopdf=path_wkhtmltopdf)
    
    # 3. 다크모드 스타일 시트 적용
    styled_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset='UTF-8'>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap');
            body {{ 
                font-family: 'Noto Sans KR', sans-serif; 
                padding: 50px; 
                background-color: #0f172a; /* 웹 화면과 유사한 다크 배경 */
                color: #e2e8f0;            /* 밝은 글자색 */
                line-height: 1.8; 
            }}
            h1 {{ 
                color: #60a5fa; 
                border-bottom: 2px solid #334155; 
                padding-bottom: 15px; 
                font-size: 32px;
                text-align: center;
            }}
            h2 {{ 
                color: #60a5fa; 
                font-size: 22px; 
                margin-top: 40px; 
                border-left: 5px solid #3b82f6; 
                padding-left: 15px;
                background-color: #1e293b;
                padding-top: 10px;
                padding-bottom: 10px;
            }}
            h3 {{ color: #34d399; font-size: 19px; margin-top: 25px; }}
            ul {{ margin-left: 20px; color: #cbd5e1; }}
            li {{ margin-bottom: 10px; }}
            a {{ color: #fb7185; text-decoration: none; border-bottom: 1px solid #fb7185; }}
            strong {{ color: #ffffff; }}
            .date {{ text-align: right; font-size: 14px; color: #94a3b8; margin-bottom: 20px; }}
            .footer {{ 
                margin-top: 60px; 
                font-size: 12px; 
                color: #64748b; 
                text-align: center; 
                border-top: 1px solid #334155; 
                padding-top: 20px; 
            }}
        </style>
    </head>
    <body>
        <div class="date">분석 일시: {target['date']}</div>
        <h1>{topic} 기술 분석 리포트</h1>
        <div class="content">
            {report_html}
        </div>
        <div class="footer">본 리포트는 Trend-Catcher AI 에이전트(Gemini 2.0 Flash)에 의해 생성되었습니다.</div>
    </body>
    </html>
    """
    
    try:
        options = {
            'page-size': 'A4',
            'margin-top': '20mm',
            'margin-right': '20mm',
            'margin-bottom': '20mm',
            'margin-left': '20mm',
            'encoding': "UTF-8",
            'no-outline': None,
            'quiet': ''
        }
        pdfkit.from_string(styled_html, pdf_filename, configuration=config, options=options)
        return FileResponse(pdf_filename, media_type='application/pdf', filename=pdf_filename)
    except Exception as e:
        print(f"PDF 생성 에러: {e}")
        return {"error": "PDF 생성 실패. wkhtmltopdf 설정을 확인하세요."}