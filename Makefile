all: 
	sudo docker compose build

start:
	sudo docker compose run --rm \
	-e WAYLAND_DISPLAY=$${WAYLAND_DISPLAY:-wayland-0} \
	-e XDG_RUNTIME_DIR=/run/user/$$(id -u) \
	-v /run/user/$$(id -u):/run/user/$$(id -u) \
	-e DISPLAY=$${DISPLAY:-:0} \
	-v /tmp/.X11-unix:/tmp/.X11-unix \
	luma

down:
	sudo docker compose down

fclean:
	sudo docker compose down --rmi all -v --remove-orphans

re: fclean all

.PHONY: all down fclean re