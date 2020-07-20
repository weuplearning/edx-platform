import os
import shutil


from django.http import HttpResponseForbidden

def copydirectorykut(src, dst):
    os.chdir(dst)
    list=os.listdir(src)
    nom= src+'.css'
    fitx= open(nom, 'w')

    for item in list:
        fitx.write("%s\n" % item)

    fitx.close()

    f = open(nom,'r')
    for line in f.readlines():
        if "." in line:
            shutil.copy(src+'/'+line[:-1],dst+'/'+line[:-1])
        else:
            if not os.path.exists(dst+'/'+line[:-1]):
                os.makedirs(dst+'/'+line[:-1])
                copydirectorykut(src+'/'+line[:-1],dst+'/'+line[:-1])
            copydirectorykut(src+'/'+line[:-1],dst+'/'+line[:-1])
    f.close()
    os.remove(nom)
    os.chdir('..')

#decorator microsite access
def microsite_staff(func):

    def wrapper(*args):  # pylint: disable=missing-docstring
        request = args[1]
        microsite_id = args[2]
        microsite = Microsite.objects.get(pk=microsite_id)
        user = request.user

        _valid_user = False

        _admin_users = [
            "aurelien.croq@themoocagency.com",
            "geoffrey.marche@themoocagency.com",
            "lucie.ory@themoocagency.com",
            "daivis.hubbel@themoocagency.com"

        ]

        if request.user.email in _admin_users:
            _valid_user = True
        else:
            try:
                MicrositeAdminManager.objects.get(user=user,microsite=microsite)
                _valid_user = True
            except:
                pass

        if _valid_user:
            return func(*args)
        else:
            return HttpResponseForbidden()
    return wrapper
