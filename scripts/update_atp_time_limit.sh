#!/bin/bash
set -e

source /edx/app/edxapp/edxapp_env
cd /edx/app/edxapp/edx-platform

echo "Backup Proxy configuration"
sudo cp -p /edx/app/edxapp/edx-platform/cms/wsgi.py /tmp/wsgi_cms.py.save
sudo cp -p /edx/app/edxapp/edx-platform/lms/wsgi.py /tmp/wsgi_lms.py.save

echo "Install new dependencies"
sudo -E -H -u edxapp env "PATH=$PATH" pip install django-import-export==2.3.0
sudo -E -H -u edxapp env "PATH=$PATH" pip install openedx-scorm-xblock==10.0.1

echo "Pull last version"
sudo -E -H -u edxapp env "PATH=$PATH" git stash
sudo -E -H -u edxapp env "PATH=$PATH" git checkout atp_juniper
sudo -E -H -u edxapp env "PATH=$PATH" git pull origin atp_juniper

echo "Run migrations for time_limit"
sudo -E -H -u edxapp env "PATH=$PATH" /edx/bin/python.edxapp ./manage.py lms --settings=production makemigrations course_overviews
sudo -E -H -u edxapp env "PATH=$PATH" /edx/bin/python.edxapp ./manage.py lms --settings=production migrate course_overviews

echo "Restore Proxy configuration"
sudo cp -p /tmp/wsgi_cms.py.save /edx/app/edxapp/edx-platform/cms/wsgi.py
sudo cp -p /tmp/wsgi_lms.py.save /edx/app/edxapp/edx-platform/lms/wsgi.py

echo "Compile translations"
sudo -E -H -u edxapp env "PATH=$PATH" /edx/app/edxapp/venvs/edxapp/bin/paver i18n_fastgenerate

echo "Paver update"
sudo -E -H -u edxapp env "PATH=$PATH" /edx/app/edxapp/venvs/edxapp/bin/paver update_assets --settings=production

echo "## Restart ##"
sudo /edx/bin/supervisorctl restart all
