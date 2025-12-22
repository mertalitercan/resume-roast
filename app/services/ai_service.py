from openai import OpenAI
from app.config import get_settings

settings = get_settings()

class AIService:
    def __init__(self):
        self.client = OpenAI(api_key=settings.openai_api_key)
    
    def analyze_resume(self, resume_text: str, job_description: str = None, job_role: str = None) -> str:
        # Build context
        context = ""
        if job_role:
            context += f"\n\nTarget Role: {job_role}"
        if job_description:
            context += f"\n\nJob Description:\n{job_description}"
        
        prompt = f"""You are an expert resume reviewer. Analyze the following resume and provide detailed, actionable feedback.
{context}

Focus on:
1. Bullet point structure (Action verb + Task + Result/Impact)
2. Quantifiable metrics (numbers, percentages, scale)
3. ATS keyword optimization
4. Overall clarity and impact
5. Formatting and organization
6. Alignment with the target role{" and job description" if job_description else ""}
7. Give a final score out of 100

Resume:
{resume_text}

Provide specific suggestions for improvement with examples. End with your score out of 100.

CRITICAL FORMATTING RULES - YOU MUST FOLLOW THESE:
- DO NOT use ** for bold (it doesn't render)
- DO NOT use * for italic (it doesn't render)
- DO NOT use # or ## for headers (it doesn't render)
- DO NOT use _ for underline (it doesn't render)
- DO NOT use markdown syntax at all

INSTEAD USE:
- Use CAPITAL LETTERS for emphasis
- Use emojis for visual breaks (✨ 🎯 📌 ✅ ⚠️ 💡)
- Use dashes - or plus signs + for bullet points
- Use numbers 1. 2. 3. for numbered lists
- Use blank lines to separate sections
- Write plain text only

Example of GOOD formatting:
FEEDBACK:

1. BULLET POINT STRUCTURE
   - Your bullets follow the structure well
   - Example: "Developed a Python script" is good

2. QUANTIFIABLE METRICS  
   ✅ Good: You included metrics like "35%"
   ⚠️  Improvement needed: Add more numbers

Example of BAD formatting (DO NOT DO THIS):
**Feedback:**
**Bullet Point Structure:**
- Your bullets are *good* but could be **better**

Remember: NO ASTERISKS, NO MARKDOWN, PLAIN TEXT ONLY."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4.1",
                messages=[
                    {
                        "role": "system", 
                        "content": "You are an expert resume reviewer. NEVER use markdown formatting. Use plain text with capital letters for emphasis, emojis for visual interest, and blank lines for spacing. Always provide a numerical score out of 100."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            feedback = response.choices[0].message.content
            
            # Safety check: Strip any remaining markdown
            feedback = feedback.replace('**', '')
            feedback = feedback.replace('__', '')
            feedback = feedback.replace('##', '')
            feedback = feedback.replace('###', '')
            
            return feedback
        
        except Exception as e:
            raise Exception(f"AI analysis failed: {str(e)}")