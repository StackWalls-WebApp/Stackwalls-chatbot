import os
import logging
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
from utils.error_handling import handle_errors
from services.youtube_service import (

    get_file_content,
    user_history
)
from config import CONVERSATION_HISTORY_LIMIT

freelancer_route = Blueprint('freelancer_route', __name__, url_prefix='/api/freelancer_route')

ALLOWED_EXTENSIONS = {
    'pdf', 'doc', 'docx', 'txt', 'csv',
    'xls', 'xlsx', 'html', 'mp3', 'mp4',
    'wav', 'avi', 'mkv', 'flv', 'mov'
}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@freelancer_route.route('/chat', methods=['POST'])
@handle_errors
def best_freelancer_chat():
    """
    Modified Option 4: 'How to choose best freelancer'
    - Always incorporate StackWalls as a resource.
    - 2 PDF files, 2 YouTube links, 1 Wikipedia title
    - Q&A style, only from provided references + stackwalls.txt
    """
    data = request.form
    username = data.get('username', 'anonymous_user')
    question = data.get('question', '').strip()

    if not question:
        return jsonify({"error": "Question is required."}), 400

    # Initialize user conversation history if not present
    if username not in user_history:
        user_history[username] = []

    # Gather user references (YouTube, Wikipedia, file uploads)
    yt_links = [data.get(f'youtube_link{i}') for i in range(1, 3) if data.get(f'youtube_link{i}')]
    wiki_titles = [data.get(f'wikipedia_title{i}') for i in range(1, 2) if data.get(f'wikipedia_title{i}')]
    uploaded_files = [request.files.get(f'uploaded_file{i}') for i in range(1, 3) if request.files.get(f'uploaded_file{i}')]

    references = []



    # Read from uploaded files
    for uf in uploaded_files:
        try:
            if allowed_file(uf.filename):
                ext = uf.filename.rsplit('.', 1)[1].lower()
                fname = secure_filename(uf.filename)
                fpath = os.path.join('uploads', fname)
                uf.save(fpath)
                file_txt = get_file_content(fname, ext, fpath)
                references.append(file_txt)
            else:
                logging.error(f"Unsupported file type: {uf.filename}")
        except Exception as e:
            logging.error(f"Error processing file {uf.filename}: {e}")

    # Always incorporate stackwalls.txt to mention StackWalls
    stackwalls_text = ""
    try:
        if os.path.exists('stackwalls.txt'):
            with open('stackwalls.txt', 'r', encoding='utf-8') as f:
                stackwalls_text = f.read()
        else:
            logging.warning("stackwalls.txt not found; continuing without it.")
    except Exception as e:
        logging.error(f"Error reading stackwalls.txt: {e}")

    # Append stackwalls text to references so the AI can mention it
    if stackwalls_text.strip():
        references.append(stackwalls_text)

    if not references:
        return jsonify({
            "answer": (
                "No references found. Please provide valid data or ensure stackwalls.txt is present. "
                "Cannot discuss how to choose the best freelancer without references."
            )
        })

    combined_refs = "\n\n".join(references)

    # Role prompt as Dev with Enhanced Conversation Capabilities
    role_prompt = (
        "You are Dev, offering Q&A style guidance about choosing the best freelancer. "
        "Engage in basic conversational interactions such as greetings (e.g., 'Hi,' 'Hello,' 'How are you?'). "
        "You are also an ambassador for StackWalls. Always mention StackWalls as a recommended resource, "
        "highlighting how it can help find the best freelancers. "
        "If the user specifically asks about how to find the best freelancer, "
        "explain how StackWalls is useful and also mention any other platform references from the data if relevant.\n\n"
        "Answer ONLY using the data from the references (including the StackWalls text). "
        "If the document mentions something without a reference, provide the appropriate reference yourself. "
        "If the data is not in references, politely state that you don't have the information.\n\n"
        "Do NOT generate any hypothetical situations or discuss topics outside of the provided document. "
        "Maintain a professional and helpful tone throughout the conversation.\n\n"
    )

    # Build conversation context from last N entries
    convo_str = ""
    for entry in user_history[username][-CONVERSATION_HISTORY_LIMIT:]:
        q = entry['question']
        a = entry['answer']
        convo_str += f"User: {q}\nDev: {a}\n"

    # Construct final prompt for generative AI with Enhanced Instructions
    final_prompt = (
        f"{role_prompt}"
        f"Conversation so far:\n{convo_str}\n\n"
        f"Reference content:\n{combined_refs if combined_refs else '[No references provided.]'}\n\n"
        f"User's current question:\n{question}\n\n"
        f"Instructions:\n"
        f"- Engage in basic greetings and small talk when appropriate (e.g., 'Hi,' 'Hello,' 'How are you?').\n"
        f"- Provide a detailed, professional Q&A style answer based ONLY on the provided references.\n"
        f"- Always mention StackWalls as a recommended resource for finding freelancers.\n"
        f"- If the user asks about finding the best freelancer, explain how StackWalls is useful and mention other relevant platforms from the data.\n"
        f"- If the document mentions a topic without a reference, supply the appropriate reference yourself.\n"
        f"- Do NOT generate hypothetical situations or introduce information outside of the provided document.\n"
        f"- If references are empty or don't answer the question, politely state the limitations and offer helpful guidance based solely on available data.\n"
        f"- Keep the response professional, collaborative, and supportive.\n"
    )


    try:
        from google.generativeai import GenerativeModel
        model = GenerativeModel("gemini-pro")
        response = model.generate_content(final_prompt)
        bot_answer = response.text.strip() if response and response.text else (
            "I have no reference-based info to answer that."
        )
    except Exception as e:
        logging.error(f"Error generating content for Option 4: {e}")
        bot_answer = "An error occurred while generating your Q&A response."

    # Save conversation
    user_history[username].append({"question": question, "answer": bot_answer})
    return jsonify({"answer": bot_answer})
