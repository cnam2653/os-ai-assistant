# tools/interview.py
import asyncio
from typing import Dict, List, Optional
import json
from datetime import datetime
import os
import uuid
from livekit.agents import function_tool, RunContext
import base64

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

class InterviewState:
    def __init__(self):
        self.session_id = None
        self.company = None
        self.interview_type = None
        self.questions = []
        self.current_question_index = 0
        self.responses = []
        self.resume_content = None
        self.interviewer_introduced = False
        self.told_about_self = False

# Global state
interview_state = InterviewState()

@function_tool()
async def start_interview_session(context: RunContext) -> str:
    """Start interview session with introduction"""
    interview_state.session_id = str(uuid.uuid4())[:8]
    interview_state.interviewer_introduced = True
    
    return """Hello! I'm Alex, your interview coach and I'll be conducting your mock interview today.

Before we begin, I'll need a few things from you:

1. **Resume**: Please provide the path to your resume file so I can tailor behavioral questions to your experience.

2. **Tell me about yourself**: Give me a brief introduction about your background, experience, and what you're looking for.

3. **Interview details**: What company are you interviewing for and what type of interview? (behavioral, technical, or both)

Let's start with your resume path, then tell me about yourself. Take your time - I won't interrupt you while you're speaking."""

@function_tool()
async def set_resume_path(context: RunContext, resume_path: str) -> str:
    """Set resume path and load content"""
    try:
        if os.path.exists(resume_path):
            with open(resume_path, 'r', encoding='utf-8') as file:
                interview_state.resume_content = file.read()[:2000]
            return f"Great! I've loaded your resume from {resume_path}. Now please tell me about yourself."
        else:
            return f"Resume file not found at {resume_path}. That's okay - please tell me about yourself and I'll use general questions."
    except Exception as e:
        return f"Couldn't load resume: {str(e)}. No worries - please tell me about yourself."

@function_tool()
async def tell_about_yourself(context: RunContext, introduction: str) -> str:
    """Record user's self-introduction"""
    interview_state.told_about_self = True
    
    return """Thank you for that introduction! 

Now, what company are you interviewing for and what type of interview would you like to practice?

Please specify:
- Company name (e.g., Google, Amazon, Microsoft, etc.)
- Interview type: 'behavioral', 'technical', or 'both'

For example: "Google technical interview" or "Amazon behavioral and technical interview"
"""

@function_tool()
async def setup_interview(context: RunContext, company: str, interview_type: str) -> str:
    """Set up interview with company and type"""
    interview_state.company = company
    interview_state.interview_type = interview_type.lower()
    
    # Generate questions
    if interview_state.interview_type == "both":
        behavioral_questions = _generate_questions(company, "behavioral", 3)
        technical_questions = _generate_questions(company, "technical", 3)
        interview_state.questions = behavioral_questions + technical_questions
    else:
        interview_state.questions = _generate_questions(company, interview_state.interview_type, 5)
    
    interview_state.current_question_index = 0
    
    return f"""Perfect! I've prepared a {interview_type} interview for {company}.

{"For behavioral questions, please use the STAR method (Situation, Task, Action, Result)." if "behavioral" in interview_type else ""}
{"For technical questions, explain your approach, code your solution, and discuss complexity." if "technical" in interview_type else ""}

Are you ready to start? I have {len(interview_state.questions)} questions prepared for you."""

@function_tool()
async def get_next_question(context: RunContext) -> str:
    """Get the next interview question"""
    if interview_state.current_question_index >= len(interview_state.questions):
        return "Interview completed! Use evaluate_interview() to get your final assessment."
    
    question_data = interview_state.questions[interview_state.current_question_index]
    question_num = interview_state.current_question_index + 1
    
    return f"""Question {question_num} of {len(interview_state.questions)}:

{question_data['question']}

{"[BEHAVIORAL] Please use the STAR method in your response." if question_data['type'] == 'behavioral' else ""}
{"[TECHNICAL] Please explain your approach and code your solution." if question_data['type'] == 'technical' else ""}

Take your time to provide a complete answer."""

@function_tool()
async def submit_answer(context: RunContext, answer: str) -> str:
    """Submit answer and get feedback"""
    if interview_state.current_question_index >= len(interview_state.questions):
        return "Interview already completed."
    
    question_data = interview_state.questions[interview_state.current_question_index]
    
    # Store response
    interview_state.responses.append({
        'question': question_data['question'],
        'answer': answer,
        'type': question_data['type'],
        'timestamp': datetime.now().isoformat()
    })
    
    # Get feedback
    feedback = _get_feedback(question_data, answer)
    
    # Move to next question
    interview_state.current_question_index += 1
    
    if interview_state.current_question_index >= len(interview_state.questions):
        return f"{feedback}\n\nInterview completed! Use evaluate_interview() to get your final assessment."
    else:
        return f"{feedback}\n\nReady for the next question? Use get_next_question() when you're ready."

