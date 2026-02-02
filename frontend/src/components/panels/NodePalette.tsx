import { Database, GitBranch, Flag } from 'lucide-react';
import type { NodeType } from '@/types';

interface NodePaletteProps {
  onDragStart: (event: React.DragEvent, nodeType: NodeType) => void;
}

const nodeItems: { type: NodeType; label: string; icon: React.ElementType; description: string }[] = [
  {
    type: 'input',
    label: 'Input',
    icon: Database,
    description: 'Lit un champ de la vulnérabilité',
  },
  {
    type: 'lookup',
    label: 'Lookup',
    icon: GitBranch,
    description: 'Recherche dans une table externe',
  },
  {
    type: 'output',
    label: 'Output',
    icon: Flag,
    description: 'Décision finale (Act, Attend...)',
  },
];

export function NodePalette({ onDragStart }: NodePaletteProps) {
  return (
    <div className="bg-white rounded-lg shadow-lg p-4 w-64">
      <h3 className="font-bold text-gray-700 mb-3 text-sm uppercase tracking-wide">
        Nœuds
      </h3>
      <p className="text-xs text-gray-500 mb-4">
        Glissez-déposez un nœud sur le canvas
      </p>

      <div className="space-y-2">
        {nodeItems.map((item) => {
          const Icon = item.icon;
          return (
            <div
              key={item.type}
              className={`
                p-3 rounded-lg border-2 border-dashed cursor-grab
                hover:border-solid hover:shadow-md transition-all
                ${item.type === 'input' ? 'border-blue-300 hover:border-blue-500 hover:bg-blue-50' : ''}
                ${item.type === 'lookup' ? 'border-purple-300 hover:border-purple-500 hover:bg-purple-50' : ''}
                ${item.type === 'output' ? 'border-green-300 hover:border-green-500 hover:bg-green-50' : ''}
              `}
              draggable
              onDragStart={(e) => onDragStart(e, item.type)}
            >
              <div className="flex items-center gap-2">
                <Icon
                  size={20}
                  className={`
                    ${item.type === 'input' ? 'text-blue-500' : ''}
                    ${item.type === 'lookup' ? 'text-purple-500' : ''}
                    ${item.type === 'output' ? 'text-green-500' : ''}
                  `}
                />
                <div>
                  <div className="font-medium text-sm text-gray-700">
                    {item.label}
                  </div>
                  <div className="text-xs text-gray-500">{item.description}</div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
