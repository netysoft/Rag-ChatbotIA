# 🤖 RAG Multi-Client avec Flask & FAISS

Un système RAG (Retrieval-Augmented Generation) multi-tenant permettant de créer des assistants IA personnalisés par client, basés sur leurs propres documents PDF.

## 📋 Table des matières

- [Fonctionnalités](#fonctionnalités)
- [Architecture](#architecture)
- [Prérequis](#prérequis)
- [Installation](#installation)
- [Configuration](#configuration)
- [Utilisation](#utilisation)
- [API Endpoints](#api-endpoints)
- [Intégration Frontend](#intégration-frontend)
- [Structure des dossiers](#structure-des-dossiers)

## ✨ Fonctionnalités

- **Multi-tenant** : Gestion de plusieurs clients avec leurs propres documents
- **Upload de PDF** : Interface simple pour uploader des documents
- **RAG intelligent** : Recherche sémantique dans les documents via FAISS
- **Cache optimisé** : Les embeddings sont mis en cache pour des performances optimales
- **API REST** : Endpoints simples et clairs pour l'intégration frontend
- **Support LLM** : Intégration avec Groq (Llama 3.3 70B)

## 🏗️ Architecture

```
┌─────────────┐
│   Frontend  │
│   (React)   │
└──────┬──────┘
       │
       │ HTTP REST API
       │
┌──────▼──────────────────────────────┐
│         Flask Backend               │
│  ┌──────────────────────────────┐  │
│  │  Upload PDF (par client_id)  │  │
│  └──────────┬───────────────────┘  │
│             │                       │
│  ┌──────────▼───────────────────┐  │
│  │  Extraction texte (PyPDF2)   │  │
│  └──────────┬───────────────────┘  │
│             │                       │
│  ┌──────────▼───────────────────┐  │
│  │  Chunking (500 chars)        │  │
│  └──────────┬───────────────────┘  │
│             │                       │
│  ┌──────────▼───────────────────┐  │
│  │  Embeddings (SentenceT.)     │  │
│  └──────────┬───────────────────┘  │
│             │                       │
│  ┌──────────▼───────────────────┐  │
│  │  Index FAISS (par client)    │  │
│  └──────────┬───────────────────┘  │
│             │                       │
│  ┌──────────▼───────────────────┐  │
│  │  Retrieval + LLM (Groq)      │  │
│  └──────────────────────────────┘  │
└─────────────────────────────────────┘
```

## 🔧 Prérequis

- Python 3.8+
- pip
- Compte Groq API (gratuit sur [groq.com](https://groq.com))

## 📦 Installation

### 1. Cloner le repository

```bash
git clone <votre-repo>
cd <votre-repo>
```

### 2. Créer un environnement virtuel (recommandé)

```bash
python -m venv venv

# Sur Windows
venv\Scripts\activate

# Sur Linux/Mac
source venv/bin/activate
```

### 3. Installer les dépendances

```bash
pip install -r requirements.txt
```

**Contenu du `requirements.txt` :**
```txt
flask==3.0.0
flask-cors==4.0.0
sentence-transformers==2.2.2
PyPDF2==3.0.1
faiss-cpu==1.7.4
python-dotenv==1.0.0
requests==2.31.0
```

### 4. Créer le fichier `.env`

Créez un fichier `.env` à la racine du projet :

```env
GROQ_API_KEY=votre_clé_api_groq
```

Pour obtenir votre clé API Groq :
1. Créez un compte sur [console.groq.com](https://console.groq.com)
2. Allez dans "API Keys"
3. Créez une nouvelle clé
4. Copiez-la dans votre `.env`

### 5. Créer le dossier uploads

```bash
mkdir uploads
```

## 🚀 Configuration

Le système utilise une structure de dossiers par client :

```
uploads/
├── 1/           # Client ID 1
│   ├── doc1.pdf
│   └── doc2.pdf
├── 2/           # Client ID 2
│   └── guide.pdf
└── 3/           # Client ID 3
    └── manual.pdf
```

Chaque `client_id` a son propre dossier contenant ses documents PDF.

## 💻 Utilisation

### Démarrer le serveur

```bash
python apiRAGPDFMultiUsers.py
```

Le serveur démarre sur `http://localhost:5000`

Vous devriez voir :
```
 * Running on http://127.0.0.1:5000
 * Running on http://192.168.1.X:5000
```

### Test rapide

```bash
curl http://localhost:5000/test
```

Réponse attendue : `API OK`

## 🔌 API Endpoints

### 1. Upload de PDF

**Endpoint :** `POST /upload?client_id={client_id}`

**Description :** Upload un fichier PDF pour un client spécifique

**Paramètres :**
- `client_id` (query param) : Identifiant du client
- `pdf` (form-data) : Fichier PDF

**Exemple avec cURL :**
```bash
curl -X POST \
  "http://localhost:5000/upload?client_id=1" \
  -F "pdf=@/chemin/vers/document.pdf"
```

**Réponse :**
```json
{
  "message": "File uploaded and cache cleared."
}
```

---

### 2. Générer une réponse (RAG)

**Endpoint :** `POST /generate`

**Description :** Pose une question au RAG basé sur les documents du client

**Body (JSON) :**
```json
{
  "text": "Quels sont les principaux sujets abordés ?",
  "client_id": "1"
}
```

**Réponse :**
```json
{
  "answer": "D'après les documents fournis, les principaux sujets abordés sont..."
}
```

**Exemple avec cURL :**
```bash
curl -X POST \
  http://localhost:5000/generate \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Résume les documents",
    "client_id": "1"
  }'
```

---

### 3. Test de santé

**Endpoint :** `GET /test`

**Description :** Vérifie que l'API fonctionne

**Réponse :** `API OK`

## 🎨 Intégration Frontend

### Exemple React/TypeScript

#### Upload de fichiers

```typescript
const uploadPDF = async (file: File, clientId: string) => {
  const formData = new FormData();
  formData.append('pdf', file);

  try {
    const response = await fetch(
      `http://localhost:5000/upload?client_id=${clientId}`,
      {
        method: 'POST',
        body: formData,
      }
    );

    if (!response.ok) {
      throw new Error('Erreur lors de l\'upload');
    }

    const data = await response.json();
    console.log(data.message);
  } catch (error) {
    console.error('Erreur:', error);
  }
};
```

#### Poser une question au RAG

```typescript
const askQuestion = async (question: string, clientId: string) => {
  try {
    const response = await fetch('http://localhost:5000/generate', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        text: question,
        client_id: clientId,
      }),
    });

    if (!response.ok) {
      throw new Error('Erreur lors de la requête');
    }

    const data = await response.json();
    return data.answer;
  } catch (error) {
    console.error('Erreur:', error);
    return null;
  }
};
```

### Exemple JavaScript Vanilla

```javascript
// Upload
async function uploadPDF(file, clientId) {
  const formData = new FormData();
  formData.append('pdf', file);

  const response = await fetch(
    `http://localhost:5000/upload?client_id=${clientId}`,
    {
      method: 'POST',
      body: formData,
    }
  );

  return await response.json();
}

// Question
async function askRAG(question, clientId) {
  const response = await fetch('http://localhost:5000/generate', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      text: question,
      client_id: clientId,
    }),
  });

  const data = await response.json();
  return data.answer;
}
```

## 📁 Structure des dossiers

```
.
├── apiRAGPDFMultiUsers.py    # Script principal
├── requirements.txt          # Dépendances Python
├── .env                      # Variables d'environnement (à créer)
├── .gitignore               # Fichiers à ignorer
├── README.md                # Ce fichier
└── uploads/                 # Dossier des documents (créé auto)
    ├── 1/                   # Client 1
    ├── 2/                   # Client 2
    └── 3/                   # Client 3
```

## 🔍 Comment ça marche ?

### 1. Upload d'un document

1. Le frontend envoie un PDF avec un `client_id`
2. Le backend sauvegarde le PDF dans `uploads/{client_id}/`
3. Le cache pour ce client est invalidé

### 2. Première question

1. Le RAG charge tous les PDFs du client
2. Extraction du texte avec PyPDF2
3. Découpage en chunks de ~500 caractères
4. Création d'embeddings avec SentenceTransformer
5. Indexation dans FAISS
6. Mise en cache (pour les questions suivantes)

### 3. Questions suivantes

1. Le cache est réutilisé (pas de rechargement)
2. La question est transformée en embedding
3. FAISS trouve les 5 chunks les plus pertinents
4. Ces chunks forment le contexte envoyé à Groq
5. Llama 3.3 génère la réponse

### 4. Cache et performance

- Le RAG est chargé **une seule fois** par client
- Les questions suivantes sont **instantanées**
- Le cache est invalidé uniquement lors d'un nouvel upload

## ⚙️ Configuration avancée

### Modifier la taille des chunks

Dans `chunk_text()` :
```python
def chunk_text(text, chunk_size=500):  # Modifier ici
    # ...
```

### Modifier le nombre de chunks récupérés

Dans `retrieve_relevant_documents()` :
```python
def retrieve_relevant_documents(query, texts, faiss_index, model, top_k=5):  # Modifier ici
    # ...
```

### Changer le modèle LLM

Dans `query_llama3()` :
```python
payload = {
    "model": "llama-3.3-70b-versatile",  # Modifier ici
    # Autres modèles : llama-3.1-8b-instant, mixtral-8x7b-32768, etc.
}
```

## 🐛 Debugging

### Voir les logs détaillés

Le script affiche automatiquement :
- Les PDFs chargés
- Le nombre de chunks créés
- Les requêtes reçues

### Problèmes courants

**Erreur 400 "Missing client_id"**
- Vérifiez que le `client_id` est bien passé dans l'URL : `?client_id=1`

**Erreur "Le dossier client n'existe pas"**
- Uploadez d'abord un PDF avant de poser une question
- Vérifiez que le dossier `uploads/{client_id}` existe

**Erreur API Groq**
- Vérifiez votre clé API dans le `.env`
- Vérifiez votre quota Groq (limite gratuite)

**CORS Error**
- Le CORS est activé pour tous les domaines
- Si problème, vérifiez votre frontend

## 📊 Performances

- **Chargement initial** : ~2-5 secondes (selon taille des PDFs)
- **Questions suivantes** : ~1-2 secondes (via Groq API)
- **Upload** : instantané

## 🔐 Sécurité

⚠️ **Important pour la production :**

- Ajoutez une authentification (JWT, OAuth, etc.)
- Validez les `client_id` (actuellement tous acceptés)
- Limitez la taille des uploads
- Scannez les PDFs contre les malwares
- Utilisez HTTPS en production
- Restreignez les CORS aux domaines autorisés

## 📝 Licence

MIT

## 🤝 Contribution

Les contributions sont les bienvenues ! N'hésitez pas à ouvrir une issue ou une pull request.

## 📧 Support

Pour toute question, ouvrez une issue sur GitHub.

---

**Créé avec ❤️ en utilisant Flask, FAISS, SentenceTransformers et Groq**