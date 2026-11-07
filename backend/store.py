import os, sqlite3, hashlib, secrets, time
from pathlib import Path
ROOT=Path(os.getenv('MEDICAL_DATA_DIR', str(Path(__file__).resolve().parent.parent/'data')))
ROOT.mkdir(parents=True,exist_ok=True)
DB=ROOT/'medical.sqlite3'
def connect():
 c=sqlite3.connect(DB,timeout=15); c.row_factory=sqlite3.Row; c.execute('PRAGMA foreign_keys=ON'); return c
def init():
 with connect() as c:
  c.executescript('''
CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY,email TEXT UNIQUE NOT NULL,name TEXT NOT NULL,department TEXT NOT NULL,role TEXT NOT NULL DEFAULT 'doctor',approved INTEGER NOT NULL DEFAULT 0,password TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,user_id TEXT REFERENCES users(id),csrf TEXT NOT NULL,expires REAL NOT NULL);
CREATE TABLE IF NOT EXISTS files(id TEXT PRIMARY KEY,department TEXT NOT NULL,name TEXT NOT NULL,kind TEXT NOT NULL,base_id TEXT,metadata TEXT NOT NULL,created REAL NOT NULL,deleted INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY,department TEXT NOT NULL,payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS reports(file_id TEXT PRIMARY KEY REFERENCES files(id),body TEXT NOT NULL,version INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS report_history(id INTEGER PRIMARY KEY,file_id TEXT,body TEXT,version INTEGER,author TEXT,created REAL);
CREATE TABLE IF NOT EXISTS notes(id INTEGER PRIMARY KEY,file_id TEXT REFERENCES files(id),author TEXT REFERENCES users(id),body TEXT NOT NULL,created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY,actor TEXT,action TEXT,object_id TEXT,created REAL);
''')
def recover_jobs():
 with connect() as c:
  c.execute("UPDATE jobs SET payload=json_set(payload,'$.status','failed','$.message','서버 재시작으로 중단','$.error','서버가 재시작되었습니다.') WHERE json_extract(payload,'$.status') IN ('queued','running')")
def digest(s): return hashlib.sha256(s.encode()).hexdigest()
def password(s,salt=None):
 salt=salt or secrets.token_hex(16)
 return salt+':'+hashlib.scrypt(s.encode(),salt=bytes.fromhex(salt),n=16384,r=8,p=1).hex()
def verify(s,h): return secrets.compare_digest(password(s,h.split(':')[0]),h)
def audit(user,action,obj):
 with connect() as c: c.execute('INSERT INTO audit(actor,action,object_id,created) VALUES(?,?,?,?)',(user,action,obj,time.time()))
init()
