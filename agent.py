import os
from dotenv import load_dotenv
from google import genai
from tavily import TavilyClient

load_dotenv()

class TrendAgent:
    def __init__(self):
        # 환경변수에서 API 키 로드
        self.genai_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        self.tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

    def search_and_analyze(self, topic: str):
        # 1. 최신 정보 검색
        search_result = self.tavily.search(query=f"latest trends and technical news about {topic}", search_depth="advanced")
        context = "\n".join([f"Source: {r['url']}\nContent: {r['content']}" for r in search_result['results']])

        # 2. 분석 프롬프트 작성
        prompt = f"""
        당신은 IT 기술 분석 전문가입니다. 주제: {topic}
        아래 검색된 내용을 바탕으로 개발자를 위한 '오늘의 기술 뉴스레터'를 작성하세요.
        반드시 Markdown 형식을 사용하고, 제목은 '## 오늘의 기술 뉴스레터: 주제명'으로 시작하세요.
        내용에는 기술적 변화, 수치, 출처 URL을 포함하고 매우 전문적으로 작성하세요.

        [검색 결과]
        {context}
        """
        
        # 3. Gemini 2.0 Flash 모델로 분석 생성
        response = self.genai_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        return response.text