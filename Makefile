all: 
	sudo docker compose build

start:
	sudo docker compose run --rm luma

down:
	sudo docker compose down

fclean:
	sudo docker compose down --rmi all -v --remove-orphans

re: fclean all

.PHONY: all down fclean re