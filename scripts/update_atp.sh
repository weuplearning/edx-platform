#!/bin/bash

source /edx/app/edxapp/edxapp_env
cd /edx/app/edxapp/edx-platform

echo "Backup Proxy configuration"
sudo cp -p /edx/app/edxapp/edx-platform/cms/wsgi.py /tmp/wsgi_cms.py.save
sudo cp -p /edx/app/edxapp/edx-platform/lms/wsgi.py /tmp/wsgi_lms.py.save

echo "Install new dependencies"
sudo -E -H -u edxapp env "PATH=$PATH" pip install django-import-export==2.3.0

echo "Pull last version"
sudo -E -H -u edxapp env "PATH=$PATH" git stash
sudo -E -H -u edxapp env "PATH=$PATH" git checkout atp_juniper
sudo -E -H -u edxapp env "PATH=$PATH" git pull origin atp_juniper

echo "Backup Proxy configuration"
sudo cp -p /tmp/wsgi_cms.py.save /edx/app/edxapp/edx-platform/cms/wsgi.py
sudo cp -p /tmp/wsgi_lms.py.save /edx/app/edxapp/edx-platform/lms/wsgi.py

echo "Compile translations"
sudo -E -H -u edxapp env "PATH=$PATH" /edx/app/edxapp/venvs/edxapp/bin/paver i18n_fastgenerate

echo "Paver update"
sudo -E -H -u edxapp env "PATH=$PATH" /edx/app/edxapp/venvs/edxapp/bin/paver update_assets --settings=production

echo "## Restart ##"
sudo /edx/bin/supervisorctl restart lms: cms: edxapp_worker:

