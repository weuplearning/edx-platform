define(['domReady', 'jquery', 'underscore','jquery.ui','tinymce','jquery.tinymce'],
    function(domReady, $, _) {
      var onReady = function() {
        /* definition des urls de call */
        var url = window.location.pathname;
        url = url.replace('manage','details');
        /* call ajax en get d'initialisation */
        /* get de depart */
        /* classe data de donnée reçu et envoyé sur le cours */
        class createCLass {
          /* set data with obj key entries */
          constructor(display_name,number,org,run,source_course_key,start_date,end_date,course_key){
            this.display_name = display_name;
            this.number = number;
            this.org = org;
            this.run = run;
            this.source_course_key = source_course_key;
            this.course_key = course_key;
          }

          /* update run & number */
          update_run_number_display_name_ids_orgs(id) {
            var This = $('#'+id);
            var val = This.val();
            val = val.replace(/\s/g,'');
            if(val.length != 0) {
              var split = val.split(',');
              this.number = split[0];
              this.run = split[1];
              this.source_course_key = This.data('course_key');
              this.org = This.data('org');
              this.display_name = This.data('display_name').replace('AMUNDI-GENERIC-TEMPLATE - ','');
            }
          }
        }

        /* initialisation de data */
        var create_data = new createCLass();

        /* action au click create */
        $('#create').click(function(){
          /* hydrate data */
          create_data.update_run_number_display_name_ids_orgs('course_identity');
          $.ajax({
            url:'/course/',
            type:'POST',
            dataType:'json',
            contentType: "application/json; charset=utf-8",
            data: JSON.stringify(create_data),
            success: function(retour) {
              create_data.course_key = retour.destination_course_key;
              var manage_url = '/settings/manage/'+create_data.course_key;
              window.open(manage_url,'_self');
            }
          })
        })
      };
      domReady(onReady);

      return {
          onReady: onReady
      };
    })
