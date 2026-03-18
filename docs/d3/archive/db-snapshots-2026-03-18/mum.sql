PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;
CREATE TABLE chats (
      jid TEXT PRIMARY KEY,
      name TEXT,
      last_message_time TEXT,
      channel TEXT,
      is_group INTEGER DEFAULT 0
    );
INSERT INTO chats VALUES('tg:5967394003','Rick','2026-03-18T03:53:56.000Z','telegram',0);
CREATE TABLE messages (
      id TEXT,
      chat_jid TEXT,
      sender TEXT,
      sender_name TEXT,
      content TEXT,
      timestamp TEXT,
      is_from_me INTEGER,
      is_bot_message INTEGER DEFAULT 0,
      PRIMARY KEY (id, chat_jid),
      FOREIGN KEY (chat_jid) REFERENCES chats(jid)
    );
CREATE TABLE scheduled_tasks (
      id TEXT PRIMARY KEY,
      group_folder TEXT NOT NULL,
      chat_jid TEXT NOT NULL,
      prompt TEXT NOT NULL,
      schedule_type TEXT NOT NULL,
      schedule_value TEXT NOT NULL,
      next_run TEXT,
      last_run TEXT,
      last_result TEXT,
      status TEXT DEFAULT 'active',
      created_at TEXT NOT NULL
    , context_mode TEXT DEFAULT 'isolated');
CREATE TABLE task_run_logs (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      task_id TEXT NOT NULL,
      run_at TEXT NOT NULL,
      duration_ms INTEGER NOT NULL,
      status TEXT NOT NULL,
      result TEXT,
      error TEXT,
      FOREIGN KEY (task_id) REFERENCES scheduled_tasks(id)
    );
CREATE TABLE router_state (
      key TEXT PRIMARY KEY,
      value TEXT NOT NULL
    );
CREATE TABLE sessions (
      group_folder TEXT PRIMARY KEY,
      session_id TEXT NOT NULL
    );
CREATE TABLE registered_groups (
      jid TEXT PRIMARY KEY,
      name TEXT NOT NULL,
      folder TEXT NOT NULL UNIQUE,
      trigger_pattern TEXT NOT NULL,
      added_at TEXT NOT NULL,
      container_config TEXT,
      requires_trigger INTEGER DEFAULT 1
    , is_main INTEGER DEFAULT 0);
INSERT INTO registered_groups VALUES('tg:5967394003','Rick Hallett','telegram_main','@Andy','2026-03-15T16:02:06.122Z',NULL,0,1);
CREATE TABLE onboarding (
      sender_id TEXT PRIMARY KEY,
      chat_jid TEXT NOT NULL,
      state TEXT NOT NULL DEFAULT 'first_contact',
      waiver_accepted_at TEXT,
      updated_at TEXT NOT NULL
    );
CREATE TABLE assessments (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      sender_id TEXT NOT NULL,
      chat_jid TEXT NOT NULL,
      question_key TEXT NOT NULL,
      question_text TEXT NOT NULL,
      phase TEXT NOT NULL,
      response_type TEXT NOT NULL,
      response TEXT NOT NULL,
      asked_at TEXT NOT NULL,
      answered_at TEXT NOT NULL,
      conversation_count INTEGER,
      session_context TEXT,
      UNIQUE(sender_id, question_key)
    );
CREATE INDEX idx_timestamp ON messages(timestamp);
CREATE INDEX idx_next_run ON scheduled_tasks(next_run);
CREATE INDEX idx_status ON scheduled_tasks(status);
CREATE INDEX idx_task_run_logs ON task_run_logs(task_id, run_at);
COMMIT;
