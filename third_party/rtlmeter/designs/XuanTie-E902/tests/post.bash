#!/bin/bash
set -x
set -e
# stdout must contain 'TEST PASSED'
grep -q "TEST PASSED" _execute/stdout.log
