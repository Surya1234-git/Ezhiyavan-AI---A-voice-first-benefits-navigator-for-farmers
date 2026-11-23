.PHONY: demo demo-docker demo-backend seed test frontend
demo:            ## backend + seeded demo farmer + frontend + browser, no Docker needed
	./scripts/demo.sh
demo-docker:     ## the same demo stack in Docker -> http://localhost:5173
	docker compose up --build
demo-backend:    ## backend only, in DEMO mode (for the real-backend browser journeys)
	cd backend && ENV=dev ALLOW_UNVERIFIED=1 SECRET_KEY=$$(python3 -c "import secrets;print(secrets.token_urlsafe(48))") python3 -m uvicorn app.main:app --reload --port 8000
seed:            ## with the backend running in demo mode: create the demo farmer
	python3 backend/scripts/seed_demo.py
test:            ## every check that can run here; says plainly what was skipped and why
	./scripts/test_all.sh
frontend:
	cd frontend && npm install && npm run dev
