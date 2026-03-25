import { useState, useEffect } from 'react';
import { X, Trash2, ArrowRight } from 'lucide-react';
import { useTreeStore } from '@/stores/treeStore';
import { useConfirm } from '@/hooks/useConfirm';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';
import type { TreeEdge } from '@/types';

interface EdgeConfigPanelProps {
  edge: TreeEdge;
  onClose: () => void;
}

export function EdgeConfigPanel({ edge, onClose }: EdgeConfigPanelProps) {
  const { nodes, edges, setEdges } = useTreeStore();
  const isAdminUser = useTreeStore((s) => s.isAdmin);
  const { confirm, confirmDialogProps } = useConfirm();
  const [label, setLabel] = useState(typeof edge.label === 'string' ? edge.label : '');

  const sourceNode = nodes.find((n) => n.id === edge.source);
  const targetNode = nodes.find((n) => n.id === edge.target);

  const handleDelete = async () => {
    const ok = await confirm('Delete connection', 'Delete this connection between nodes?');
    if (ok) {
      setEdges(edges.filter((e) => e.id !== edge.id));
      onClose();
    }
  };

  // Find the condition associated with this handle
  const getConditionForHandle = () => {
    if (!sourceNode || !edge.sourceHandle) return null;
    const handleIndex = parseInt(edge.sourceHandle.replace('handle-', ''), 10);
    return sourceNode.data.conditions[handleIndex] || null;
  };

  const condition = getConditionForHandle();

  // Sync local label when edge changes
  useEffect(() => {
    setLabel(typeof edge.label === 'string' ? edge.label : '');
  }, [edge.id, edge.label]);

  // Update edge label
  const handleLabelChange = (newLabel: string) => {
    setLabel(newLabel);
    setEdges(
      edges.map((e) =>
        e.id === edge.id ? { ...e, label: newLabel || undefined } : e
      )
    );
  };

  return (
    <div className="bg-white rounded-lg shadow-lg w-72">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b">
        <h3 className="font-bold text-gray-700">Connection</h3>
        <button
          onClick={onClose}
          className="p-1 hover:bg-gray-100 rounded"
        >
          <X size={20} />
        </button>
      </div>

      <div className={`p-4 space-y-4 ${!isAdminUser() ? 'pointer-events-none opacity-60' : ''}`}>
        {/* Source -> Target */}
        <div className="flex items-center gap-2 text-sm">
          <div className="flex-1 p-2 bg-gray-50 rounded text-center truncate">
            {sourceNode?.data.label || edge.source}
          </div>
          <ArrowRight size={16} className="text-gray-400 flex-shrink-0" />
          <div className="flex-1 p-2 bg-gray-50 rounded text-center truncate">
            {targetNode?.data.label || edge.target}
          </div>
        </div>

        {/* Label */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Label
          </label>
          <input
            type="text"
            value={label}
            onChange={(e) => handleLabelChange(e.target.value)}
            placeholder="E.g.: Critical, Yes, No..."
            className="w-full px-3 py-2 border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          {condition && (
            <p className="text-xs text-gray-500 mt-1">
              Suggestion based on condition: "{condition.label}"
            </p>
          )}
        </div>

        {/* Condition details */}
        {condition && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Associated condition
            </label>
            <div className="p-2 bg-blue-50 rounded-md text-sm">
              <span className="font-mono">
                {condition.operator} {String(condition.value)}
              </span>
            </div>
          </div>
        )}

        {/* Info */}
        <div className="text-xs text-gray-500 bg-gray-50 p-2 rounded">
          The label is displayed on the connection in the canvas.
          Leave empty to hide the label.
        </div>

        {/* Actions */}
        <div className="flex gap-2 pt-2 border-t">
          <button
            onClick={handleDelete}
            className="flex-1 flex items-center justify-center gap-2 p-2 text-red-600 bg-red-50 hover:bg-red-100 rounded-md font-medium"
          >
            <Trash2 size={18} />
            Delete
          </button>
        </div>
      </div>
      <ConfirmDialog {...confirmDialogProps} />
    </div>
  );
}
