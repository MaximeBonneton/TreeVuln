import { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import type { NodeProps } from '@xyflow/react';
import { Database, GitBranch, Flag, Calculator } from 'lucide-react';
import type { TreeNodeData, InputNodeConfig, LookupNodeConfig } from '@/types';
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
  equation: {
    bg: 'bg-amber-50',
    border: 'border-amber-400',
    header: 'bg-amber-500',
    icon: Calculator,
  },
  output: {
    bg: 'bg-green-50',
    border: 'border-green-400',
    header: 'bg-green-500',
    icon: Flag,
  },
};

/** Get input_count from node config (defaults to 1) */
function getInputCount(data: TreeNodeData): number {
  if (data.nodeType === 'output' || data.nodeType === 'equation') return 1;
  const config = data.config as InputNodeConfig | LookupNodeConfig;
  return config.input_count ?? 1;
}

function TreeNodeComponent({ id, data, selected }: TreeNodeProps) {
  const selectNode = useTreeStore((state) => state.selectNode);
  const setHoveredNode = useTreeStore((state) => state.setHoveredNode);
  const style = nodeStyles[data.nodeType];
  const Icon = style.icon;
  const inputCount = getInputCount(data);
  const isMultiInput = inputCount > 1;

  // Pour les nœuds output, utilise la couleur configurée
  const headerStyle =
    data.nodeType === 'output' && 'color' in data.config
      ? { backgroundColor: (data.config as { color: string }).color }
      : undefined;

  // Mode multi-input: layout complètement différent
  if (isMultiInput && data.conditions.length > 0) {
    const numConditions = data.conditions.length;
    const rowHeight = 24; // hauteur d'une ligne de condition en px
    const bandHeight = numConditions * rowHeight;
    const headerHeight = 40; // header
    const infoHeight = 28; // info champ
    const totalBandsHeight = inputCount * bandHeight;

    return (
      <div
        role="group"
        aria-label={`Nœud ${data.nodeType}: ${data.label}`}
        className={`
          min-w-[160px] rounded-lg shadow-md border-2
          ${style.bg} ${style.border}
          ${selected ? 'ring-2 ring-blue-500 ring-offset-2' : ''}
        `}
        onClick={() => selectNode(id)}
      >
        {/* Header pleine largeur */}
        <div
          className={`${style.header} text-white px-3 py-2 flex items-center gap-2 rounded-t-md`}
          style={{ ...headerStyle, height: `${headerHeight}px` }}
        >
          <Icon size={16} />
          <span className="font-medium text-sm flex-1">{data.label}</span>
          <span className="text-xs bg-white/20 px-1.5 py-0.5 rounded">{inputCount} entrées</span>
        </div>

        {/* Info champ */}
        <div
          className="px-3 text-xs text-gray-600 border-b border-gray-200 bg-white/50 flex items-center"
          style={{ height: `${infoHeight}px` }}
        >
          {data.nodeType === 'input' && 'field' in data.config && (
            <span>
              <span className="font-medium">Champ:</span>{' '}
              {(data.config as { field: string }).field || '(non configuré)'}
            </span>
          )}
          {data.nodeType === 'lookup' && 'lookup_table' in data.config && (
            <span>
              <span className="font-medium">Lookup:</span>{' '}
              {(data.config as { lookup_table: string }).lookup_table}
            </span>
          )}
        </div>

        {/* Bandes entrée/sortie */}
        <div
          className="flex flex-col rounded-b-md overflow-hidden"
          onMouseLeave={() => setHoveredNode(null)}
        >
          {Array.from({ length: inputCount }).map((_, inputIdx) => {
            const bandBg = inputIdx % 2 === 0 ? 'bg-white' : 'bg-gray-100';
            return (
              <div
                key={inputIdx}
                className={`relative flex ${bandBg} ${inputIdx > 0 ? 'border-t border-gray-300' : ''} hover:bg-blue-50 transition-colors cursor-pointer`}
                style={{ height: `${bandHeight}px` }}
                onMouseEnter={(e) => {
                  e.stopPropagation();
                  setHoveredNode(id, inputIdx);
                }}
              >
                {/* Ligne pointillée centrée verticalement */}
                <div className="flex-1 flex items-center px-3">
                  <div className="w-full h-0 border-t-2 border-dashed border-gray-300" />
                </div>

                {/* Conditions en colonne */}
                <div className="flex flex-col justify-center border-l border-gray-200">
                  {data.conditions.map((condition, condIdx) => (
                    <div
                      key={`label-${inputIdx}-${condIdx}`}
                      className="flex items-center justify-end px-2 pr-4"
                      style={{ height: `${rowHeight}px` }}
                    >
                      <span className="text-[10px] text-gray-600">{condition.label}</span>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>

        {/* Handles d'entrée - positionnés absolument */}
        {Array.from({ length: inputCount }).map((_, inputIdx) => {
          const bandTop = headerHeight + infoHeight + inputIdx * bandHeight;
          const handleTop = bandTop + bandHeight / 2;
          const topPercent = (handleTop / (headerHeight + infoHeight + totalBandsHeight)) * 100;
          return (
            <Handle
              key={`input-${inputIdx}`}
              type="target"
              position={Position.Left}
              id={`input-${inputIdx}`}
              className="!bg-gray-500 !w-3 !h-3 !border-2 !border-white"
              style={{ top: `${topPercent}%` }}
            />
          );
        })}

        {/* Handles de sortie - positionnés absolument */}
        {Array.from({ length: inputCount }).map((_, inputIdx) =>
          data.conditions.map((_, condIdx) => {
            const handleId = `handle-${inputIdx}-${condIdx}`;
            const handleColor = getHandleColor(id, inputIdx * 100 + condIdx);
            const bandTop = headerHeight + infoHeight + inputIdx * bandHeight;
            const handleTop = bandTop + (condIdx + 0.5) * rowHeight;
            const topPercent = (handleTop / (headerHeight + infoHeight + totalBandsHeight)) * 100;
            return (
              <Handle
                key={handleId}
                type="source"
                position={Position.Right}
                id={handleId}
                className="!w-3 !h-3 !border-2 !border-white"
                style={{ backgroundColor: handleColor, top: `${topPercent}%` }}
              />
            );
          })
        )}
      </div>
    );
  }

  // Mode standard (single-input ou output)
  return (
    <div
      role="group"
      aria-label={`Nœud ${data.nodeType}: ${data.label}`}
      className={`
        min-w-[140px] rounded-lg shadow-md border-2 flex
        ${style.bg} ${style.border}
        ${selected ? 'ring-2 ring-blue-500 ring-offset-2' : ''}
      `}
      onClick={() => selectNode(id)}
    >
      {/* Handle d'entrée unique */}
      <Handle
        type="target"
        position={Position.Left}
        className="!bg-gray-400 !w-3 !h-3"
      />

      {/* Contenu principal */}
      <div className="flex-1">
        {/* Header */}
        <div
          className={`${style.header} text-white px-3 py-2 rounded-tl-md ${data.nodeType === 'output' || data.conditions.length === 0 ? 'rounded-tr-md' : ''} flex items-center gap-2`}
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

          {data.nodeType === 'equation' && 'formula' in data.config && (
            <div className="font-mono text-[10px] text-amber-700 truncate max-w-[120px]" title={(data.config as { formula: string }).formula}>
              {((data.config as { formula: string }).formula || '(non configuré)').slice(0, 30)}
              {((data.config as { formula: string }).formula || '').length > 30 ? '...' : ''}
            </div>
          )}

          {data.nodeType === 'output' && 'decision' in data.config && (
            <div className="font-bold text-base">
              {(data.config as { decision: string }).decision}
            </div>
          )}
        </div>
      </div>

      {/* Handles de sortie pour single-input */}
      {data.nodeType !== 'output' && data.conditions.length > 0 && (
        <div className="border-l border-gray-200 flex flex-col justify-around py-1 min-w-[60px] pr-3">
          {data.conditions.map((condition, index) => {
            const handleColor = getHandleColor(id, index);
            const totalConditions = data.conditions.length;
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
