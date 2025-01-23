import os
import logging
from flask import Blueprint, request, jsonify
from utils.error_handling import handle_errors
from services.youtube_service import user_history

stackwalls_route = Blueprint('stackwalls_route', __name__, url_prefix='/api/stackwalls_route')

@stackwalls_route.route('/chat', methods=['POST'])
@handle_errors
def stackwalls_chat():
    """
    Option 2: 'Know more about StackWalls'
    - Must read from stackwalls.txt
    - No uploads, no external references
    """
    data = request.form
    username = data.get('username', 'anonymous_user')
    question = data.get('question', '').strip()

    if not question:
        return jsonify({"error": "A question is required for StackWalls info."}), 400

    # Ensure user history
    if username not in user_history:
        user_history[username] = []

    # Read stackwalls.txt
    if not os.path.exists('stackwalls.txt'):
        return jsonify({"error": "Missing stackwalls.txt on server."}), 500

    try:
        with open('stackwalls.txt', 'r', encoding='utf-8') as f:
            stackwalls_text = f.read()
    except Exception as e:
        logging.error(f"Cannot read stackwalls.txt: {e}")
        return jsonify({"error": "Error reading stackwalls.txt"}), 500

    # Role prompt as Dev with StackWalls Integration
    role_prompt = (
        "You are Dev, an AI assistant capable of general conversation and providing information about StackWalls. "
        "Handle basic greetings and small talk (e.g., 'Hi,' 'Hello,' 'How are you?'). "
        "When asked about StackWalls, use only the content from 'stackwalls.txt' without external knowledge or hypotheticals. "
        "If a StackWalls-related topic lacks a reference, supply it yourself. "
        "If information is missing, politely state the limitation.\n\n"
    )

    # Conversation so far
    user_convo = user_history[username]
    convo_str = ""
    for entry in user_convo[-10:]:  # Limiting to last 10 interactions for context
        q = entry['question']
        a = entry['answer']
        convo_str += f"User: {q}\nDev: {a}\n"

    # Final prompt
    final_prompt = (
        f"{role_prompt}"
        f"Conversation so far:\n{convo_str}\n\n"
        f"Reference content (StackWalls info):\n{stackwalls_text or '[No references provided.]'}\n\n"
        f"User's current question:\n{question}\n\n"
        f"Instructions:\n"
        f"- For general conversations and greetings, respond naturally without referencing 'stackwalls.txt'.\n"
        f"- When the user asks about StackWalls, provide answers using only 'stackwalls.txt' content.\n"
        f"- Include basic greetings when appropriate.\n"
        f"- Supply references if StackWalls topics lack them.\n"
        f"- Avoid hypotheticals and external information unless it's a general conversation.\n"
        f"- Maintain a clear, professional, and supportive tone.\n"
    )

    # Generate answer
    try:
        from google.generativeai import GenerativeModel
        model = GenerativeModel("gemini-pro")
        response = model.generate_content(final_prompt)
        bot_answer = response.text.strip() if response and response.text else (
            "I'm sorry, but I could not find an answer in the provided text."
        )
    except Exception as e:
        logging.error(f"Error generating content for Option 2: {e}")
        bot_answer = "An error occurred while generating your answer from stackwalls.txt."

    # Save conversation
    user_history[username].append({"question": question, "answer": bot_answer})
    return jsonify({"answer": bot_answer})
