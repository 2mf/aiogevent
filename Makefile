.PHONY: doc

test:
	tox
clean:
	rm -rf build dist aiogevent.egg-info .tox
	find -name "*.pyc" -delete
	find -name "__pycache__" -exec rm -rf {} \;
