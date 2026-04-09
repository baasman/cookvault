import React, { useState, useRef, useEffect, useCallback } from 'react';
import type { Instruction } from '../../types';
import { detectTimers, detectDonenessCues } from '../../utils/timerDetection';
import { recipesEngagementApi } from '../../services/recipesEngagementApi';
import { CookingModeTimer } from './CookingModeTimer';

interface CookingModeStepProps {
  instruction: Instruction;
  recipeId: number;
  stepNumber: number;
}

const CookingModeStep: React.FC<CookingModeStepProps> = ({
  instruction,
  recipeId,
  stepNumber,
}) => {
  const timers = detectTimers(instruction.text);
  const cues = detectDonenessCues(instruction.text);
  const imageUrl = instruction.cloudinary_url || instruction.image_url;
  const [noteText, setNoteText] = useState(instruction.user_note || '');
  const [isSaving, setIsSaving] = useState(false);
  const [showNote, setShowNote] = useState(!!instruction.user_note);
  const saveTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isDirtyRef = useRef(false);
  const prevInstructionIdRef = useRef(instruction.id);

  // Sync note text only when navigating to a different step
  useEffect(() => {
    if (prevInstructionIdRef.current !== instruction.id) {
      // Navigated to a new step — flush any pending save for the old step, then reset
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current);
      }
      setNoteText(instruction.user_note || '');
      setShowNote(!!instruction.user_note);
      isDirtyRef.current = false;
      prevInstructionIdRef.current = instruction.id;
    }
  }, [instruction.id, instruction.user_note]);

  const saveNote = useCallback(async (content: string) => {
    setIsSaving(true);
    try {
      await recipesEngagementApi.saveInstructionNote(recipeId, instruction.id, content);
      isDirtyRef.current = false;
    } catch (error) {
      console.error('Failed to save instruction note:', error);
    } finally {
      setIsSaving(false);
    }
  }, [recipeId, instruction.id]);

  const handleNoteChange = useCallback((value: string) => {
    setNoteText(value);
    isDirtyRef.current = true;

    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current);
    }
    saveTimeoutRef.current = setTimeout(() => {
      saveNote(value);
    }, 1200);
  }, [saveNote]);

  // Flush pending save on unmount
  useEffect(() => {
    return () => {
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current);
      }
      // Save immediately on unmount if dirty
      if (isDirtyRef.current) {
        recipesEngagementApi.saveInstructionNote(recipeId, instruction.id, noteText).catch(() => {});
      }
    };
  }, [recipeId, instruction.id, noteText]);

  return (
    <div className="px-6 py-4">
      {/* Step number badge */}
      <div className="flex items-center gap-3 mb-6">
        <div
          className="w-10 h-10 lg:w-14 lg:h-14 rounded-full flex items-center justify-center text-white font-bold text-lg lg:text-2xl flex-shrink-0"
          style={{ backgroundColor: '#f15f1c' }}
        >
          {stepNumber}
        </div>
        <span className="text-sm lg:text-base font-medium text-gray-400">Step {stepNumber}</span>
      </div>

      {/* Step image */}
      {imageUrl && (
        <div className="mb-5 rounded-xl overflow-hidden">
          <img
            src={imageUrl}
            alt={`Step ${stepNumber}`}
            className="w-full max-h-[40vh] object-cover"
            loading="eager"
          />
        </div>
      )}

      {/* Instruction text */}
      <p className="text-xl md:text-2xl lg:text-3xl leading-relaxed lg:leading-relaxed" style={{ color: '#1c120d' }}>
        {instruction.text}
      </p>

      {/* Detected timers with doneness cues */}
      {timers.map((timer, i) => (
        <CookingModeTimer key={`${stepNumber}-${i}`} timer={timer} cues={cues} stepNumber={stepNumber} />
      ))}

      {/* Doneness cues without a timer — still useful to highlight */}
      {timers.length === 0 && cues.length > 0 && (
        <div className="mt-4 flex flex-wrap gap-2">
          {cues.map((cue, i) => (
            <span
              key={i}
              className="inline-flex items-center gap-1 text-sm px-2.5 py-1 rounded-full bg-blue-50 text-blue-700"
            >
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
              </svg>
              {cue.text}
            </span>
          ))}
        </div>
      )}

      {/* Note section */}
      <div className="mt-6">
        {!showNote ? (
          <button
            onClick={() => setShowNote(true)}
            className="flex items-center gap-2 text-sm text-gray-400 hover:text-gray-600"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
            </svg>
            Add a note for this step
          </button>
        ) : (
          <div className="border border-gray-200 rounded-xl p-3 bg-amber-50/50">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium text-amber-700 flex items-center gap-1">
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                </svg>
                Your note
              </span>
              {isSaving && (
                <span className="text-xs text-gray-400">Saving...</span>
              )}
            </div>
            <textarea
              value={noteText}
              onChange={(e) => handleNoteChange(e.target.value)}
              placeholder="Tip, modification, or reminder..."
              className="w-full bg-transparent text-base text-gray-700 resize-none outline-none placeholder-gray-400"
              rows={2}
              maxLength={500}
            />
          </div>
        )}
      </div>
    </div>
  );
};

export { CookingModeStep };
