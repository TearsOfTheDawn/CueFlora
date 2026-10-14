// Core subtitle data

export interface Word {
  text: string;
  startMs: number;
  endMs: number;
  prefix?: string;
}

export interface Cue {
  startMs: number;
  endMs: number;
  text: string;
  words?: Word[];
}

// Language system

export interface IsoInfo {
  code: string | null;
  whisper: boolean;
}

export interface Language {
  name: string;
  iso: IsoInfo;
  bcp47: string | null;
  iso_default?: boolean;
  whisper_variant_prompt?: string;
}

// YouTube caption track (from bridge via internal player API)

export interface CaptionTrack {
  languageCode: string;
  baseUrl?: string;
  url?: string;
  kind?: string;
  isDefault?: boolean;
  name?: { simpleText?: string };
  languageName?: { simpleText?: string };
}

// Native messaging protocol

export interface PingMessage {
  type: 'PING';
}

export interface OnboardingFinishMessage {
  type: 'ONBOARDING_FINISH';
  revision: string;
  languages: { transcription: string; translation: string };
}

export interface OnboardingState { step: number; complete: boolean }
export interface OnboardingFinishResult {
  languagesSaved: boolean;
  step?: number;
  complete?: boolean;
  error?: string;
  reason?: 'revision' | 'languages' | 'progress';
}

export interface TranscribeMessage {
  type: 'TRANSCRIBE_NATIVE';
  jobId: string;
  videoId: string;
  whisperConfig: WhisperConfig;
}

export interface TranslateMessage {
  type: 'TRANSLATE_NATIVE';
  jobId: string;
  cues: Cue[];
  systemPrompt: string;
  translateConfig: TranslateConfig;
  captureId?: string;
  sourceIndexes?: number[];
}

export interface CapturePresentationMessage {
  type: 'CAPTURE_PRESENTATION';
  jobId: string;
  captureId: string;
  sourceCues: Cue[];
  translations: Cue[];
  displayCues: Cue[];
  sourceIndexes: number[][];
  diagnostics: TranslationTimingDiagnostics | null;
}

export interface ProgressMessage {
  type: 'NATIVE_PROGRESS';
  jobId: string;
  stage: string;
  percent?: number;
  speed?: string;
  message?: string;
  raw?: unknown;
}

export type ExtensionMessage =
  | PingMessage
  | import('./credentials').ProtectCredentialMessage
  | import('./credentials').MigrateCredentialsMessage
  | OnboardingFinishMessage
  | TranscribeMessage
  | TranslateMessage
  | CapturePresentationMessage
  | ProgressMessage;

export interface WhisperConfig {
  apiKey: string;
  baseUrl: string;
  model: string;
  language?: string | null;
  prompt?: string;
  maxParallel?: number;
  mbPerReq?: number;
}

export interface TranslateConfig {
  apiKey: string;
  baseUrl: string;
  model: string;
}

export interface NativeTranscribeResult {
  jobId?: string;
  cues?: Cue[];
  error?: string;
  diagnostics?: TranscriptionDiagnostics;
}

export interface NativeTranslateResult {
  evidence?: EvidenceDiagnostics;
  jobId?: string;
  translations?: unknown[];
  error?: string;
  errorKind?: 'output' | 'network' | 'auth' | 'http' | 'protocol';
  finishReason?: string;
  requestCount?: number;
  requestedOutputTokens?: number;
  reasoningEffort?: string;
  promptTokens?: number;
  completionTokens?: number;
  totalTokens?: number;
  reasoningTokens?: number;
  durationMs?: number;
}

export interface TranslationRequestDiagnostics {
  cueCount: number;
  requestedOutputTokens?: number;
  reasoningEffort?: string;
  finishReason?: string;
  promptTokens?: number;
  completionTokens?: number;
  totalTokens?: number;
  reasoningTokens?: number;
  durationMs?: number;
}

export type TranslationQualityReason =
  | 'label-leak'
  | 'extreme-under-translation';

export interface TranslationQualityFlag {
  cueIndex: number;
  reason: TranslationQualityReason;
  sourceInformationCharacters?: number;
  targetInformationCharacters?: number;
  targetWords?: number;
}

