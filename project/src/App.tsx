import { useState } from 'react';
import ChatInterface from './components/ChatInterface';
import PdfUploader from './components/PdfUploader';
import { MessageSquare, Upload } from 'lucide-react';

function App() {
  const [activeTab, setActiveTab] = useState<'chat' | 'upload'>('chat');

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      <div className="container mx-auto px-4 py-8 max-w-6xl">
        <header className="mb-8">
          <h1 className="text-4xl font-bold text-slate-800 mb-2">
            RAG Chatbot
          </h1>
          <p className="text-slate-600">
            Interrogez vos documents PDF avec l'intelligence artificielle
          </p>
        </header>

        <div className="bg-white rounded-xl shadow-lg overflow-hidden">
          <div className="flex border-b border-slate-200">
            <button
              onClick={() => setActiveTab('chat')}
              className={`flex items-center gap-2 px-6 py-4 font-medium transition-colors ${
                activeTab === 'chat'
                  ? 'bg-blue-50 text-blue-600 border-b-2 border-blue-600'
                  : 'text-slate-600 hover:bg-slate-50'
              }`}
            >
              <MessageSquare size={20} />
              Chat
            </button>
            <button
              onClick={() => setActiveTab('upload')}
              className={`flex items-center gap-2 px-6 py-4 font-medium transition-colors ${
                activeTab === 'upload'
                  ? 'bg-blue-50 text-blue-600 border-b-2 border-blue-600'
                  : 'text-slate-600 hover:bg-slate-50'
              }`}
            >
              <Upload size={20} />
              Upload PDF
            </button>
          </div>

          <div className="p-6">
            {activeTab === 'chat' ? <ChatInterface /> : <PdfUploader />}
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
