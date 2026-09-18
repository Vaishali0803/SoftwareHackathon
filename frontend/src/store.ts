import { create } from 'zustand'
import type {
  DatasetProfile,
  PreprocessingResult,
  GenerationStatus,
  ValidationReport,
  PrivacyReport,
  WorkflowStep,
} from './types'

interface Store {
  // Data
  dataset: DatasetProfile | null
  preprocessing: PreprocessingResult | null
  generation: GenerationStatus | null
  validation: ValidationReport | null
  privacy: PrivacyReport | null
  currentStep: WorkflowStep

  // Actions
  setDataset: (d: DatasetProfile | null) => void
  setPreprocessing: (p: PreprocessingResult | null) => void
  setGeneration: (g: GenerationStatus | null) => void
  setValidation: (v: ValidationReport | null) => void
  setPrivacy: (p: PrivacyReport | null) => void
  reset: () => void
}

const initial = {
  dataset: null,
  preprocessing: null,
  generation: null,
  validation: null,
  privacy: null,
  currentStep: 'idle' as WorkflowStep,
}

export const useStore = create<Store>((set) => ({
  ...initial,

  setDataset: (d) =>
    set({ dataset: d, currentStep: d ? 'uploaded' : 'idle' }),

  setPreprocessing: (p) =>
    set({ preprocessing: p, currentStep: p ? 'preprocessed' : 'uploaded' }),

  setGeneration: (g) =>
    set((state) => ({
      generation: g,
      currentStep:
        g?.status === 'done'
          ? 'done'
          : g?.status === 'error'
          ? state.currentStep
          : 'generating',
    })),

  setValidation: (v) => set({ validation: v }),

  setPrivacy: (p) => set({ privacy: p }),

  reset: () => set(initial),
}))
