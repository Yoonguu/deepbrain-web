"""Create isolated public prototype accounts: python -m backend.demo_accounts."""
import secrets
from .store import connect, password

ACCOUNTS = (
    ('demo-admin@medical-web.example', '공개 데모 관리자', 'head', 'DemoAdmin!2026#MRI'),
    ('demo-doctor@medical-web.example', '공개 데모 의사', 'doctor', 'DemoDoctor!2026#MRI'),
)

if __name__ == '__main__':
    with connect() as c:
        for email, name, role, secret in ACCOUNTS:
            existing = c.execute('SELECT id,department FROM users WHERE email=?', (email,)).fetchone()
            if existing and existing['department'] != '공개 데모':
                raise SystemExit(f'다른 부서에서 사용 중인 이메일: {email}')
            if existing:
                c.execute('UPDATE users SET name=?,role=?,approved=1,password=? WHERE id=?',
                          (name, role, password(secret), existing['id']))
                c.execute('DELETE FROM sessions WHERE user_id=?', (existing['id'],))
            else:
                c.execute('INSERT INTO users VALUES(?,?,?,?,?,?,?)',
                          (secrets.token_hex(16), email, name, '공개 데모', role, 1, password(secret)))
    print('공개 데모 계정 2개를 준비했습니다.')
