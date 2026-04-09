import { useState, useCallback, useMemo } from 'react';

export function useRecipeSelection() {
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [isSelectionMode, setIsSelectionMode] = useState(false);

  const toggleSelection = useCallback((id: number) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }, []);

  const selectAll = useCallback((ids: number[]) => {
    setSelectedIds(new Set(ids));
  }, []);

  const clearSelection = useCallback(() => {
    setSelectedIds(new Set());
  }, []);

  const isSelected = useCallback((id: number) => {
    return selectedIds.has(id);
  }, [selectedIds]);

  const exitSelectionMode = useCallback(() => {
    setIsSelectionMode(false);
    setSelectedIds(new Set());
  }, []);

  const toggleSelectionMode = useCallback(() => {
    setIsSelectionMode(prev => {
      if (prev) {
        // Exiting selection mode — clear selections
        setSelectedIds(new Set());
      }
      return !prev;
    });
  }, []);

  const selectionCount = useMemo(() => selectedIds.size, [selectedIds]);

  return {
    selectedIds,
    isSelectionMode,
    selectionCount,
    toggleSelection,
    selectAll,
    clearSelection,
    isSelected,
    toggleSelectionMode,
    exitSelectionMode,
  };
}
