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

cofounder_route = Blueprint('cofounder_route', __name__, url_prefix='/api/cofounder_route')

ALLOWED_EXTENSIONS = {
    'pdf', 'doc', 'docx', 'txt', 'csv',
    'xls', 'xlsx', 'html', 'mp3', 'mp4',
    'wav', 'avi', 'mkv', 'flv', 'mov'
}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@cofounder_route.route('/chat', methods=['POST'])
@handle_errors
def cofounder_chat():
    """
    Option 3: 'Your AI-powered co-founder'
    - Up to 2 PDF files, 2 YouTube links, 1 Wikipedia title
    - Respond as a co-founder, only using the provided resources if they are present.
    - If no references are provided, still respond in a supportive, professional co-founder tone.
    """
    data = request.form
    username = data.get('username', 'anonymous_user')
    question = data.get('question', '').strip()

    if not question:
        return jsonify({"error": "Question is required."}), 400

    # Ensure user conversation history
    if username not in user_history:
        user_history[username] = []

    # Gather user inputs
    yt_links = [data.get(f'youtube_link{i}') for i in range(1, 3) if data.get(f'youtube_link{i}')]
    wiki_titles = [data.get(f'wikipedia_title{i}') for i in range(1, 2) if data.get(f'wikipedia_title{i}')]
    uploaded_files = [request.files.get(f'uploaded_file{i}') for i in range(1, 3) if request.files.get(f'uploaded_file{i}')]

    # Build reference content
    references = []



    # File references
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

    # Combine all references into one big string
    combined_refs = "\n\n".join(references)

    # Role prompt as AI Co-Founder with Enhanced Conversation Capabilities
    role_prompt = (
        "You are the user's AI-powered co-founder. "
        "Engage in basic conversational interactions such as greetings (e.g., 'Hi,' 'Hello,' 'How are you?'). "
        "When responding to queries, use a collaborative, forward-thinking voice and offer detailed, professional insights. "
        "Use ONLY the user's provided references for factual information. "
        "If the document mentions something without a reference, provide the appropriate reference yourself. "
        "Do NOT generate any hypothetical situations or discuss topics outside of the provided document. "
        "If there are no references or if the references do not address the question, "
        "politely state any limits and provide your best co-founder guidance or clarifications based solely on the available data. "
        "Maintain a supportive tone, but stay grounded in actual data or disclaim when data is unavailable.\n\n"
    )

    # Build conversation context
    convo_str = ""
    for entry in user_history[username][-CONVERSATION_HISTORY_LIMIT:]:
        q = entry['question']
        a = entry['answer']
        convo_str += f"User: {q}\nDev (Co-Founder): {a}\n"

    # Final prompt for the model with Enhanced Instructions
    final_prompt = (
        f"{role_prompt}"
        f"Conversation so far:\n{convo_str}\n\n"
        f"Reference content:\n{combined_refs if combined_refs else '[No references provided.]'}\n\n"
        f"User's current question:\n{question}\n\n"
        f"Instructions:\n"
        f"- Engage in basic greetings and small talk when appropriate (e.g., 'Hi,' 'Hello,' 'How are you?').\n"
        f"- Provide a detailed, professional co-founder style answer based ONLY on the provided references.\n"
        f"- If the document mentions a topic without a reference, supply the appropriate reference yourself.\n"
        f"- Do NOT generate hypothetical situations or introduce information outside of the provided document.\n"
        f"- If references are empty or don't answer the question, politely state the limitations and offer helpful guidance based solely on available data.\n"
        f"- Keep the response collaborative and supportive.\n"
    )

    # Generate the answer using Google Generative AI
    try:
        from google.generativeai import GenerativeModel
        model = GenerativeModel("gemini-pro")
        response = model.generate_content(final_prompt)
        bot_answer = response.text.strip() if response and response.text else (
            "I’m sorry, but I couldn’t generate a response at this time."
        )
    except Exception as e:
        logging.error(f"Error generating content for Option 3 (cofounder_chat): {e}")
        bot_answer = "An error occurred while generating your co-founder response."

    # Save the question and answer in the user's conversation history
    user_history[username].append({"question": question, "answer": bot_answer})

    return jsonify({"answer": bot_answer})