// File: frontend/src/types/trainer.ts

export type TrainerMode = 'spread' | 'recognition';

export interface CompletedQuestion {
  questionId: string;
  questionType: TrainerMode;
  completedAt: number; // Unix timestamp
  isCorrect: boolean;
  sessionId?: string;
}

export interface SessionProgress {
  sessionId: string;
  startedAt: number;
  questionsAttempted: number;
  questionsCorrect: number;
  currentStreak: number;
  questionIds: string[];
}

export interface CompletionData {
  questions: Map<string, CompletedQuestion>; // questionId -> completion data
  sessions: Map<string, SessionProgress>; // sessionId -> session data
  lastCleanup: number; // When localStorage was last cleaned
}

export interface TrainerStoreState {
  // Existing state (unchanged)
  mode: TrainerMode | null;
  balance: TrainerBalanceSchema | null;
  progress: TrainerProgressSchema | null;
  currentSpreadQuestion: SpreadQuestionSchema | null;
  currentRecognitionQuestion: RecognitionQuestionSchema | null;

  // New completion tracking state
  completionData: CompletionData;
  currentSessionId: string | null;
  isTrackingEnabled: boolean;
}

// API Schema types from existing trainer store
export interface TrainerBalanceSchema {
  trainer_attempts_count: number;
  has_subscription: boolean;
  out_of_trainer_attempts_times_count: number;
  trainer_gift_acquired: boolean;
}

export interface TrainerProgressSchema {
  user_id: number;
  // Spread stats
  spread_questions_answered: number;
  spread_correct_answers: number;
  spread_current_streak: number;
  spread_best_streak: number;
  spread_last_session_date: string | null;
  // Recognition stats
  cards_studied: number[];
  cards_mastery_levels: Record<string, number>;
  recognition_questions_answered: number;
  recognition_correct_answers: number;
  recognition_current_streak: number;
  recognition_best_streak: number;
  recognition_last_session_date: string | null;
  // General stats
  total_sessions: number;
  total_study_time: number;
}

export interface TarotCardSchema {
  id: number;
  name: string;
  key: string;
  image_url: string;
  meaning_upright: string;
  meaning_reversed: string;
  suit?: string;
  number?: number;
}

export interface SpreadQuestionSchema {
  id: string;
  category: string;
  difficulty: string;
  question_text: string;
  cards: TarotCardSchema[];
  answers: {
    correct: string;
    options: string[];
  };
  explanation: string;
}

export interface RecognitionQuestionSchema {
  id: string;
  category: string;
  difficulty: string;
  keywords: string[];
  target_card: TarotCardSchema;
  card_options: TarotCardSchema[];
  explanation: string;
}

export interface AnswerResultSchema {
  correct: boolean;
  explanation: string;
  correct_answer?: string | null;
  correct_card_id?: number | null;
  progress: TrainerProgressSchema;
  balance: TrainerBalanceSchema;
}

// Local storage key constants
export const TRAINER_STORAGE_KEY = 'trainer_completion_data';
export const TRAINER_SESSION_KEY = 'trainer_current_session';
export const STORAGE_VERSION = '1.0';
export const STORAGE_EXPIRY_HOURS = 24; // Hours before cleaning old data
export const MAX_STORED_QUESTIONS = 100; // Maximum questions to keep in localStorage
