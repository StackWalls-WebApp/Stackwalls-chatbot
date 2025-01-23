import os
import logging
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
from utils.error_handling import handle_errors
from services.youtube_service import (

    answer_question,
    user_history,
    get_wikipedia_content,
    get_file_content
)
from config import CONVERSATION_HISTORY_LIMIT

project_discussion_route = Blueprint('project_discussion_route', __name__, url_prefix='/api/project_discussion_route')

ALLOWED_EXTENSIONS = {
    'pdf', 'doc', 'docx', 'txt', 'csv',
    'xls', 'xlsx', 'html', 'mp3', 'mp4',
    'wav', 'avi', 'mkv', 'flv', 'mov'
}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@project_discussion_route.route('/chat', methods=['POST'])
@handle_errors
def discuss_project_chat():
    """
    Option 1: 'Discuss about project'
    - Up to 2 PDF files
    - 2 YouTube links
    - 1 Wikipedia title
    - Provide strict, purely technical guidance from the user-supplied data.
    """
    data = request.form
    username = data.get('username', 'anonymous_user')
    question = data.get('question', '').strip()

    if not question:
        return jsonify({"error": "Question is required."}), 400

    # Create user conversation history if not present
    if username not in user_history:
        user_history[username] = []

    # Collect the resources
    yt_links = [data.get(f'youtube_link{i}') for i in range(1, 3) if data.get(f'youtube_link{i}')]
    wiki_titles = [data.get(f'wikipedia_title{i}') for i in range(1, 2) if data.get(f'wikipedia_title{i}')]
    uploaded_files = [request.files.get(f'uploaded_file{i}') for i in range(1, 3) if request.files.get(f'uploaded_file{i}')]

    reference_texts = []



    # Process Wikipedia
    for title in wiki_titles:
        try:
            wiki_txt = get_wikipedia_content(title)
            reference_texts.append(wiki_txt)
        except Exception as e:
            logging.error(f"Error processing Wikipedia title {title}: {e}")

    # Process uploaded files
    for uf in uploaded_files:
        try:
            if allowed_file(uf.filename):
                ext = uf.filename.rsplit('.', 1)[1].lower()
                fname = secure_filename(uf.filename)
                fpath = os.path.join('uploads', fname)
                uf.save(fpath)
                file_txt = get_file_content(fname, ext, fpath)
                reference_texts.append(file_txt)
            else:
                logging.error(f"Unsupported file type: {uf.filename}")
        except Exception as e:
            logging.error(f"Error processing file {uf.filename}: {e}")

    # If no references were extracted, respond accordingly
    if not reference_texts:
        return jsonify({
            "answer": "No valid resources found to discuss from. Please provide valid YouTube links, Wikipedia titles, or PDFs."
        })

    combined_text = "\n\n".join(reference_texts)

    # Role prompt as Dev with Enhanced Strict Technical Guidance
    role_prompt = (
        "You are Dev, an extremely strict and purely technical project consultant. "
        "Engage in basic conversational interactions such as greetings (e.g., 'Hi,' 'Hello,' 'How are you?'). "
        "You have the following reference materials from the user (transcripts, documents, wiki entries). "
        "You must NOT use any personal knowledge, imagination, or hypotheticals. "
        "Provide direct, no-nonsense guidance about the user's project based solely on the given reference materials. "
        "If the document mentions something without a reference, provide the appropriate reference yourself. "
        "Do NOT generate any hypothetical situations or discuss topics outside of the provided document. "
        "If there are no references or if the references do not address the question, "
        "politely state any limits and provide your best technical guidance or clarifications based solely on the available data.\n\n"
    )

    # Build conversation context
    convo_str = ""
    for entry in user_history[username][-CONVERSATION_HISTORY_LIMIT:]:
        q = entry['question']
        a = entry['answer']
        convo_str += f"User: {q}\nDev: {a}\n"

    # Final prompt for the model with Enhanced Instructions
    final_prompt = (
        f"{role_prompt}"
        f"Conversation so far:\n{convo_str}\n\n"
        f"Reference content:\n{combined_text if combined_text else '[No references provided.]'}\n\n"
        f"User's current question:\n{question}\n\n"
        f"Instructions:\n"
        f"- Engage in basic greetings and small talk when appropriate (e.g., 'Hi,' 'Hello,' 'How are you?').\n"
        f"- Provide direct, strictly technical guidance based ONLY on the provided references.\n"
        f"- If the document mentions a topic without a reference, supply the appropriate reference yourself.\n"
        f"- Do NOT generate hypothetical situations or introduce information outside of the provided document.\n"
        f"- If references are empty or don't answer the question, politely state the limitations and offer helpful guidance based solely on available data.\n"
        f"- Keep the response strictly technical, clear, and professional.\n"
    )


    # Generate the answer (directly calling google.generativeai)
    try:
        from google.generativeai import GenerativeModel
        model = GenerativeModel("gemini-pro")
        response = model.generate_content(final_prompt)
        bot_answer = response.text.strip() if response and response.text else (
            "I cannot answer from the provided references."
        )
    except Exception as e:
        logging.error(f"Error generating content for Option 1: {e}")
        bot_answer = "An error occurred while generating your answer."

    # Save conversation
    user_history[username].append({"question": question, "answer": bot_answer})
    return jsonify({"answer": bot_answer})
