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

CORS(app, origins=[
    "http://localhost:5000",
    "https://app.qrcodecms.com"
])


# ---------------------------
#   Utils
# ---------------------------

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
        # fallback encodage si UTF-8 échoue
        with open(file_path, newline='', encoding='latin-1') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                text += " ".join(row) + "\n"
    return text

# ---------------------------
#   PDF -> TEXT
# ---------------------------

def load_pdf(file_path):
    text = ""
    with open(file_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"

    return text

# NEW: Charge tous les PDF d’un dossier
def load_all_pdfs_in_directory(directory):
    full_text = ""
    for filename in os.listdir(directory):
        if filename.lower().endswith(".pdf"):
            pdf_path = os.path.join(directory, filename)
            print(f"[RAG] Chargement du PDF : {filename}")
            full_text += load_pdf(pdf_path) + "\n"
    return full_text


# Découpe le texte en chunks pour le RAG (par ex. 300 caractères)
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


# ---------------------------
#   Setup RAG uniquement PDF
# ---------------------------

def setup_rag_system(directory_path):
    try:
        # # 1) Charger PDF
        # full_text = load_pdf(pdf_path)
        
        # 1) Charger tous les PDF
        full_text = load_all_pdfs_in_directory(directory_path)

        # 2) Découper en segments
        chunks = chunk_text(full_text)

        # 3) Embeddings SentenceTransformer
        model = SentenceTransformer('all-MiniLM-L6-v2')
        embeddings = model.encode(chunks)

        # 4) FAISS index
        dimension = embeddings.shape[1]
        index = faiss.IndexFlatL2(dimension)
        index.add(embeddings)
        print("RAG mis à jour après nouvel upload !")
        return chunks, index, model

    except Exception as e:
        raise RuntimeError(f"Error setting up RAG system: {e}")


# ---------------------------
#   Initialisation du RAG
# ---------------------------

# pdf_path = "nucleaire.pdf"   # 👉 remplacer par ton PDF ici
uploads_directory = "uploads"   # 👉 maintenant on charge tout ce dossier

try:
    # texts, faiss_index, model = setup_rag_system(pdf_path)
    # print("RAG PDF initialisé avec succès.")
    texts, faiss_index, model = setup_rag_system(uploads_directory)
    print("RAG initialisé avec TOUS les PDF du dossier uploads/.")
except Exception as e:
    print(f"Erreur RAG: {e}")


# ---------------------------
#   Recherche FAISS
# ---------------------------

def retrieve_relevant_documents(query, texts, faiss_index, model, top_k=5):
    query_embedding = model.encode([query])
    distances, indices = faiss_index.search(query_embedding, top_k)
    return [texts[i] for i in indices[0]]


# ---------------------------
#   Appel à Ollama
# ---------------------------

def query_llama3(prompt):
    load_dotenv()  # charge .env
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
            data = response.json()
            return data['choices'][0]['message']['content']
        else:
            return f"Erreur API Groq: {response.status_code} {response.text}"

    except Exception as e:
        return f"Erreur: {e}"
    

# ---------------------------
#   Appel à Mistral
# ---------------------------

def query_mistral(prompt):
    load_dotenv()
    api_key = os.getenv("MISTRAL_API_KEY")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "mistral-large-latest",
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }

    try:
        response = requests.post(
            "https://api.mistral.ai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=120
        )

        if response.status_code == 200:
            data = response.json()
            return data['choices'][0]['message']['content']
        else:
            return f"Erreur API Mistral: {response.status_code} {response.text}"

    except Exception as e:
        return f"Erreur: {e}"


# ---------------------------
#   API Flask
# ---------------------------

@app.route('/generate', methods=['POST'])
def generate():
    data = request.json
    text = data.get('text', '')

    if not text:
        return jsonify({"error": "No text provided"}), 400

    try:
        # Récupération des chunks pertinents
        relevant_docs = retrieve_relevant_documents(text, texts, faiss_index, model)
        context = " ".join(relevant_docs)

        # Prompt final
        prompt = (
            f"Tu dois répondre en français.\n"
            f"Contexte issu du PDF :\n{context}\n\n"
            f"Question : {text}\n"
            f"Répond de manière détaillée (minimum 5 lignes)."
        )

        # response = query_llama3(prompt)
        response = query_mistral(prompt)
        response = clean_unicode(response)

        return jsonify({"story": response})

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

@app.route('/generate/minisite/<minisite_id>', methods=['POST'])
def generate_minisite(minisite_id):
    data = request.json
    text = data.get('text', '')

    if not text:
        return jsonify({"error": "No text provided"}), 400
    
    BASE_STORAGE_PATH = os.getenv("STORAGE_PATH")
    directory_path = os.path.join(BASE_STORAGE_PATH, str(minisite_id))

    if not os.path.exists(directory_path):
        return jsonify({"error": f"Directory not found: {directory_path}"}), 404

    global texts, faiss_index, model
    texts, faiss_index, model = setup_rag_system(directory_path)

    try:
        # Récupération des chunks pertinents
        relevant_docs = retrieve_relevant_documents(text, texts, faiss_index, model)
        context = " ".join(relevant_docs)

        # Prompt final
        prompt = (
            f"Tu dois répondre en français.\n"
            f"Contexte issu du PDF :\n{context}\n\n"
            f"Question : {text}\n"
            f"Répond de manière détaillée (minimum 5 lignes)."
        )

        response = query_mistral(prompt)
        response = clean_unicode(response)

        return jsonify({"story": response})

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

@app.route('/test', methods=['GET'])
def test():
    return "test"

@app.route('/upload', methods=['POST'])
def upload_pdf():
    if 'pdf' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files['pdf']
    
    # Sauvegarder dans votre répertoire
    file.save(os.path.join('uploads', file.filename))
    
    # 🔥 Mise à jour automatique du RAG (nouveau PDF pris en compte)
    global texts, faiss_index, model
    texts, faiss_index, model = setup_rag_system("uploads")
    print("RAG mis à jour après nouvel upload !")
    
    return jsonify({"message": "File uploaded successfully"}), 200


@app.route('/upload/minisite/<minisite_id>', methods=['POST'])
def upload_pdf_minisite(minisite_id):
    if 'pdf' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files['pdf']

    BASE_STORAGE_PATH = os.getenv("STORAGE_PATH")
    directory_path = os.path.join(BASE_STORAGE_PATH, str(minisite_id))

    os.makedirs(directory_path, exist_ok=True)

    # Sauvegarde le PDF dans le dossier du minisite
    file_path = os.path.join(directory_path, file.filename)
    file.save(file_path)
    print(f"Fichier sauvegardé : {file_path}")

    # Mise à jour automatique du RAG pour ce minisite
    global texts, faiss_index, model
    texts, faiss_index, model = setup_rag_system(directory_path)
    print(f"RAG mis à jour pour le minisite {minisite_id} !")

    return jsonify({"message": f"File uploaded successfully to minisite {minisite_id}"}), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
