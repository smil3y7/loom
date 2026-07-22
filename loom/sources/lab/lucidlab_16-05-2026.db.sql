BEGIN TRANSACTION;
CREATE TABLE IF NOT EXISTS "alembic_version" (
	"version_num"	VARCHAR(32) NOT NULL,
	CONSTRAINT "alembic_version_pkc" PRIMARY KEY("version_num")
);
CREATE TABLE IF NOT EXISTS "course_lessons" (
	"id"	INTEGER NOT NULL,
	"module_id"	INTEGER NOT NULL,
	"slug"	VARCHAR(50) NOT NULL,
	"order"	INTEGER,
	PRIMARY KEY("id"),
	FOREIGN KEY("module_id") REFERENCES "course_modules"("id")
);
CREATE TABLE IF NOT EXISTS "course_modules" (
	"id"	INTEGER NOT NULL,
	"slug"	VARCHAR(50) NOT NULL,
	"order"	INTEGER,
	PRIMARY KEY("id"),
	UNIQUE("slug")
);
CREATE TABLE IF NOT EXISTS "dream_entries" (
	"id"	INTEGER NOT NULL,
	"sleep_cycle_id"	INTEGER NOT NULL,
	"is_lucid"	BOOLEAN,
	"method"	VARCHAR(20),
	"stability_score"	INTEGER,
	"vividness"	INTEGER,
	"trigger_type"	VARCHAR(50),
	"duration_estimate"	INTEGER,
	"created_at"	DATETIME,
	PRIMARY KEY("id"),
	FOREIGN KEY("sleep_cycle_id") REFERENCES "sleep_cycles"("id")
);
CREATE TABLE IF NOT EXISTS "dreams" (
	"id"	INTEGER NOT NULL,
	"user_id"	INTEGER NOT NULL,
	"title"	VARCHAR(255) NOT NULL,
	"date"	DATE NOT NULL,
	"notes"	TEXT,
	"created_at"	DATETIME,
	PRIMARY KEY("id"),
	FOREIGN KEY("user_id") REFERENCES "users"("id")
);
CREATE TABLE IF NOT EXISTS "event_logs" (
	"id"	INTEGER NOT NULL,
	"sleep_cycle_id"	INTEGER NOT NULL,
	"event_type"	VARCHAR(50) NOT NULL,
	"subtype"	VARCHAR(50),
	"timestamp_order"	INTEGER,
	"notes"	TEXT,
	"created_at"	DATETIME,
	PRIMARY KEY("id"),
	FOREIGN KEY("sleep_cycle_id") REFERENCES "sleep_cycles"("id")
);
CREATE TABLE IF NOT EXISTS "exercises" (
	"id"	INTEGER NOT NULL,
	"user_id"	INTEGER NOT NULL,
	"type"	VARCHAR(50) NOT NULL,
	"status"	VARCHAR(20),
	"result_data"	TEXT,
	"assigned_at"	DATETIME,
	"completed_at"	DATETIME,
	"module_slug"	VARCHAR(50),
	PRIMARY KEY("id"),
	FOREIGN KEY("user_id") REFERENCES "users"("id")
);
CREATE TABLE IF NOT EXISTS "lookup_categories" (
	"id"	INTEGER NOT NULL,
	"slug"	VARCHAR(50) NOT NULL,
	"system"	BOOLEAN,
	PRIMARY KEY("id"),
	UNIQUE("slug")
);
CREATE TABLE IF NOT EXISTS "lookup_values" (
	"id"	INTEGER NOT NULL,
	"category_id"	INTEGER NOT NULL,
	"value"	VARCHAR(50) NOT NULL,
	"label_en"	VARCHAR(100) NOT NULL,
	"label_sl"	VARCHAR(100) NOT NULL,
	"sort_order"	INTEGER,
	"active"	BOOLEAN,
	"created_at"	DATETIME,
	CONSTRAINT "uq_lookup_cat_value" UNIQUE("category_id","value"),
	PRIMARY KEY("id"),
	FOREIGN KEY("category_id") REFERENCES "lookup_categories"("id")
);
CREATE TABLE IF NOT EXISTS "sleep_cycles" (
	"id"	INTEGER NOT NULL,
	"dream_id"	INTEGER NOT NULL,
	"time"	VARCHAR(10),
	"contents"	TEXT,
	"comments"	TEXT,
	"created_at"	DATETIME,
	PRIMARY KEY("id"),
	FOREIGN KEY("dream_id") REFERENCES "dreams"("id")
);
CREATE TABLE IF NOT EXISTS "user_profiles" (
	"id"	INTEGER NOT NULL,
	"user_id"	INTEGER NOT NULL,
	"timezone"	VARCHAR(50),
	"experience_level"	VARCHAR(20),
	"monthly_goal"	INTEGER,
	"practice_frequency"	VARCHAR(20),
	"onboarding_complete"	BOOLEAN,
	"onboarding_step"	INTEGER,
	"bio"	TEXT,
	"created_at"	DATETIME,
	"updated_at"	DATETIME,
	"plan"	VARCHAR(20),
	"trial_started_at"	DATETIME,
	"trial_used"	BOOLEAN,
	"stripe_customer_id"	VARCHAR(100),
	"stripe_subscription_id"	VARCHAR(100),
	"plan_expires_at"	DATETIME,
	PRIMARY KEY("id"),
	UNIQUE("user_id"),
	FOREIGN KEY("user_id") REFERENCES "users"("id")
);
CREATE TABLE IF NOT EXISTS "user_progress" (
	"id"	INTEGER NOT NULL,
	"user_id"	INTEGER NOT NULL,
	"module"	VARCHAR(50) NOT NULL,
	"lesson"	VARCHAR(50) NOT NULL,
	"completed"	BOOLEAN,
	"score"	INTEGER,
	"completed_at"	DATETIME,
	PRIMARY KEY("id"),
	CONSTRAINT "uq_user_module_lesson" UNIQUE("user_id","module","lesson"),
	FOREIGN KEY("user_id") REFERENCES "users"("id")
);
CREATE TABLE IF NOT EXISTS "users" (
	"id"	INTEGER NOT NULL,
	"email"	VARCHAR(255) NOT NULL,
	"username"	VARCHAR(100) NOT NULL,
	"password_hash"	VARCHAR(255) NOT NULL,
	"created_at"	DATETIME,
	PRIMARY KEY("id")
);
CREATE UNIQUE INDEX IF NOT EXISTS "ix_users_email" ON "users" (
	"email"
);
COMMIT;
