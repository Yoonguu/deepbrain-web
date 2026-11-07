"""최초 부서장 생성: python -m backend.bootstrap"""
import getpass, secrets
from .store import connect,password
if __name__=='__main__':
 email=input('부서장 이메일: ').strip().lower(); name=input('이름: ').strip(); department=input('부서: ').strip()
 pw=getpass.getpass('비밀번호 (12자 이상): ')
 if len(pw)<12 or not all((email,name,department)): raise SystemExit('입력을 확인하세요.')
 with connect() as c:
  existing=c.execute('SELECT id,role,approved FROM users WHERE email=?',(email,)).fetchone()
  if existing:
   if existing['role']!='doctor' or existing['approved']:
    raise SystemExit('이미 활성화된 계정입니다. 다른 이메일을 사용하세요.')
   c.execute('UPDATE users SET name=?,department=?,role=?,approved=1,password=? WHERE id=?',(name,department,'head',password(pw),existing['id']))
   c.execute('DELETE FROM sessions WHERE user_id=?',(existing['id'],))
  else:
   c.execute('INSERT INTO users VALUES(?,?,?,?,?,?,?)',(secrets.token_hex(16),email,name,department,'head',1,password(pw)))
 print('부서장 계정이 생성되었습니다.')
