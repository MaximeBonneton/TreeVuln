import { Database, GitBranch, Flag, Calculator } from 'lucide-react';
import type { NodeType } from '@/types';

interface NodePaletteProps {
  onDragStart: (event: React.DragEvent, nodeType: NodeType) => void;
}

const nodeItems: { type: NodeType; label: string; icon: React.ElementType; description: string }[] = [
  {
    type: 'input',
    label: 'Input',
    icon: Database,
    description: 'Reads a vulnerability field',
  },
  {
    type: 'lookup',
    label: 'Lookup',
    icon: GitBranch,
    description: 'Lookup in external table',
  },
  {
    type: 'equation',
    label: 'Equation',
    icon: Calculator,
    description: 'Multi-field calculation with formula',
  },
  {
    type: 'output',
    label: 'Output',
    icon: Flag,
    description: 'Final decision (Act, Attend...)',
  },
];

export function NodePalette({ onDragStart }: NodePaletteProps) {
  return (
    <div className="bg-white rounded-lg shadow-lg p-4 w-64">
      <h3 className="font-bold text-gray-700 mb-3 text-sm uppercase tracking-wide">
        Nodes
      </h3>
      <p className="text-xs text-gray-500 mb-4">
        Drag and drop a node onto the canvas
      </p>

      <div className="space-y-2">
        {nodeItems.map((item) => {
          const Icon = item.icon;
          return (
            <div
              key={item.type}
              role="button"
              aria-label={`Add ${item.label} node: ${item.description}`}
              tabIndex={0}
              className={`
                p-3 rounded-lg border-2 border-dashed cursor-grab
                hover:border-solid hover:shadow-md transition-all
                ${item.type === 'input' ? 'border-blue-300 hover:border-blue-500 hover:bg-blue-50' : ''}
                ${item.type === 'lookup' ? 'border-purple-300 hover:border-purple-500 hover:bg-purple-50' : ''}
                ${item.type === 'equation' ? 'border-amber-300 hover:border-amber-500 hover:bg-amber-50' : ''}
                ${item.type === 'output' ? 'border-green-300 hover:border-green-500 hover:bg-green-50' : ''}
              `}
              draggable
              onDragStart={(e) => onDragStart(e, item.type)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  // Simulate drag start via synthetic event
                  const syntheticEvent = new DragEvent('dragstart');
                  onDragStart(syntheticEvent as unknown as React.DragEvent, item.type);
                }
              }}
            >
              <div className="flex items-center gap-2">
                <Icon
                  size={20}
                  className={`
                    ${item.type === 'input' ? 'text-blue-500' : ''}
                    ${item.type === 'lookup' ? 'text-purple-500' : ''}
                    ${item.type === 'equation' ? 'text-amber-500' : ''}
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
