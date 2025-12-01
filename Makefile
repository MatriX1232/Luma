all: 
	docker compose up --build

down:
	docker compose down

fclean:
	docker compose down --rmi all -v --remove-orphans

re: fclean all

.PHONY: all down fclean re