@echo off

if "%1" == "test" goto :test

:test
echo testing ...
set TEST_MODULE=Test.Test
python -m coverage run -m unittest %TEST_MODULE%
python -m coverage report -m > coverage.report