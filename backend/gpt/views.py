import os
import openai
from rest_framework.response import Response

from django.http import JsonResponse, StreamingHttpResponse
from rest_framework.decorators import api_view

from src.utils.gpt import get_conversation_answer, get_gpt_title, get_simple_answer

openai.api_key = os.getenv("OPENAI_API_KEY")

@api_view(["GET"])
def gpt_root_view(request):
    return JsonResponse({"message": "GPT endpoint works!"})



@api_view(["POST"])
def get_title(request):
    data = request.data
    title = get_gpt_title(data["user_question"], data["chatbot_response"])
    return JsonResponse({"content": title})



@api_view(["POST"])
def get_answer(request):
    data = request.data
    return StreamingHttpResponse(get_simple_answer(data["user_question"], stream=True), content_type="text/html")



@api_view(["POST"])
def get_conversation(request):
    data = request.data
    return StreamingHttpResponse(
        get_conversation_answer(data["conversation"], data["model"], stream=True), content_type="text/html"
    )

@api_view(["POST"])
def chat_with_gpt(request):
    user_message = request.data.get("message", "")
    
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": user_message}]
        )
        message = response['choices'][0]['message']['content']
        return Response({"response": message})
    except Exception as e:
        return Response({"error": str(e)}, status=500)