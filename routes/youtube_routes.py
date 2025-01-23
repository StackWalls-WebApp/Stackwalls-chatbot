from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
import os
import logging
import threading

from services.youtube_service import (

    answer_question,
    answer_general_question,
    merge_answers,
    get_file_content,
    get_wikipedia_content,
    end_conversation,
    user_history
)
from services.pdf_service import process_file
from utils.error_handling import handle_errors

youtube_bp = Blueprint('youtube_bp', __name__)

ALLOWED_EXTENSIONS = {
    'pdf', 'doc', 'docx', 'txt', 'csv',
    'xls', 'xlsx', 'html', 'mp3', 'mp4',
    'wav', 'avi', 'mkv', 'flv', 'mov'
}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@youtube_bp.route('/api/interactive_chat', methods=['POST'])
@handle_errors
def interactive_chat():
    """
    Unified endpoint for the 4 chatbot options:
      option 1 = Discuss about project
      option 2 = Know more about StackWalls
      option 3 = Your AI-powered co-founder
      option 4 = How to choose best freelancer
    """
    data = request.form
    username = data.get('username', 'anonymous_user')
    option = data.get('option')  # 1, 2, 3, or 4
    question = data.get('question', '').strip()

    # Create user conversation history if not present
    if username not in user_history:
        user_history[username] = []

    # === Option 2 (StackWalls) special handling ===
    if option == '2':
        # We only want to read from stackwalls.txt and answer the question directly
        # ignoring everything else, no uploads used.
        if not question:
            return jsonify({"error": "No question provided for StackWalls info."}), 400

        # Read the entire stackwalls.txt
        try:
            with open('stackwalls.txt', 'r', encoding='utf-8') as f:
                stackwalls_text = f.read()
        except Exception as e:
            logging.error(f"Could not read stackwalls.txt: {e}")
            return jsonify({"error": "Internal error reading stackwalls.txt"}), 500

        # Directly answer the question from the stackwalls text
        ans = answer_question(
            content_text=stackwalls_text,
            metadata={"title": "StackWalls", "author_name": "System"},
            user_question=question,
            conversation_history=user_history[username]
        )

        # Append to conversation
        user_history[username].append({"question": question, "answer": ans})
        return jsonify({"answer": ans})

    # For Options 1, 3, 4, we allow user to upload some resources:
    youtube_links = [data.get(f'youtube_link{i}') for i in range(1, 3) if data.get(f'youtube_link{i}')]
    wikipedia_titles = [data.get(f'wikipedia_title{i}') for i in range(1, 2) if data.get(f'wikipedia_title{i}')]
    uploaded_files = [request.files.get(f'uploaded_file{i}') for i in range(1, 3) if request.files.get(f'uploaded_file{i}')]

    if not question:
        return jsonify({"error": "A question or message is required."}), 400

    # Collect text from provided resources
    resource_texts = []



    # 3) Uploaded Files
    for uf in uploaded_files:
        try:
            if allowed_file(uf.filename):
                ext = uf.filename.rsplit('.', 1)[1].lower()
                fname = secure_filename(uf.filename)
                fpath = os.path.join('uploads', fname)
                uf.save(fpath)
                txt = get_file_content(fname, ext, fpath)
                resource_texts.append(txt)
            else:
                logging.error(f"Unsupported file type: {uf.filename}")
        except Exception as e:
            logging.error(f"Error processing file {uf.filename}: {e}")

    # Merge all resources into one big text chunk for now:
    # (Alternatively, you can handle them individually.)
    if not resource_texts:
        # If no resources were provided or they failed, fallback or return error
        # But the user wants "No own knowledge", so we must handle carefully
        if option == '4':
            # For option 4, if there's no resources, we have nothing to answer from.
            # Return an error or empty response
            return jsonify({"answer": "No resources provided. Please upload or link relevant data."})
        # Otherwise, fallback to normal chat (but user wants no outside knowledge).
        return jsonify({
            "answer": "No valid resources found to answer from."
        })

    merged_content = "\n\n".join(resource_texts)

    # Option-based role-play or style:
    if option == '1':
        # "Discuss about project" -> fully technical, strict guidance
        role_intro = (
            "You are Dev, an extremely strict and technical project advisor. "
            "You must only use the content the user provided in these PDFs, YouTube videos, or Wikipedia article. "
            "Provide direct, no-nonsense guidance about the project without hypothetical or personal knowledge.\n\n"
        )
    elif option == '3':
        # "Your AI-powered co-founder" -> speak as a co-founder, but only from user’s files
        role_intro = (
            "You are the user's AI-powered co-founder. "
            "Address the user from the perspective of a co-founder with the provided resources. "
            "Do NOT use outside knowledge or personal imagination. Stay within the uploaded data.\n\n"
        )
    elif option == '4':
        # "How to choose best freelancer" -> Q&A style, only from provided resources
        role_intro = (
            "You are Dev, offering Q&A style tips on choosing the best freelancer. "
            "Only respond using the data from the provided PDFs, YouTube, or Wikipedia. "
            "No external or hypothetical knowledge.\n\n"
        )
    else:
        # Default fallback
        role_intro = "You are Dev, a neutral assistant.\n\n"

    # Build conversation history
    conversation_snippets = ""
    for entry in user_history[username]:
        conversation_snippets += f"User: {entry['question']}\nDev: {entry['answer']}\n"

    # Construct prompt
    full_prompt = (
        f"{role_intro}"
        f"Conversation so far:\n"
        f"{conversation_snippets}\n"
        f"Reference content:\n"
        f"{merged_content}\n\n"
        f"User now asks:\n"
        f"{question}\n\n"
        f"Answer strictly from the reference content above.\n"
    )

    # Now we call your generative function, similar to answer_question
    from google.generativeai import GenerativeModel
    model = GenerativeModel("gemini-pro")

    try:
        response = model.generate_content(full_prompt)
        final_answer = response.text.strip() if response.text else "I'm not sure how to answer from the given resources."
    except Exception as e:
        logging.error(f"Error generating answer: {e}")
        final_answer = "I'm sorry, I couldn't generate a response right now."

    # Save to user history
    user_history[username].append({"question": question, "answer": final_answer})

    return jsonify({"answer": final_answer})

@youtube_bp.route('/api/end_conversation', methods=['POST'])
@handle_errors
def end_conversation_route():
    end_conversation()
    return jsonify({"message": "Conversation ended and in-memory caches cleared."})
