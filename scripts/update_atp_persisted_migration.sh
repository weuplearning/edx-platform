 1 #!/bin/bash
 2 set -e
 3
 4 source /edx/app/edxapp/edxapp_env
 5 cd /edx/app/edxapp/edx-platform
 6
 7 echo "Backup Proxy configuration"
 8 sudo cp -p /edx/app/edxapp/edx-platform/cms/wsgi.py /tmp/wsgi_cms.py.save
 9 sudo cp -p /edx/app/edxapp/edx-platform/lms/wsgi.py /tmp/wsgi_lms.py.save
10
11 echo "Install new dependencies"
12 sudo -E -H -u edxapp env "PATH=$PATH" pip install django-import-export==2.3.0
13 sudo -E -H -u edxapp env "PATH=$PATH" pip install openedx-scorm-xblock==10.0.1
14
15 echo "Pull last version"
16 sudo -E -H -u edxapp env "PATH=$PATH" git stash
17 sudo -E -H -u edxapp env "PATH=$PATH" git checkout atp_juniper
18 sudo -E -H -u edxapp env "PATH=$PATH" git pull origin atp_juniper
19
20 echo "Run migrations for persisted_grades"
21 sudo -E -H -u edxapp env "PATH=$PATH" /edx/bin/python.edxapp ./manage.py lms --settings=production makemigrations persisted_grades
22 sudo -E -H -u edxapp env "PATH=$PATH" /edx/bin/python.edxapp ./manage.py lms --settings=production migrate persisted_grades
23
24 echo "Restore Proxy configuration"
25 sudo cp -p /tmp/wsgi_cms.py.save /edx/app/edxapp/edx-platform/cms/wsgi.py
26 sudo cp -p /tmp/wsgi_lms.py.save /edx/app/edxapp/edx-platform/lms/wsgi.py
27
28 echo "Compile translations"
29 sudo -E -H -u edxapp env "PATH=$PATH" /edx/app/edxapp/venvs/edxapp/bin/paver i18n_fastgenerate
30
31 echo "Paver update"
32 sudo -E -H -u edxapp env "PATH=$PATH" /edx/app/edxapp/venvs/edxapp/bin/paver update_assets --settings=production
33
34 echo "## Restart ##"
35 sudo /edx/bin/supervisorctl restart all
36
