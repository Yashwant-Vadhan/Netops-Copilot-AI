from app.db import session
from app.models import schema # Ensures all models are registered on Base.metadata

def init_db():
    schema.Base.metadata.create_all(bind=session.engine)

if __name__ == "__main__":
    init_db()
    print("Database tables initialized successfully.")
