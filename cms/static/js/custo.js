define(['domReady', 'jquery', 'underscore'],
    function(domReady, $, _) {
      var onReady = function() {
    
      console.log("salut")
        /* action on card */
        $('.course-item').each(function(){
          var This = $(this);
          var data = This.data('status');
          if(data == 'template') {
            This.hide();
          }
        })
        /* action on click on the index menu */
        $('.sub_menu').find('button').click(function(){
          var This = $(this);
          var data = This.data('sub');
          $('.sub_menu').find('button').not(This).removeClass('active_button');
          This.addClass('active_button');
          $('.course-item').each(function(){
            var That = $(this);
            var that_data = That.data('status');
            if(that_data == data){
              That.show();
            }else{
              That.hide();
            }
            if(data != 'all') {
              $('.up_list_courses').hide();
            }else{
              $('.up_list_courses').show();
            }
          })
        });
        /* action on svgs */
        // Get the Object by ID
        $(".svg-class").each(function(){
          var This = $(this);
          This.contents().find('svg').attr("fill", "#dc9e29");
        })
        $('.svg-class-title').each(function(){
          var This = $(this);
          This.contents().find('svg').attr("fill", "#05144d");
        })
      };
      domReady(onReady);

      return {
          onReady: onReady
      };
    })
