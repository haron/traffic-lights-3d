.PHONY: build test linter package clean

build:
	uv run traffic_light.py

test: build
	uv run check.py

linter:
	uvx ruff check .
	uvx ruff format --check .

package: test
	rm -f traffic_light_print.zip
	zip -j traffic_light_print.zip out/traffic_light.3mf out/*.stl PRINT.txt

clean:
	rm -rf out traffic_light_print.zip
