img:
	docker build -t freecrm:0.0.1 .

run:
	docker run -p 8001:8001 freecrm:0.0.1

