.PHONY: doc

test:
	tox
doc:
	make -C doc html
clean:
	rm -rf build dist aiogreen.egg-info .tox
	find -name "*.pyc" -delete
	find -name "__pycache__" -exec rm -rf {} \;
	make -C doc clean
