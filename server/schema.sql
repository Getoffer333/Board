PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS resume (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  version_name TEXT NOT NULL UNIQUE,
  direction_tags TEXT NOT NULL DEFAULT '[]',
  file_path TEXT,
  file_name TEXT,
  content_text TEXT,
  highlights TEXT NOT NULL DEFAULT '[]',
  is_active INTEGER NOT NULL DEFAULT 1,
  note TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS jd (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  company TEXT NOT NULL,
  title TEXT NOT NULL,
  direction_tag TEXT NOT NULL,
  url TEXT,
  source TEXT,
  location TEXT,
  salary_range TEXT,
  raw_text TEXT,
  parsed_json TEXT NOT NULL DEFAULT '{}',
  status TEXT NOT NULL DEFAULT 'active',
  note TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS contact (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  org TEXT,
  role TEXT NOT NULL DEFAULT '内推人',
  wechat TEXT,
  phone TEXT,
  email TEXT,
  warmth TEXT NOT NULL DEFAULT '一般',
  last_contact_at TEXT,
  followup_cycle_days INTEGER NOT NULL DEFAULT 14,
  next_followup_at TEXT,
  note TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS application (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  jd_id INTEGER REFERENCES jd(id) ON DELETE SET NULL,
  resume_id INTEGER NOT NULL REFERENCES resume(id),
  contact_id INTEGER REFERENCES contact(id) ON DELETE SET NULL,
  company_snapshot TEXT NOT NULL,
  title_snapshot TEXT NOT NULL,
  direction_tag TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'intention',
  channel TEXT NOT NULL DEFAULT '官网',
  priority TEXT NOT NULL DEFAULT '中',
  applied_at TEXT,
  stage_entered_at TEXT NOT NULL,
  next_followup_at TEXT,
  expected_salary TEXT,
  offer_salary TEXT,
  close_reason TEXT,
  note TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS interview (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  application_id INTEGER NOT NULL REFERENCES application(id) ON DELETE CASCADE,
  round TEXT NOT NULL DEFAULT '一面',
  scheduled_at TEXT,
  duration_min INTEGER,
  mode TEXT NOT NULL DEFAULT '线上',
  location TEXT,
  interviewers TEXT NOT NULL DEFAULT '[]',
  questions TEXT NOT NULL DEFAULT '[]',
  went_well TEXT,
  went_bad TEXT,
  action_items TEXT,
  result TEXT NOT NULL DEFAULT 'pending',
  self_score INTEGER,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS interview_question (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  question TEXT NOT NULL,
  category TEXT NOT NULL DEFAULT '行为',
  direction_tag TEXT,
  frequency INTEGER NOT NULL DEFAULT 1,
  source_interview_id INTEGER REFERENCES interview(id) ON DELETE SET NULL,
  company TEXT,
  answer_hint TEXT,
  mastered INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS skill (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  direction_tag TEXT,
  category TEXT,
  current_level INTEGER NOT NULL DEFAULT 1,
  target_level INTEGER NOT NULL DEFAULT 4,
  source TEXT NOT NULL DEFAULT '自评',
  source_ref TEXT,
  plan TEXT,
  status TEXT NOT NULL DEFAULT '进行中',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_skill_name_dir
  ON skill(name, IFNULL(direction_tag, ''));

CREATE TABLE IF NOT EXISTS skill_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  skill_id INTEGER NOT NULL REFERENCES skill(id) ON DELETE CASCADE,
  log_date TEXT NOT NULL,
  duration_min INTEGER NOT NULL DEFAULT 30,
  content TEXT,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS match_result (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  jd_id INTEGER NOT NULL REFERENCES jd(id) ON DELETE CASCADE,
  resume_id INTEGER NOT NULL REFERENCES resume(id) ON DELETE CASCADE,
  score INTEGER NOT NULL DEFAULT 0,
  dimension_scores TEXT NOT NULL DEFAULT '{}',
  matched_points TEXT NOT NULL DEFAULT '[]',
  missing_points TEXT NOT NULL DEFAULT '[]',
  suggestion TEXT,
  source TEXT NOT NULL DEFAULT 'local',
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS activity_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL,
  entity_type TEXT NOT NULL,
  entity_id INTEGER,
  action TEXT NOT NULL,
  summary TEXT
);

CREATE TABLE IF NOT EXISTS setting (
  key TEXT PRIMARY KEY,
  value TEXT
);

CREATE INDEX IF NOT EXISTS idx_app_status ON application(status);
CREATE INDEX IF NOT EXISTS idx_app_dir ON application(direction_tag);
CREATE INDEX IF NOT EXISTS idx_app_resume ON application(resume_id);
CREATE INDEX IF NOT EXISTS idx_itv_app ON interview(application_id);
CREATE INDEX IF NOT EXISTS idx_log_ts ON activity_log(ts);
