export interface AskRequest {
  type: string;
  sid: string;
  audioData?: string;
  text?: string;
}

export interface AskResponse {
  type: string;
  text: string;
  videoPath: string | null;
  confidence: number;
  sources: string[];
}

export interface KnowledgeDoc {
  id: string;
  title: string;
  content: string;
  category: string;
}