@function_tool()
async def check_code_solution(context: RunContext, screenshot_base64: str, code_description: str) -> str:
    """Check code solution from screenshot using GPT-4V"""
    if not OPENAI_AVAILABLE:
        return "OpenAI not available. Please describe your solution and I'll provide feedback."
    
    try:
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"Please analyze this code solution and provide feedback. The user described it as: {code_description}\n\nCheck for:\n1. Correctness\n2. Efficiency\n3. Code quality\n4. Edge cases\n5. Provide a score out of 10"
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{screenshot_base64}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=500
        )
        
        return f"Code Review:\n{response.choices[0].message.content}"
    except Exception as e:
        return f"Error analyzing code: {str(e)}. Please describe your solution verbally."

@function_tool()
async def evaluate_interview(context: RunContext) -> str:
    """Provide final interview evaluation"""
    if not interview_state.responses:
        return "No interview responses to evaluate."
    
    total_score = 0
    behavioral_count = 0
    technical_count = 0
    
    for response in interview_state.responses:
        if response['type'] == 'behavioral':
            behavioral_count += 1
            score = _score_behavioral_response(response['answer'])
        else:
            technical_count += 1
            score = _score_technical_response(response['answer'])
        total_score += score
    
    avg_score = total_score / len(interview_state.responses)
    
    return f"""
═══════════════════════════════════════
FINAL INTERVIEW EVALUATION - {interview_state.company}
═══════════════════════════════════════

Overall Score: {avg_score:.1f}/10

Performance Summary:
- Questions answered: {len(interview_state.responses)}
- Behavioral questions: {behavioral_count}
- Technical questions: {technical_count}

Rating: {_get_rating(avg_score)}

Strengths:
{_get_strengths(interview_state.responses)}

Areas for Improvement:
{_get_improvement_areas(interview_state.responses)}

Recommendations:
{_get_recommendations(interview_state.company, avg_score)}

Session ID: {interview_state.session_id}
═══════════════════════════════════════
"""

def _generate_questions(company: str, question_type: str, num_questions: int) -> List[Dict]:
    """Generate questions for the interview"""
    if not OPENAI_AVAILABLE:
        return _get_fallback_questions(company, question_type, num_questions)
    
    try:
        if question_type == "behavioral":
            prompt = f"""Generate {num_questions} behavioral interview questions that {company} would actually ask. 
            
            Requirements:
            - Based on {company}'s known interview patterns and values
            - Focus on leadership, teamwork, problem-solving, conflict resolution
            - Include company culture fit questions
            
            Return as JSON array: [{{"question": "text", "type": "behavioral", "category": "leadership/teamwork/etc"}}]"""
        else:
            prompt = f"""Generate {num_questions} technical interview questions that {company} would actually ask.
            
            Requirements:
            - Mix of coding problems, system design, and technical discussions
            - Appropriate for {company}'s technical interview style
            - Include various difficulty levels
            
            Return as JSON array: [{{"question": "text", "type": "technical", "category": "coding/system-design/etc", "difficulty": "easy/medium/hard"}}]"""
        
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an expert interviewer who knows company-specific interview patterns. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.7
        )
        
        questions = json.loads(response.choices[0].message.content)
        return questions
        
    except Exception as e:
        return _get_fallback_questions(company, question_type, num_questions)

def _get_fallback_questions(company: str, question_type: str, num_questions: int) -> List[Dict]:
    """Fallback questions when AI isn't available"""
    if question_type == "behavioral":
        questions = [
            {"question": "Tell me about a time when you had to work with a difficult team member.", "type": "behavioral", "category": "teamwork"},
            {"question": "Describe a situation where you had to make a decision with incomplete information.", "type": "behavioral", "category": "problem-solving"},
            {"question": "Give me an example of when you had to learn something new quickly.", "type": "behavioral", "category": "learning"},
            {"question": "Tell me about a time when you had to meet a tight deadline.", "type": "behavioral", "category": "time-management"},
            {"question": "Describe a situation where you disagreed with your manager.", "type": "behavioral", "category": "conflict-resolution"}
        ]
    else:
        questions = [
            {"question": "Write a function to reverse a string without using built-in methods.", "type": "technical", "category": "coding", "difficulty": "easy"},
            {"question": "Design a URL shortener like bit.ly.", "type": "technical", "category": "system-design", "difficulty": "medium"},
            {"question": "Find the maximum element in a binary tree.", "type": "technical", "category": "coding", "difficulty": "easy"},
            {"question": "Explain the difference between processes and threads.", "type": "technical", "category": "technical-discussion", "difficulty": "medium"},
            {"question": "Design a scalable chat application.", "type": "technical", "category": "system-design", "difficulty": "hard"}
        ]
    
    return questions[:num_questions]

