import React from 'react';
import { COURSE_TYPES } from '../../types';
import type { SmartFolderRule, SmartFolderRules } from '../../services/smartFoldersApi';

interface SmartFolderRuleBuilderProps {
  rules: SmartFolderRules;
  onChange: (rules: SmartFolderRules) => void;
  previewCount?: number | null;
}

const FIELD_OPTIONS = [
  { value: 'course_type', label: 'Course Type' },
  { value: 'difficulty', label: 'Difficulty' },
  { value: 'cook_time', label: 'Cook Time (min)' },
  { value: 'prep_time', label: 'Prep Time (min)' },
  { value: 'servings', label: 'Servings' },
  { value: 'tags', label: 'Tag' },
  { value: 'min_rating', label: 'Average Rating' },
  { value: 'is_public', label: 'Visibility' },
];

const OPERATORS_BY_FIELD: Record<string, Array<{ value: string; label: string }>> = {
  course_type: [
    { value: 'eq', label: 'is' },
    { value: 'neq', label: 'is not' },
  ],
  difficulty: [
    { value: 'eq', label: 'is' },
    { value: 'neq', label: 'is not' },
  ],
  cook_time: [
    { value: 'lte', label: 'at most' },
    { value: 'gte', label: 'at least' },
    { value: 'eq', label: 'exactly' },
  ],
  prep_time: [
    { value: 'lte', label: 'at most' },
    { value: 'gte', label: 'at least' },
    { value: 'eq', label: 'exactly' },
  ],
  servings: [
    { value: 'lte', label: 'at most' },
    { value: 'gte', label: 'at least' },
    { value: 'eq', label: 'exactly' },
  ],
  tags: [
    { value: 'contains', label: 'includes' },
    { value: 'not_contains', label: 'does not include' },
  ],
  min_rating: [
    { value: 'gte', label: 'at least' },
  ],
  is_public: [
    { value: 'eq', label: 'is' },
  ],
};

const DIFFICULTY_OPTIONS = ['Easy', 'Medium', 'Hard'];

const SmartFolderRuleBuilder: React.FC<SmartFolderRuleBuilderProps> = ({
  rules,
  onChange,
  previewCount,
}) => {
  const updateCondition = (index: number, updates: Partial<SmartFolderRule>) => {
    const newConditions = [...rules.conditions];
    newConditions[index] = { ...newConditions[index], ...updates };
    onChange({ ...rules, conditions: newConditions });
  };

  const addCondition = () => {
    onChange({
      ...rules,
      conditions: [
        ...rules.conditions,
        { field: 'course_type', operator: 'eq', value: '' },
      ],
    });
  };

  const removeCondition = (index: number) => {
    const newConditions = rules.conditions.filter((_, i) => i !== index);
    onChange({ ...rules, conditions: newConditions });
  };

  const handleFieldChange = (index: number, field: string) => {
    const operators = OPERATORS_BY_FIELD[field] || [];
    const defaultOp = operators[0]?.value || 'eq';
    let defaultValue: string | number | boolean = '';

    if (field === 'is_public') defaultValue = true;
    else if (['cook_time', 'prep_time', 'servings'].includes(field)) defaultValue = 30;
    else if (field === 'min_rating') defaultValue = 4;

    updateCondition(index, { field, operator: defaultOp, value: defaultValue });
  };

  const renderValueInput = (condition: SmartFolderRule, index: number) => {
    const { field } = condition;

    if (field === 'course_type') {
      return (
        <select
          value={String(condition.value)}
          onChange={(e) => updateCondition(index, { value: e.target.value })}
          className="flex-1 px-2 py-1.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent/20 focus:border-accent"
        >
          <option value="">Select...</option>
          {COURSE_TYPES.map((type) => (
            <option key={type} value={type}>{type}</option>
          ))}
        </select>
      );
    }

    if (field === 'difficulty') {
      return (
        <select
          value={String(condition.value)}
          onChange={(e) => updateCondition(index, { value: e.target.value })}
          className="flex-1 px-2 py-1.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent/20 focus:border-accent"
        >
          <option value="">Select...</option>
          {DIFFICULTY_OPTIONS.map((d) => (
            <option key={d} value={d}>{d}</option>
          ))}
        </select>
      );
    }

    if (field === 'is_public') {
      return (
        <select
          value={String(condition.value)}
          onChange={(e) => updateCondition(index, { value: e.target.value === 'true' })}
          className="flex-1 px-2 py-1.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent/20 focus:border-accent"
        >
          <option value="true">Public</option>
          <option value="false">Private</option>
        </select>
      );
    }

    if (['cook_time', 'prep_time', 'servings', 'min_rating'].includes(field)) {
      return (
        <input
          type="number"
          value={condition.value as number}
          onChange={(e) => updateCondition(index, { value: Number(e.target.value) })}
          min={field === 'min_rating' ? 1 : 0}
          max={field === 'min_rating' ? 5 : undefined}
          step={field === 'min_rating' ? 0.5 : 1}
          className="flex-1 px-2 py-1.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent/20 focus:border-accent w-24"
        />
      );
    }

    // Tags and fallback: text input
    return (
      <input
        type="text"
        value={String(condition.value)}
        onChange={(e) => updateCondition(index, { value: e.target.value })}
        placeholder={field === 'tags' ? 'Tag name...' : 'Value...'}
        className="flex-1 px-2 py-1.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent/20 focus:border-accent"
      />
    );
  };

  return (
    <div className="space-y-4">
      {/* Match mode */}
      <div className="flex items-center gap-2">
        <span className="text-sm text-text-secondary">Match</span>
        <select
          value={rules.match}
          onChange={(e) => onChange({ ...rules, match: e.target.value as 'all' | 'any' })}
          className="px-2 py-1 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent/20 focus:border-accent"
        >
          <option value="all">all conditions</option>
          <option value="any">any condition</option>
        </select>
        {previewCount !== null && previewCount !== undefined && (
          <span className="ml-auto text-sm text-text-secondary">
            {previewCount} recipe{previewCount !== 1 ? 's' : ''} match
          </span>
        )}
      </div>

      {/* Conditions */}
      <div className="space-y-2">
        {rules.conditions.map((condition, index) => (
          <div key={index} className="flex items-center gap-2 flex-wrap sm:flex-nowrap">
            {/* Field */}
            <select
              value={condition.field}
              onChange={(e) => handleFieldChange(index, e.target.value)}
              className="px-2 py-1.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent/20 focus:border-accent min-w-[130px]"
            >
              {FIELD_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>

            {/* Operator */}
            <select
              value={condition.operator}
              onChange={(e) => updateCondition(index, { operator: e.target.value })}
              className="px-2 py-1.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent/20 focus:border-accent min-w-[100px]"
            >
              {(OPERATORS_BY_FIELD[condition.field] || []).map((op) => (
                <option key={op.value} value={op.value}>{op.label}</option>
              ))}
            </select>

            {/* Value */}
            {renderValueInput(condition, index)}

            {/* Remove button */}
            <button
              onClick={() => removeCondition(index)}
              className="p-1.5 text-gray-400 hover:text-red-500 transition-colors flex-shrink-0"
              disabled={rules.conditions.length <= 1}
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        ))}
      </div>

      {/* Add condition */}
      <button
        onClick={addCondition}
        className="flex items-center gap-1 text-sm text-accent hover:text-accent/80 transition-colors"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
        </svg>
        Add condition
      </button>
    </div>
  );
};

export { SmartFolderRuleBuilder };
