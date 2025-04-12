py manage.py runserver
celery -A app worker --pool=solo -l info
celery -A app.celery beat -l info 
uvicorn app.asgi:application --host 127.0.0.1 --port 8005
cd FASTAPI
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
