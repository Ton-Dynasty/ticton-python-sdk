bump:
	poetry version patch
install:
	poetry self add poetry-bumpversion
    poetry self add poetry-plugin-export
	poetry install