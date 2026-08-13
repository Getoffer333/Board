export interface Resume {
  id: number
  version_name: string
  direction_tags: string[]
  file_path: string | null
  file_name: string | null
  content_text: string
  highlights: string[]
  is_active: number
  note: string
  created_at: string
  updated_at: string
}

export interface JD {
  id: number
  company: string
  title: string
  direction_tag: string
  url: string
  source: string
  location: string
  salary_range: string
  raw_text: string
  parsed_json: {
    responsibilities: string[]
    requirements: string[]
    keywords: string[]
    years_required?: number | null
    education_required?: string | null
    highlights: string[]
  } | null
  ai_parsed: number
  direction_alert: string | null
  match_score: number
  status: string
  note: string
  created_at: string
  updated_at: string
}

export interface Application {
  id: number
  jd_id: number
  resume_id: number
  contact_id: number | null
  company_snapshot: string
  title_snapshot: string
  direction_tag: string
  status: string
  channel: string
  priority: string
  applied_at: string
  stage_entered_at: string
  next_followup_at: string | null
  expected_salary: string
  offer_salary: number | null
  close_reason: string | null
  note: string
  created_at: string
  updated_at: string
  interviews?: Interview[]
}

export interface Interview {
  id: number
  application_id: number
  round: string
  scheduled_at: string
  duration_min: number
  mode: string
  location: string
  interviewers: { name: string; role: string }[]
  questions: { q: string; my_answer: string; score: number }[]
  went_well?: string
  went_bad?: string
  action_items?: string
  result?: string
  self_score?: number
  unanswered?: string[]
  bank?: { question: string; category: string }[]
  company?: string
  direction_tag?: string
  created_at?: string
}

export interface Question {
  id: number
  question: string
  category: string
  direction_tag: string
  company: string
  answer_hint: string
  mastered: number
  freq?: number
}

export interface Contact {
  id: number
  name: string
  org: string
  role: string
  wechat: string
  phone: string
  email: string
  warmth: string
  last_contact_at: string | null
  followup_cycle_days: number
  next_followup_at: string | null
  note: string
}

export interface SkillLog {
  id: number
  log_date: string
  duration_min: number
  content: string
}

export interface Skill {
  id: number
  name: string
  direction_tag: string
  category: string
  current_level: string
  target_level: string
  source: string
  source_ref: string
  plan: string
  status: string
  logs: SkillLog[]
  log_count: number
}

export interface Settings {
  primary_direction: string
  backup_directions: string
  owner_name: string
  years_experience: string
  education: string
  current_city: string
  llm_enabled: string
  llm_base_url: string
  llm_api_key: string
  llm_model: string
}

export interface FunnelStat {
  total: number
  counts: Record<string, number>
  series: { status: string; label: string; count: number; rate_from_prev: number | null; rate_from_start: number }[]
}

export interface DirectionStat {
  direction: string
  applications: number
  interviews: number
  offers: number
  closed: number
  interview_rate: number
  offer_rate: number
}

export interface ResumeVersionStat {
  id: number
  version: string
  direction: string
  used: number
  interviews: number
  offers: number
}

export interface Overdue {
  type: string
  level: string
  title: string
  detail: string
  entity: string
  entity_id: number
}

export interface SummaryStat {
  total_applications: number
  active: number
  interviews: number
  offers: number
  resumes: number
  jds: number
  contacts: number
  questions: number
  skills: number
  scripts: number
  reminders: number
}

export interface MatchLocal {
  jd_id: number
  resume_id: number
  score: number
  dimension_scores: Record<string, number>
  matched_points: string[]
  missing_points: string[]
  suggestion: string
  source: string
}

export interface SuggestedSkill {
  name: string
  direction_tag: string
  source: string
  category: string
}

export interface TimelineItem {
  date: string
  type: string
  company?: string
  title?: string
  summary?: string
}

export interface JDRecommendation {
  jd_id: number
  company: string
  title: string
  direction: string
  location: string
  salary: string
  match_score: number
  matched_resume: string
  applied: boolean
}

export interface WeeklySnapshot {
  this_week: { start: string; end: string; applications: number }
  next_week: { start: string; end: string; interviews: number; followups: number }
}