def _get_feedback(question_data: Dict, answer: str) -> str:
    """Get feedback for an answer"""
    if question_data['type'] == 'behavioral':
        score = _score_behavioral_response(answer)
        has_star = any(keyword in answer.lower() for keyword in ['situation', 'task', 'action', 'result'])
        
        feedback = f"""
💡 Feedback (Score: {score}/10):

Strengths:
- {'Good use of STAR method structure' if has_star else 'Clear and direct response'}
- {'Detailed explanation with context' if len(answer) > 100 else 'Concise answer'}

Areas for improvement:
- {'Great structure! Consider adding more quantifiable results' if has_star else 'Try using the STAR method (Situation, Task, Action, Result)'}
- {'Consider more specific examples of your individual impact' if len(answer) < 50 else 'Good detail level'}
"""
    else:
        score = _score_technical_response(answer)
        has_approach = any(keyword in answer.lower() for keyword in ['approach', 'algorithm', 'complexity', 'time', 'space'])
        
        feedback = f"""
Feedback (Score: {score}/10):

Strengths:
- {'Good explanation of approach and complexity' if has_approach else 'Attempted to solve the problem'}
- {'Thorough technical discussion' if len(answer) > 100 else 'Direct answer'}

Areas for improvement:
- {'Consider discussing alternative approaches' if has_approach else 'Always explain your approach and discuss time/space complexity'}
- {'Think about edge cases and optimizations' if len(answer) < 50 else 'Good technical depth'}
"""
    
    return feedback

def _score_behavioral_response(answer: str) -> int:
    """Score behavioral response"""
    score = 5  # Base score
    
    # Check for STAR method
    if any(keyword in answer.lower() for keyword in ['situation', 'task', 'action', 'result']):
        score += 2
    
    # Check length (detail level)
    if len(answer) > 100:
        score += 1
    if len(answer) > 200:
        score += 1
    
    # Check for specific examples
    if any(keyword in answer.lower() for keyword in ['example', 'specifically', 'instance']):
        score += 1
    
    return min(10, score)

def _score_technical_response(answer: str) -> int:
    """Score technical response"""
    score = 5  # Base score
    
    # Check for approach explanation
    if any(keyword in answer.lower() for keyword in ['approach', 'algorithm', 'solution']):
        score += 2
    
    # Check for complexity discussion
    if any(keyword in answer.lower() for keyword in ['complexity', 'time', 'space', 'o(n)']):
        score += 2
    
    # Check for code or pseudocode
    if any(keyword in answer.lower() for keyword in ['function', 'def', 'return', 'if', 'for', 'while']):
        score += 1
    
    return min(10, score)

def _get_rating(score: float) -> str:
    """Get rating based on score"""
    if score >= 8.5:
        return "Excellent - Strong hire recommendation"
    elif score >= 7.5:
        return "Good - Hire with minor improvements"
    elif score >= 6.5:
        return "Average - Needs improvement"
    else:
        return "Below average - Significant improvement needed"

def _get_strengths(responses: List[Dict]) -> str:
    """Get strengths from responses"""
    strengths = []
    
    avg_length = sum(len(r['answer']) for r in responses) / len(responses)
    if avg_length > 100:
        strengths.append("- Provides detailed, comprehensive answers")
    
    behavioral_responses = [r for r in responses if r['type'] == 'behavioral']
    if behavioral_responses:
        star_usage = sum(1 for r in behavioral_responses if any(keyword in r['answer'].lower() for keyword in ['situation', 'task', 'action', 'result']))
        if star_usage > len(behavioral_responses) * 0.5:
            strengths.append("- Good use of STAR method in behavioral responses")
    
    technical_responses = [r for r in responses if r['type'] == 'technical']
    if technical_responses:
        complexity_discussion = sum(1 for r in technical_responses if any(keyword in r['answer'].lower() for keyword in ['complexity', 'time', 'space']))
        if complexity_discussion > 0:
            strengths.append("- Discusses time and space complexity in technical answers")
    
    if not strengths:
        strengths.append("- Completed all interview questions")
        strengths.append("- Maintained engagement throughout the interview")
    
    return '\n'.join(strengths)

def _get_improvement_areas(responses: List[Dict]) -> str:
    """Get areas for improvement"""
    improvements = []
    
    behavioral_responses = [r for r in responses if r['type'] == 'behavioral']
    if behavioral_responses:
        star_usage = sum(1 for r in behavioral_responses if any(keyword in r['answer'].lower() for keyword in ['situation', 'task', 'action', 'result']))
        if star_usage < len(behavioral_responses) * 0.5:
            improvements.append("- Practice using the STAR method more consistently")
    
    technical_responses = [r for r in responses if r['type'] == 'technical']
    if technical_responses:
        complexity_discussion = sum(1 for r in technical_responses if any(keyword in r['answer'].lower() for keyword in ['complexity', 'time', 'space']))
        if complexity_discussion == 0:
            improvements.append("- Always discuss time and space complexity for technical problems")
    
    avg_length = sum(len(r['answer']) for r in responses) / len(responses)
    if avg_length < 50:
        improvements.append("- Provide more detailed examples and explanations")
    
    if not improvements:
        improvements.append("- Continue practicing with more diverse question types")
    
    return '\n'.join(improvements)

def _get_recommendations(company: str, score: float) -> str:
    """Get specific recommendations"""
    recommendations = []
    
    if score < 7:
        recommendations.append(f"- Practice more {company}-specific interview questions")
        recommendations.append("- Focus on providing concrete examples with measurable results")
    
    recommendations.append(f"- Research {company}'s values and recent news")
    recommendations.append("- Practice mock interviews regularly")
    
    return '\n'.join(recommendations)