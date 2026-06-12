from app.tasks import celery_app

# Entrypoint for Celery execution
if __name__ == "__main__":
    celery_app.start()
