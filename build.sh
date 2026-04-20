#!/usr/bin/env bash
# exit on error
set -o errexit

# 1. Install dependencies
pip install -r requirements.txt

# 2. Collect Static Files (for Whitenoise)
python manage.py collectstatic --no-input

# 3. Run Migrations
python manage.py migrate

# 4. Run your 17 Tests
# If tests fail, Render will stop the deployment automatically.
python manage.py test