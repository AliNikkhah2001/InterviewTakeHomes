run:
	python -m src.main --input data/messages.json --output sample_output.json
api:
	uvicorn src.main:app --reload --port 8000
test:
	pytest -q
