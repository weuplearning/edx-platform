define(['domReady', 'jquery', 'underscore','jquery.ui','tinymce','jquery.tinymce'],
    function(domReady, $, _) {
      var onReady = function() {
        //popup footer
        $('#legal_notice,#close_legal').click(function(){
          $('#pop_up_legal_notice').toggle();
        })
      };
      domReady(onReady);

      return {
          onReady: onReady
      };
    })

