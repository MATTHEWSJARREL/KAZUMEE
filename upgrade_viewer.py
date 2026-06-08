import sys
sys.path.insert(0, '.')

from backend.database.session import SessionLocal
from backend.database.models.user import User
from backend.database.models.viewer import Viewer

db = SessionLocal()

user = db.query(User).filter(User.email == 'viewerno2@gmail.com').first()
if user:
    print(f'Found user: {user.email}')
    viewer = db.query(Viewer).filter(Viewer.user_id == user.id).first()
    if viewer:
        viewer.subscription_tier = 'pro'
        db.commit()
        print('Viewer upgraded to pro')
    else:
        print('No viewer record found')
else:
    print('User not found')

db.close()