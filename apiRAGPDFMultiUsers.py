from flask import Flask, request, jsonify
from flask_cors import CORS
from sentence_transformers import SentenceTransformer
import unicodedata
import PyPDF2
import faiss
import os
import requests
import csv
from dotenv import load_dotenv

app = Flask(__name__)

CORS(app, resources={r"/*": {"origins": "*"}})

# ---------------------------------------------------------------------
#   Utils
# ---------------------------------------------------------------------

def clean_unicode(text):
    return unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8', 'ignore')

def load_csv(file_path):
    text = ""
    try:
        with open(file_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                text += " ".join(row) + "\n"
    except:
        with open(file_path, newline='', encoding='latin-1') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                text += " ".join(row) + "\n"
    return text

# ---------------------------------------------------------------------
#   PDF → TEXT
# ---------------------------------------------------------------------

def load_pdf(file_path):
    text = ""
    with open(file_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text


def load_all_pdfs_in_directory(directory):
    full_text = ""
    if not os.path.exists(directory):
        print(f"[RAG] Aucun dossier trouvé : {directory}")
        return ""

    for filename in os.listdir(directory):
        if filename.lower().endswith(".pdf"):
            pdf_path = os.path.join(directory, filename)
            print(f"[RAG] Chargement PDF : {filename}")
            full_text += load_pdf(pdf_path) + "\n"
    return full_text


def chunk_text(text, chunk_size=500):
    chunks = []
    words = text.split()
    current = []
    current_len = 0

    for w in words:
        current.append(w)
        current_len += len(w) + 1
        if current_len >= chunk_size:
            chunks.append(" ".join(current))
            current = []
            current_len = 0

    if current:
        chunks.append(" ".join(current))

    return chunks

# ---------------------------------------------------------------------
#   RAG PAR CLIENT (Multi-tenants)
# ---------------------------------------------------------------------

rag_cache = {}  
# Exemple:
# rag_cache[client_id] = { "texts": [...], "index": faiss_index, "model": model }

def load_rag_for_client(client_id):
    """
    Construit ou recharge le RAG pour un miniSite/client.
    """
    client_folder = os.path.join("uploads", str(client_id))

    if not os.path.exists(client_folder):
        raise RuntimeError(f"Le dossier client '{client_id}' n'existe pas.")

    # Si déjà chargé → on réutilise
    if client_id in rag_cache:
        return rag_cache[client_id]["texts"], rag_cache[client_id]["index"], rag_cache[client_id]["model"]

    print(f"[RAG] Initialisation du RAG pour le client {client_id}…")

    full_text = load_all_pdfs_in_directory(client_folder)
    chunks = chunk_text(full_text)

    model = SentenceTransformer('all-MiniLM-L6-v2')
    embeddings = model.encode(chunks)

    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings)

    rag_cache[client_id] = {
        "texts": chunks,
        "index": index,
        "model": model
    }

    print(f"[RAG] Client {client_id} chargé avec {len(chunks)} chunks.")
    return chunks, index, model

# ---------------------------------------------------------------------
#   FAISS Retrieval
# ---------------------------------------------------------------------

def retrieve_relevant_documents(query, texts, faiss_index, model, top_k=5):
    query_embedding = model.encode([query])
    distances, indices = faiss_index.search(query_embedding, top_k)
    return [texts[i] for i in indices[0]]

# ---------------------------------------------------------------------
#   LLM (Groq)
# ---------------------------------------------------------------------

def query_llama3(prompt):
    load_dotenv()
    api_key = os.getenv("GROQ_API_KEY")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=120
        )

        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            return f"Erreur API Groq: {response.status_code} {response.text}"
    except Exception as e:
        return f"Erreur: {e}"

# ---------------------------------------------------------------------
#   API
# ---------------------------------------------------------------------

@app.route('/generate', methods=['POST'])
def generate():
    data = request.json
    text = data.get('text', '')
    client_id = data.get('client_id')

    if not text:
        return jsonify({"error": "Missing 'text'"}), 400
    if not client_id:
        return jsonify({"error": "Missing 'client_id'"}), 400

    try:
        texts, faiss_index, model = load_rag_for_client(client_id)

        relevant_docs = retrieve_relevant_documents(text, texts, faiss_index, model)
        context = " ".join(relevant_docs)

        prompt = (
            f"Tu dois répondre en français.\n"
            f"Contexte du miniSite {client_id} :\n{context}\n\n"
            f"Question : {text}\n"
            f"Répond clairement et en minimum 5 lignes."
        )

        response = query_llama3(prompt)
        return jsonify({"answer": clean_unicode(response)})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/upload', methods=['POST'])
def upload_pdf():
    print("=== Nouvelle requête UPLOAD ===")
    print("Form:", request.form)
    print("Files:", request.files)
    
    client_id = request.args.get("client_id")
    

    print(f"client_id final: '{client_id}'")


    
    if not client_id:
        return jsonify({"error": "Missing 'client_id'"}), 400

    if 'pdf' not in request.files:
        return jsonify({"error": "Missing file"}), 400

    file = request.files['pdf']

    client_folder = os.path.join("uploads", client_id)
    os.makedirs(client_folder, exist_ok=True)

    file.save(os.path.join(client_folder, file.filename))

    # Invalide le cache pour ce client
    if client_id in rag_cache:
        del rag_cache[client_id]

    return jsonify({"message": "File uploaded and cache cleared."})


@app.route('/test')
def test():
    return "API OK"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
