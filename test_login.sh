#!/bin/bash
curl -i -c cookies.txt -X POST \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "username=admin&password=ChangeMe!123" \
     http://10.2.2.49:9000/auth/login
