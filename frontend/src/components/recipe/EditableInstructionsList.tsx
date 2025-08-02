import React, { useState } from 'react';
import { Button } from '../ui';

interface EditableInstructionsListProps {
  instructions: string[];
  onChange: (instructions: string[]) => void;
}

export const EditableInstructionsList: React.FC<EditableInstructionsListProps> = ({
  instructions,
  onChange,
}) => {
  const [editingIndex, setEditingIndex] = useState<number | null>(null);

  const addInstruction = () => {
    onChange([...instructions, '']);
    setEditingIndex(instructions.length);
  };

  const updateInstruction = (index: number, value: string) => {
    const updated = [...instructions];
    updated[index] = value;
    onChange(updated);
  };

  const removeInstruction = (index: number) => {
    const updated = instructions.filter((_, i) => i !== index);
    onChange(updated);
    if (editingIndex === index) {
      setEditingIndex(null);
    }
  };

  const moveInstruction = (index: number, direction: 'up' | 'down') => {
    const newIndex = direction === 'up' ? index - 1 : index + 1;
    if (newIndex < 0 || newIndex >= instructions.length) return;

    const updated = [...instructions];
    [updated[index], updated[newIndex]] = [updated[newIndex], updated[index]];
    onChange(updated);
    
    if (editingIndex === index) {
      setEditingIndex(newIndex);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-medium" style={{color: '#1c120d'}}>
          Instructions ({instructions.length} steps)
        </h3>
        <Button onClick={addInstruction} variant="primary" size="sm">
          Add Step
        </Button>
      </div>

      <div className="space-y-3">
        {instructions.map((instruction, index) => (
          <div
            key={index}
            className="border rounded-lg p-4 bg-background-secondary"
            style={{borderColor: '#e8d7cf'}}
          >
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center space-x-2">
                <div className="flex-shrink-0 w-8 h-8 bg-accent text-black rounded-full flex items-center justify-center font-medium">
                  {index + 1}
                </div>
                <div className="flex space-x-1">
                  <button
                    onClick={() => moveInstruction(index, 'up')}
                    disabled={index === 0}
                    className="p-1 text-text-secondary hover:text-text-primary disabled:opacity-50"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
                    </svg>
                  </button>
                  <button
                    onClick={() => moveInstruction(index, 'down')}
                    disabled={index === instructions.length - 1}
                    className="p-1 text-text-secondary hover:text-text-primary disabled:opacity-50"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                  </button>
                </div>
              </div>
              <div className="flex space-x-2">
                <button
                  onClick={() => setEditingIndex(editingIndex === index ? null : index)}
                  className="p-1 text-text-secondary hover:text-accent"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                  </svg>
                </button>
                <button
                  onClick={() => removeInstruction(index)}
                  className="p-1 text-text-secondary hover:text-red-500"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                </button>
              </div>
            </div>

            {editingIndex === index ? (
              <div>
                <label className="block text-sm font-medium text-text-secondary mb-2">
                  Step {index + 1} Instructions
                </label>
                <textarea
                  value={instruction}
                  onChange={(e) => updateInstruction(index, e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-accent focus:border-transparent"
                  rows={4}
                  placeholder="Describe what to do in this step..."
                  required
                />
                <div className="mt-2 flex justify-end space-x-2">
                  <button
                    onClick={() => setEditingIndex(null)}
                    className="px-3 py-1 text-sm text-text-secondary hover:text-text-primary"
                  >
                    Done
                  </button>
                </div>
              </div>
            ) : (
              <div className="text-text-primary leading-relaxed">
                {instruction || (
                  <span className="text-text-secondary italic">
                    Click edit to add instruction text
                  </span>
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      {instructions.length === 0 && (
        <div className="text-center py-8">
          <p className="text-text-secondary mb-4">No instructions added yet</p>
          <Button onClick={addInstruction} variant="primary" size="sm">
            Add First Step
          </Button>
        </div>
      )}

      {instructions.length > 0 && (
        <div className="text-center pt-4">
          <Button onClick={addInstruction} variant="secondary" size="sm">
            Add Another Step
          </Button>
        </div>
      )}
    </div>
  );
};