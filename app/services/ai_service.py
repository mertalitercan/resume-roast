from openai import OpenAI
from app.config import get_settings

settings = get_settings()

class AIService:
    def __init__(self):
        self.client = OpenAI(api_key=settings.openai_api_key)
    
    def analyze_resume(self, resume_text: str) -> str:
        """
        Analyze resume using OpenAI GPT-4.
        Returns detailed feedback as a string.
        """
        prompt = f"""You are an expert resume reviewer. Analyze the following resume and provide detailed, actionable feedback.

Focus on:
1. Bullet point structure (Action verb + Task + Result/Impact)
2. Quantifiable metrics (numbers, percentages, scale)
3. ATS keyword optimization
4. Overall clarity and impact
5. Formatting and organization
6. Tell what do you think about the resume in terms of the plausible roles you are applying for.
7. Give a score out of 100 for the resume

(make sure to not use any text effects like ###, **, (for text decoration) * or _ or any other markdown formatting. however, do use emojis and -, +, etc. for better formatting.)


Resume:
{resume_text}

Provide specific suggestions for improvement with examples."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert resume reviewer specializing in helping job seekers improve their resumes."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1500
            )
            
            return response.choices[0].message.content
        
        except Exception as e:
            raise Exception(f"AI analysis failed: {str(e)}")
