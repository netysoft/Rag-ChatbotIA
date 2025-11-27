import { useState, useRef } from 'react';
import { Upload, File, CheckCircle, XCircle, Loader2 } from 'lucide-react';

interface UploadedFile {
  name: string;
  size: number;
  status: 'pending' | 'uploading' | 'success' | 'error';
  error?: string;
}

function PdfUploader() {
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  const handleFiles = (fileList: FileList | null) => {
    if (!fileList) return;

    const newFiles: UploadedFile[] = Array.from(fileList)
      .filter(file => file.type === 'application/pdf')
      .map(file => ({
        name: file.name,
        size: file.size,
        status: 'pending' as const,
      }));

    setFiles(prev => [...prev, ...newFiles]);

    newFiles.forEach((_, index) => {
      setTimeout(() => {
        uploadFile(fileList[index], files.length + index);
      }, index * 100);
    });
  };

  const uploadFile = async (file: File, index: number) => {
    setFiles(prev => {
      const updated = [...prev];
      updated[index] = { ...updated[index], status: 'uploading' };
      return updated;
    });

    const formData = new FormData();
    formData.append('pdf', file);
    

    try {
      const response = await fetch('http://localhost:5000/upload?client_id=2', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error('Erreur lors de l\'upload');
      }

      setFiles(prev => {
        const updated = [...prev];
        updated[index] = { ...updated[index], status: 'success' };
        return updated;
      });
    } catch (error) {
      setFiles(prev => {
        const updated = [...prev];
        updated[index] = {
          ...updated[index],
          status: 'error',
          error: error instanceof Error ? error.message : 'Erreur inconnue',
        };
        return updated;
      });
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    handleFiles(e.dataTransfer.files);
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    handleFiles(e.target.files);
  };

  const getStatusIcon = (status: UploadedFile['status']) => {
    switch (status) {
      case 'pending':
        return <File className="text-slate-400" size={20} />;
      case 'uploading':
        return <Loader2 className="text-blue-600 animate-spin" size={20} />;
      case 'success':
        return <CheckCircle className="text-green-600" size={20} />;
      case 'error':
        return <XCircle className="text-red-600" size={20} />;
    }
  };

  return (
    <div className="space-y-6">
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`border-2 border-dashed rounded-lg p-12 text-center cursor-pointer transition-colors ${
          isDragging
            ? 'border-blue-500 bg-blue-50'
            : 'border-slate-300 hover:border-blue-400 hover:bg-slate-50'
        }`}
      >
        <Upload
          className={`mx-auto mb-4 ${isDragging ? 'text-blue-600' : 'text-slate-400'}`}
          size={48}
        />
        <p className="text-lg font-medium text-slate-700 mb-2">
          Déposez vos fichiers PDF ici
        </p>
        <p className="text-sm text-slate-500 mb-4">
          ou cliquez pour sélectionner des fichiers
        </p>
        <p className="text-xs text-slate-400">
          Seuls les fichiers PDF sont acceptés
        </p>
        <input
          ref={fileInputRef}
          type="file"
          accept="application/pdf"
          multiple
          onChange={handleFileSelect}
          className="hidden"
        />
      </div>

      {files.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-lg font-semibold text-slate-800">
            Fichiers ({files.length})
          </h3>
          <div className="space-y-2">
            {files.map((file, index) => (
              <div
                key={index}
                className="flex items-center gap-3 p-4 bg-slate-50 rounded-lg border border-slate-200"
              >
                {getStatusIcon(file.status)}
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-slate-800 truncate">
                    {file.name}
                  </p>
                  <p className="text-sm text-slate-500">
                    {formatFileSize(file.size)}
                  </p>
                  {file.error && (
                    <p className="text-sm text-red-600 mt-1">{file.error}</p>
                  )}
                </div>
                {file.status === 'uploading' && (
                  <span className="text-sm text-blue-600 font-medium">
                    Upload...
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      
    </div>
  );
}

export default PdfUploader;
