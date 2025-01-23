import PyPDF2
import docx
import csv
import pandas as pd
from bs4 import BeautifulSoup
import logging
import google.generativeai as genai
from config import SUMMARY_WORD_LIMIT

def process_pdf_file(pdf_file_path):
    try:
        with open(pdf_file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            text = ''
            for page in reader.pages:
                text += page.extract_text()
            return text
    except Exception as e:
        logging.error(f"Error processing PDF file {pdf_file_path}: {e}")
        raise RuntimeError(f"Failed to process PDF file: {e}")

def process_doc_file(doc_file_path):
    try:
        doc = docx.Document(doc_file_path)
        text = "\n".join(para.text for para in doc.paragraphs)
        return text
    except Exception as e:
        logging.error(f"Error processing DOC/DOCX file {doc_file_path}: {e}")
        raise RuntimeError(f"Failed to process DOC/DOCX file: {e}")

def process_txt_file(txt_file_path):
    try:
        with open(txt_file_path, 'r', encoding='utf-8') as file:
            text = file.read()
        return text
    except Exception as e:
        logging.error(f"Error processing TXT file {txt_file_path}: {e}")
        raise RuntimeError(f"Failed to process TXT file: {e}")

def process_csv_file(csv_file_path):
    try:
        with open(csv_file_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            text = "\n".join([", ".join(row) for row in reader])
        return text
    except Exception as e:
        logging.error(f"Error processing CSV file {csv_file_path}: {e}")
        raise RuntimeError(f"Failed to process CSV file: {e}")

def process_xls_xlsx_file(xls_xlsx_file_path):
    try:
        df = pd.read_excel(xls_xlsx_file_path)
        return df.to_string()
    except Exception as e:
        logging.error(f"Error processing XLS/XLSX file {xls_xlsx_file_path}: {e}")
        raise RuntimeError(f"Failed to process XLS/XLSX file: {e}")

def process_html_file(html_file_path):
    try:
        with open(html_file_path, 'r', encoding='utf-8') as file:
            soup = BeautifulSoup(file, 'html.parser')
            return soup.get_text()
    except Exception as e:
        logging.error(f"Error processing HTML file {html_file_path}: {e}")
        raise RuntimeError(f"Failed to process HTML file: {e}")

def summarize_content(content):
    """
    Basic summarization for PDF or other file content, if needed.
    """
    try:
        model = genai.GenerativeModel("gemini-pro")
        prompt = (
            f"Summarize the following content in approximately {SUMMARY_WORD_LIMIT} words:\n\n"
            f"{content[:10000]}"
        )
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        logging.error(f"Error summarizing content: {e}")
        raise RuntimeError("Failed to generate content summary.")

def process_file(file_path, file_extension):
    file_extension = file_extension.lower()
    if file_extension == 'pdf':
        return process_pdf_file(file_path)
    elif file_extension in ['doc', 'docx']:
        return process_doc_file(file_path)
    elif file_extension == 'txt':
        return process_txt_file(file_path)
    elif file_extension == 'csv':
        return process_csv_file(file_path)
    elif file_extension in ['xls', 'xlsx']:
        return process_xls_xlsx_file(file_path)
    elif file_extension == 'html':
        return process_html_file(file_path)
    elif file_extension in ['mp3', 'mp4', 'wav', 'avi', 'mkv', 'flv', 'mov']:
        raise ValueError("Audio/Video handling is done in youtube_service.py or similar.")
    else:
        raise ValueError(f"Unsupported file type: {file_extension}")