export interface TranslationTimingDiagnostics {
  fastCueCountBefore: number;
  fastCueCountAfter: number;
  maxCpsBefore: number;
  maxCpsAfter: number;
  extensions: number;
  merges: number;
  unresolvedFastCueIndexes: number[];
}

export type WorkflowStatus =
  | 'idle'
  | 'transcribing'
  | 'transcription_complete'
  | 'translating'
  | 'complete'
  | 'error'
  | 'cancelled';

export type WorkflowStage = 'transcription' | 'translation';
export type WorkflowStageStatus =
  | 'idle'
  | 'waiting'
  | 'running'
  | 'done'
  | 'error'
  | 'skipped';

export interface WorkflowStageState {
  status: WorkflowStageStatus;
  message: string;
  percent: number | null;
}

export interface EvidenceDiagnostics {
  complete: boolean;
  stages: Record<string, 'complete' | 'incomplete'>;
}

export interface TranscriptionDiagnostics {
  evidence?: EvidenceDiagnostics;
  captureId?: string;
  normalizationVersion?: string;
  emptySegmentCount?: number;
  audioDurationMs?: number;
  rawSegmentCount?: number;
  finalCueCount?: number;
  collapsedWordsRemoved?: number;
  repetitionSanitizations?: number;
}

export interface WorkflowRunDiagnostics {
  jobId: string;
  videoId: string;
  startedAt: number;
  finishedAt?: number;
  durationMs?: number;
  transcription: TranscriptionDiagnostics & {
    startedAt?: number;
    durationMs?: number;
    status: 'pending' | 'running' | 'complete' | 'error' | 'skipped';
    error?: string;
  };
  translation: {
    evidence?: EvidenceDiagnostics;
    startedAt?: number;
    durationMs?: number;
    status: 'pending' | 'running' | 'complete' | 'error' | 'skipped';
    totalCues: number;
    logicalBatches: number;
    physicalRequests: number;
    retries: number;
    repairCalls: number;
    salvagedPositions: number;
    truncatedResponses: number;
    qualityRepairs: number;
    qualityFlags: TranslationQualityFlag[];
    unresolvedQualityFlags: TranslationQualityFlag[];
    timing?: TranslationTimingDiagnostics;
    lastRequest?: TranslationRequestDiagnostics;
    error?: string;
  };
}

export interface WorkflowState {
  status: WorkflowStatus;
  jobId: string | null;
  videoId: string | null;
  error: string | null;
  transcription: WorkflowStageState;
  translation: WorkflowStageState;
  diagnostics: WorkflowRunDiagnostics | null;
}

// State singleton

export interface AppState {
  activeInterval: ReturnType<typeof setInterval> | null;
  initInterval: ReturnType<typeof setInterval> | null;
  transcriptionCues: Cue[];
  translationCues: Cue[];
  availableTracks: CaptionTrack[];
  generatedTracks: Record<string, Cue[]>;
  subtitleCache: Record<string, Cue[]>;
  isPanelOpen: boolean;
  showTranscription: boolean;
  showTranslation: boolean;
  highlightCurrentWord: boolean;
  workflow: WorkflowState;
  overlayOffsetBottom: number;
  subtitleBgOpacity: number;
  _cleanupUI: (() => void) | null;
}

// Translation batch (internal to api.ts)

export interface TranslationBatch {
  cues: Cue[];
  startIndex: number;
  endIndex: number; // exclusive
  sourceChars: number;
}

export interface TranslationCacheMetadata {
  schemaVersion: number;
  pipelineVersion: string;
  sourceFingerprint: string;
  sourceLanguage: string;
  targetLanguage: string;
  model: string;
}

// YouTube JSON3 format shapes (for parsing)

export interface Json3Segment {
  utf8?: string;
  tOffsetMs?: number;
}

export interface Json3Event {
  tStartMs?: number;
  dDurationMs?: number;
  segs?: Json3Segment[];
  aAppend?: number;
}

export interface Json3Data {
  events?: Json3Event[];
}
