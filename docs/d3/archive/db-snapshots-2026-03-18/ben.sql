PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;
CREATE TABLE chats (
      jid TEXT PRIMARY KEY,
      name TEXT,
      last_message_time TEXT,
      channel TEXT,
      is_group INTEGER DEFAULT 0
    );
INSERT INTO chats VALUES('tg:5967394003','Rick','2026-03-18T09:22:01.000Z','telegram',0);
INSERT INTO chats VALUES('tg:8660755707','Ben','2026-03-18T09:42:58.000Z','telegram',0);
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
INSERT INTO messages VALUES('55','tg:5967394003','5967394003','Rick','What cli tools do you have available?','2026-03-17T17:22:09.000Z',0,0);
INSERT INTO messages VALUES('57','tg:5967394003','5967394003','Rick','whats the output of gh auth whoami?','2026-03-17T17:22:59.000Z',0,0);
INSERT INTO messages VALUES('59','tg:5967394003','5967394003','Rick',unistr('Just checking setup configs buddy.\u000a\u000agh and vercel should work, neon is being a pain in the but'),'2026-03-17T17:37:16.000Z',0,0);
INSERT INTO messages VALUES('61','tg:5967394003','5967394003','Rick','Lets do some smoke tests on the halos ecosystem. Ben won''t know about these things when he arrives and doesnt really need to. The hope is that you will be able to use them on his behalf to....do whatever mad shit it is that he wants to do...','2026-03-17T17:38:26.000Z',0,0);
INSERT INTO messages VALUES('63','tg:5967394003','5967394003','Rick','The latter, but good recon. Can you create new notes with memctl?','2026-03-17T17:40:25.000Z',0,0);
INSERT INTO messages VALUES('65','tg:5967394003','5967394003','Rick','I love it when a plan comes together.','2026-03-17T17:41:04.000Z',0,0);
INSERT INTO messages VALUES('67','tg:5967394003','5967394003','Rick','Could you give me a file tree (maybe 3-4 levels deep unless that hits python libraries or something) to indicate the permissions on your surroundings, what you physical are and are not able to do.','2026-03-17T17:42:06.000Z',0,0);
INSERT INTO messages VALUES('69','tg:5967394003','5967394003','Rick','Are your websearch tools functional?','2026-03-17T17:45:05.000Z',0,0);
INSERT INTO messages VALUES('73','tg:5967394003','5967394003','Rick','testing','2026-03-17T20:45:10.000Z',0,0);
INSERT INTO messages VALUES('75','tg:5967394003','5967394003','Rick','what symbols do we ignore around these parts?','2026-03-17T20:50:12.000Z',0,0);
INSERT INTO messages VALUES('77','tg:5967394003','5967394003','Rick','+10 points','2026-03-17T20:51:06.000Z',0,0);
INSERT INTO messages VALUES('79','tg:5967394003','5967394003','Rick','dude','2026-03-17T21:07:04.000Z',0,0);
INSERT INTO messages VALUES('81','tg:5967394003','5967394003','Rick','Test','2026-03-18T03:19:53.000Z',0,0);
INSERT INTO messages VALUES('83','tg:5967394003','5967394003','Rick','and another test','2026-03-18T09:17:44.000Z',0,0);
INSERT INTO messages VALUES('85','tg:5967394003','5967394003','Rick','who am i?','2026-03-18T09:18:02.000Z',0,0);
INSERT INTO messages VALUES('87','tg:5967394003','5967394003','Rick','Marvellous. Ready to meet Ben?','2026-03-18T09:18:25.000Z',0,0);
INSERT INTO messages VALUES('101','tg:5967394003','5967394003','Rick','cool. Well, I would quite like some help sorting out my arse from my elbow','2026-03-18T09:19:54.000Z',0,0);
INSERT INTO messages VALUES('103','tg:5967394003','5967394003','Rick','I keep promising to stay sober but twice a week I just go on a bender, at home, in my underpants, and then my family 100s of incoherent messages','2026-03-18T09:20:45.000Z',0,0);
INSERT INTO messages VALUES('105','tg:5967394003','5967394003','Rick','maybe i should keep a log?','2026-03-18T09:21:02.000Z',0,0);
INSERT INTO messages VALUES('107','tg:5967394003','5967394003','Rick','how would I find it again after today?','2026-03-18T09:21:31.000Z',0,0);
INSERT INTO messages VALUES('109','tg:5967394003','5967394003','Rick','where is ''here''','2026-03-18T09:22:01.000Z',0,0);
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
INSERT INTO router_state VALUES('last_timestamp','2026-03-18T09:22:01.000Z');
INSERT INTO router_state VALUES('last_agent_timestamp','{"tg:5967394003":"2026-03-18T09:22:01.000Z"}');
CREATE TABLE sessions (
      group_folder TEXT PRIMARY KEY,
      session_id TEXT NOT NULL
    );
INSERT INTO sessions VALUES('telegram_main','1e581802-4c48-45b5-a317-25d6852564f0');
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
INSERT INTO onboarding VALUES('5967394003','tg:5967394003','active','2026-03-18T09:19:20.881Z','2026-03-18T09:19:21.123Z');
INSERT INTO onboarding VALUES('8660755707','tg:8660755707','active','2026-03-18T09:24:59.144Z','2026-03-18T09:24:59.242Z');
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
