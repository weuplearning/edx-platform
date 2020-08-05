#!/bin/bash

source /edx/app/edxapp/edxapp_env
cd /edx/app/edxapp/edx-platform

sudo -E -H -u edxapp env "PATH=$PATH" git stash
sudo -E -H -u edxapp env "PATH=$PATH" git checkout atp_juniper
sudo -E -H -u edxapp env "PATH=$PATH" git pull origin atp_juniper

echo "Compile translations"
sudo -E -H -u edxapp env "PATH=$PATH" /edx/app/edxapp/venvs/edxapp/bin/paver i18n_fastgenerate

echo "Paver update"
sudo -E -H -u edxapp env "PATH=$PATH" /edx/app/edxapp/venvs/edxapp/bin/paver update_assets --settings=production

echo "## Restart ##"
sudo /edx/bin/supervisorctl restart lms: cms: edxapp_worker:

