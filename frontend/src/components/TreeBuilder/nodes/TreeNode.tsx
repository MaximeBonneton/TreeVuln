import { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import type { NodeProps } from '@xyflow/react';
import { Database, GitBranch, Flag } from 'lucide-react';
import type { TreeNodeData } from '@/types';
import { useTreeStore } from '@/stores/treeStore';
import { getHandleColor } from '../edges';

type TreeNodeProps = NodeProps & {
  data: TreeNodeData;
};

const nodeStyles = {
  input: {
    bg: 'bg-blue-50',
    border: 'border-blue-400',
    header: 'bg-blue-500',
    icon: Database,
  },
  lookup: {
    bg: 'bg-purple-50',
    border: 'border-purple-400',
    header: 'bg-purple-500',
    icon: GitBranch,
  },
  output: {
    bg: 'bg-green-50',
    border: 'border-green-400',
    header: 'bg-green-500',
    icon: Flag,
  },
};

function TreeNodeComponent({ id, data, selected }: TreeNodeProps) {
  const selectNode = useTreeStore((state) => state.selectNode);
  const style = nodeStyles[data.nodeType];
  const Icon = style.icon;

  // Pour les nœuds output, utilise la couleur configurée
  const headerBg =
    data.nodeType === 'output' && 'decision' in data.config
      ? undefined
      : undefined;
  const headerStyle =
    data.nodeType === 'output' && 'color' in data.config
      ? { backgroundColor: (data.config as { color: string }).color }
      : undefined;

  return (
    <div
      className={`
        min-w-[140px] rounded-lg shadow-md border-2 flex
        ${style.bg} ${style.border}
        ${selected ? 'ring-2 ring-blue-500 ring-offset-2' : ''}
      `}
      onClick={() => selectNode(id)}
    >
      {/* Handle d'entrée à gauche */}
      <Handle
        type="target"
        position={Position.Left}
        className="!bg-gray-400 !w-3 !h-3"
      />

      {/* Contenu principal */}
      <div className="flex-1">
        {/* Header */}
        <div
          className={`${headerBg || style.header} text-white px-3 py-2 rounded-tl-md ${data.nodeType === 'output' || data.conditions.length === 0 ? 'rounded-tr-md' : ''} flex items-center gap-2`}
          style={headerStyle}
        >
          <Icon size={16} />
          <span className="font-medium text-sm">{data.label}</span>
        </div>

        {/* Body */}
        <div className="px-3 py-2 text-xs text-gray-600">
          {data.nodeType === 'input' && 'field' in data.config && (
            <div>
              <span className="font-medium">Champ:</span>{' '}
              {(data.config as { field: string }).field || '(non configuré)'}
            </div>
          )}

          {data.nodeType === 'lookup' && 'lookup_table' in data.config && (
            <div>
              <span className="font-medium">Lookup:</span>{' '}
              {(data.config as { lookup_table: string }).lookup_table}
            </div>
          )}

          {data.nodeType === 'output' && 'decision' in data.config && (
            <div className="font-bold text-base">
              {(data.config as { decision: string }).decision}
            </div>
          )}
        </div>
      </div>

      {/* Handles de sortie à droite pour les conditions */}
      {data.nodeType !== 'output' && data.conditions.length > 0 && (
        <div className="border-l border-gray-200 flex flex-col justify-around py-1 min-w-[60px] pr-3">
          {data.conditions.map((condition, index) => {
            const handleColor = getHandleColor(id, index);
            const totalConditions = data.conditions.length;
            // Calcule la position verticale du handle (réparti uniformément)
            const topPercent = ((index + 0.5) / totalConditions) * 100;
            return (
              <div
                key={index}
                className="flex items-center justify-end text-xs py-0.5"
              >
                <span className="text-gray-500 truncate max-w-[50px]">{condition.label}</span>
                <Handle
                  type="source"
                  position={Position.Right}
                  id={`handle-${index}`}
                  className="!w-2.5 !h-2.5 !border-2 !border-white"
                  style={{
                    backgroundColor: handleColor,
                    top: `${topPercent}%`,
                  }}
                />
              </div>
            );
          })}
        </div>
      )}

      {/* Handle de sortie unique pour output ou nœuds sans conditions */}
      {(data.nodeType === 'output' || data.conditions.length === 0) && (
        <Handle
          type="source"
          position={Position.Right}
          className="!bg-gray-400 !w-3 !h-3"
        />
      )}
    </div>
  );
}

export const TreeNode = memo(TreeNodeComponent);
