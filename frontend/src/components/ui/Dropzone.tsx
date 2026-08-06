import { useRef, useState } from 'react';
import { FileUp } from 'lucide-react';

interface DropzoneProps {
  /** Extensions acceptées, ex ".csv" ou ".csv,.json" */
  accept: string;
  file: File | null;
  onFileSelect: (file: File) => void;
  hint?: string;
}

/** Zone de dépôt de fichier réutilisable : clic ou glisser-déposer, filtre par extension. */
export function Dropzone({ accept, file, onFileSelect, hint }: DropzoneProps) {
  const [isDragging, setIsDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const extensions = accept.split(',').map((e) => e.trim().toLowerCase());
  const matches = (f: File) => extensions.some((ext) => f.name.toLowerCase().endsWith(ext));

  const handleFiles = (files: FileList | null) => {
    const f = files?.[0];
    if (f && matches(f)) onFileSelect(f);
  };

  return (
    <div
      role="button"
      tabIndex={0}
      aria-label="Déposer un fichier"
      onClick={() => inputRef.current?.click()}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') inputRef.current?.click(); }}
      onDrop={(e) => { e.preventDefault(); setIsDragging(false); handleFiles(e.dataTransfer.files); }}
      onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
      onDragLeave={() => setIsDragging(false)}
      className={`flex cursor-pointer flex-col items-center justify-center gap-2 rounded-card border-2 border-dashed p-8 text-center transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 ${
        isDragging ? 'border-indigo-400 bg-indigo-50' : 'border-slate-300 bg-white hover:border-slate-400'
      }`}
    >
      <FileUp size={24} className="text-slate-400" aria-hidden="true" />
      {file ? (
        <>
          <p className="text-sm font-medium text-slate-900">{file.name}</p>
          <p className="text-xs text-slate-500">{(file.size / 1024).toFixed(1)} Ko — cliquer ou déposer pour remplacer</p>
        </>
      ) : (
        <>
          <p className="text-sm font-medium text-slate-700">Cliquer ou glisser-déposer un fichier</p>
          {hint && <p className="text-xs text-slate-500">{hint}</p>}
        </>
      )}
      <input
        ref={inputRef}
        data-testid="dropzone-input"
        type="file"
        accept={accept}
        className="hidden"
        onChange={(e) => { handleFiles(e.target.files); e.target.value = ''; }}
      />
    </div>
  );
}
