define(["domReady", "jquery", "underscore"],
    function (domReady, $, _, CancelOnEscape, CreateMicrositeUtilsFactory) {
        "use strict";
        // microsite form
        var new_microsite_form = function(e) {
          e.preventDefault();
          $('.wrapper-create-element').removeClass('is-shown');
          $('.wrapper-create-microsite').addClass('is-shown');
        }
        var ajax_cancel_microsite = function(e) {
          $('.wrapper-create-microsite').removeClass('is-shown');
        }
        console.log('sdf sdf sdf sd fsd fsdgfqkj sdqsjkdf qksdjgh fkqsdjhgf qksdjghf qksdjhg fqsdj gfkqsjdhgf kqsdjgf qsdkjgfsdkqjf kqsdjgf qksdjgh qsdkjghf qsdjk qsdkjhgf qksdjhgqf sdkjhg ')
        var ajax_call_create_microsite = function(e) {
          console.log('creating microsite')
          e.preventDefault();
          var url = '/create-microsite/';
          var formData = new FormData();
          formData.append('display_name',$('#new-microsite-name').val());
          formData.append('logo',$('#new-microsite-logo').prop("files")[0]);
          formData.append('logo_couleur',$('#new-microsite-logo-couleur').prop("files")[0]);
          formData.append('primary_color',$('#new-microsite-primary_color').val());
          formData.append('secondary_color',$('#new-microsite-secondary_color').val());
          formData.append('contact_address',$('#new-microsite-contact').val());
          formData.append('language',$('#language-value').val());
          formData.append('amundi_brand',$('#amundi-brand').val());
          $.ajax({
            url:url,
            data:formData,
            cache: false,
            contentType: false,
            processData: false,
            type: 'POST',
            success: function(data) {
              $('.wrapper-create-microsite').removeClass('is-shown');
              location.reload();
            }
          })
        }
        // message aucune campagne
        var campaign_info = function(e) {
          $('#course-index-tabs').find('li').find('button').click(function(){
            $('.modules_items').removeClass('is_hide_atp').removeClass('is_show_atp');
            $('.campaign_items').removeClass('is_hide_atp').removeClass('is_show_atp');
            $('.action_search').removeClass('active_s_atp');
            $('#search_block').find("input").attr('value',"");
            $('.search_result').find('p').addClass('is_hidden_atp');
            $('.search_result').addClass('is_hide_atp');
            $('#search_block_campaign').find("input").attr('value',"");
            var This = $(this);
            var data = This.data('sub');
            if(data == 'all') {
              $('#no_course').show();
              $('.content-supplementary').css('border','1px solid #c8c8c8');
              $('#info_my_campaign').show();
              $('#info_my_module').hide();
              $('#module_search').removeClass('is_show_atp').addClass('is_hide_atp');
              $('#campaign_search').removeClass('is_hide_atp').addClass('is_show_atp');
              $('.libraries').removeClass("active");
            }else{
              $('#no_course').hide();
            }
            if(data == 'microsites') {
              $('.content-supplementary').css('border','1px solid transparent');
              $('#info_my_campaign').hide();
              $('#info_my_module').hide();
              $('#module_search').removeClass('is_show_atp').addClass('is_hide_atp');
              $('#campaign_search').removeClass('is_show_atp').addClass('is_hide_atp');
              $('.libraries').removeClass("active");
            }
            if(data == 'libraries-tab') {
              $('.content-supplementary').css('border','1px solid transparent');
              $('#info_my_campaign').hide();
              $('#info_my_module').hide();
              $('#module_search').removeClass('is_show_atp').addClass('is_hide_atp');
              $('.libraries').addClass("active");
            }
            if(data == 'template') {
              $('#generic_title').show();
              $('.content-supplementary').css('border','1px solid #c8c8c8');
              $('#info_my_campaign').hide();
              $('#info_my_module').show();
              $('#module_search').removeClass('is_hide_atp').addClass('is_show_atp');
              $('#campaign_search').removeClass('is_show_atp').addClass('is_hide_atp');
              $('.libraries').removeClass("active");
            }else{
              $('#generic_title').attr('style','');
            }
          })
        }
        // search
        var search_module = function(e) {
          // variable globales
          var categ_search = '';
          var input_s = '';
          // click picto loupe
          function do_search(cat,inp) {
            // si init
            var rows = 0;
            var no_result = true;
            if(cat == "" && input_s == "") {

              $('.modules_items').removeClass('is_hide_atp');
              no_result = false;
              rows = $('.modules_items').length;
            }else if(cat != "" && inp == "") {

              $('.modules_items').each(function(){
                var That = $(this);
                var that_data = That.data("search");
                if(that_data.indexOf("fundamental") != -1) {
                  that_data = that_data.replace("s","");
                }
                if(cat.indexOf(that_data) != -1) {
                  That.removeClass('is_hide_atp');
                  no_result = false;
                  rows = rows + 1;
                }else{
                  That.addClass('is_hide_atp');
                }
              });

            }else if(cat == "" && inp != "") {

              $('.modules_items').each(function(){
                var That = $(this);
                var that_data = That.find('.course-title').text().toLowerCase();
                if(that_data.indexOf(inp) != -1) {
                  That.removeClass('is_hide_atp');
                  no_result = false;
                  rows = rows + 1;
                }else{
                  That.addClass('is_hide_atp');
                }
              });

            }else if(cat != "" && inp != "") {

              $('.modules_items').each(function(){
                var That = $(this);
                var that_data = That.find('.course-title').text().toLowerCase();
                var data = That.data("search");
                if(data.indexOf("fundamental") != -1) {
                  data = data.replace("s","");
                }
                if(that_data.indexOf(inp) != -1 && cat.indexOf(data) != -1) {
                  That.removeClass('is_hide_atp');
                  no_result = false;
                  rows = rows + 1;
                }else{
                  That.addClass('is_hide_atp');
                }
              });

            }
            if(no_result) {
              $('.search_result').find('.p_1').removeClass('is_hidden_atp');
            }else{
              $('.search_result').find('.p_2').removeClass('is_hidden_atp');
              $('.search_result').find('.p_2').find('span').text(rows);
            }
          };
          $('#search_block').find('button').click(function(){
            $('.search_result').removeClass('is_hide_atp');
            $('.search_result').find('p').addClass('is_hidden_atp');
            input_s = $('#search_block').find('input').attr("value");
            do_search(categ_search,input_s);
          })
          // enter input
          // enter input
          $('#search_block').find('input').on('keydown', function(e) {
              if (e.which == 13) {
                  e.preventDefault();
                  input_s = $(this).attr("value");
                  $('.search_result').find('p').addClass('is_hidden_atp');
                  do_search(categ_search,input_s);
                  $('.search_result').removeClass('is_hide_atp');
              }
          });
          //click bouton categorie
          $('#category_block').find("button").click(function(){
            $('.search_result').removeClass('is_hide_atp');
            $('.search_result').find('p').addClass('is_hidden_atp');
            var This = $(this);
            var is_active = false;
            if(This.hasClass('active_s_atp')) {
              is_active = true;
            }
            //$('#category_block').find("button").removeClass('active_s_atp');
            if(!is_active) {
              This.addClass('active_s_atp');
              categ_search = categ_search+This.data("categ");
            }else{
              This.removeClass('active_s_atp');
              categ_search = categ_search.replace(This.data("categ"),"");
            }
            do_search(categ_search,input_s);
          })
          $('.search_result').find('button').click(function(){
            categ_search = '';
            input_s = '';
            $('.search_result').find('p').addClass('is_hidden_atp');
            $('.search_result').addClass('is_hide_atp');
            $('.active_s_atp').removeClass('active_s_atp');
            $('#search_block').find('input').attr('value',"");
            do_search(categ_search,input_s);
          })
        }
        // search campaign
        var search_campaign = function(e) {
          // variable globales
          var categ_search = '';
          var input_s = '';
          // click picto loupe
          function do_search(cat,inp) {
            // si init
            var rows = 0;
            var no_result = true;
            if(cat == "" && input_s == "") {

              $('.campaign_items').removeClass('is_hide_atp');
              no_result = false;
              rows = $('.campaign_items').length;
            }else if(cat != "" && inp == "") {

              $('.campaign_items').each(function(){
                var That = $(this);
                var that_data = That.data("search");
                if(that_data.indexOf("fundamental") != -1) {
                  that_data = that_data.replace("s","");
                }
                if(cat.indexOf(that_data) != -1) {
                  That.removeClass('is_hide_atp');
                  no_result = false;
                  rows = rows + 1;
                }else{
                  That.addClass('is_hide_atp');
                }
              });

            }else if(cat == "" && inp != "") {

              $('.campaign_items').each(function(){
                var That = $(this);
                var that_data = That.find('.course-title').text().toLowerCase();
                if(that_data.indexOf(inp) != -1) {
                  That.removeClass('is_hide_atp');
                  no_result = false;
                  rows = rows + 1;
                }else{
                  That.addClass('is_hide_atp');
                }
              });

            }else if(cat != "" && inp != "") {

              $('.campaign_items').each(function(){
                var That = $(this);
                var that_data = That.find('.course-title').text().toLowerCase();
                var data = That.data("search");
                if(data.indexOf("fundamental") != -1) {
                  data = data.replace("s","");
                }
                if(that_data.indexOf(inp) != -1 && cat.indexOf(data) != -1) {
                  That.removeClass('is_hide_atp');
                  no_result = false;
                  rows = rows + 1;
                }else{
                  That.addClass('is_hide_atp');
                }
              });

            }
            if(no_result) {
              $('.search_result').find('.p_1').removeClass('is_hidden_atp');
            }else{
              $('.search_result').find('.p_2').removeClass('is_hidden_atp');
              $('.search_result').find('.p_2').find('span').text(rows);
            }
          };
          $('#search_block_campaign').find('button').click(function(){
            input_s = $('#search_block_campaign').find('input').attr("value");
            $('.search_result').find('p').addClass('is_hidden_atp');
            do_search(categ_search,input_s);
            $('.search_result').removeClass('is_hide_atp');
          })
          // enter input
          $('#search_block_campaign').find('input').on('keydown', function(e) {
              if (e.which == 13) {
                  e.preventDefault();
                  input_s = $(this).attr("value");
                  $('.search_result').find('p').addClass('is_hidden_atp');
                  do_search(categ_search,input_s);
                  $('.search_result').removeClass('is_hide_atp');
              }
          });
          //click bouton categorie
          $('#category_block_campaign').find("button").click(function(){
            var This = $(this);
            var is_active = false;
            $('.search_result').find('p').addClass('is_hidden_atp');
            $('.search_result').removeClass('is_hide_atp');
            if(This.hasClass('active_s_atp')) {
              is_active = true;
            }
            //$('#category_block').find("button").removeClass('active_s_atp');
            if(!is_active) {
              This.addClass('active_s_atp');
              categ_search = categ_search+This.data("categ");
            }else{
              This.removeClass('active_s_atp');
              categ_search = categ_search.replace(This.data("categ"),"");
            }
            do_search(categ_search,input_s);
          })

          $('.search_result').find('button').click(function(){
            categ_search = '';
            input_s = '';
            $('.search_result').find('p').addClass('is_hidden_atp');
            $('.search_result').addClass('is_hide_atp');
            $('.active_s_atp').removeClass('active_s_atp');
            $('#search_block_campaign').find('input').attr('value',"");
            do_search(categ_search,input_s);
          })

        }
        // search message
        var new_search = function() {

        }
        // svg loading
        var svg_load = function(){
          jQuery('img.svg').each(function(){
              var $img = jQuery(this);
              var imgID = $img.attr('id');
              var imgClass = $img.attr('class');
              var imgURL = $img.attr('src');
              jQuery.get(imgURL, function(data) {
                  // Get the SVG tag, ignore the rest
                  var $svg = jQuery(data).find('svg');
                  // Add replaced image's ID to the new SVG
                  if(typeof imgID !== 'undefined') {
                      $svg = $svg.attr('id', imgID);
                  }
                  // Add replaced image's classes to the new SVG
                  if(typeof imgClass !== 'undefined') {
                      $svg = $svg.attr('class', imgClass+' replaced-svg');
                  }
                  // Remove any invalid XML tags as per http://validator.w3.org
                  $svg = $svg.removeAttr('xmlns:a');
                  // Replace image with new SVG
                  $img.replaceWith($svg);

              }, 'xml');
          });
          $('img.svg').show();
        }
        var onReady = function () {
            $('.new-microsite-button').bind('click',new_microsite_form);
            $('.new-microsite-save').bind('click',ajax_call_create_microsite);
            $('.new-microsite-cancel').bind('click',ajax_cancel_microsite);
            campaign_info();
            svg_load();
            search_module();
            search_campaign();


            // Redirection vers le module concerné après create my campaign back to modules
            function getParameterByName(name, url) {
                if (!url) url = window.location.href;
                name = name.replace(/[\[\]]/g, "\\$&");
                var regex = new RegExp("[?&]" + name + "(=([^&#]*)|&|#|$)"),
                    results = regex.exec(url);
                if (!results) return null;
                if (!results[2]) return '';
                return decodeURIComponent(results[2]);
            }
            var campaign_from =getParameterByName("campaign");
            var module_from =getParameterByName("module");
            if(campaign_from){
              document.getElementById(campaign_from).scrollIntoView();
            }
            if(module_from){
              $("#my-campaigns").removeClass("active_button");
              $("#my-modules").addClass("active_button");
              $(".up_list_courses").css('display','none');
              $("#generic_title").css("display","block");
              $(".campaign_items").css("display","none");
              $(".modules_items").css("display","list-item");
              $("#campaign_search").addClass('is_hide_atp').removeClass('is_show_atp');
              $("#module_search").removeClass('is_hide_atp').addClass('is_show_atp');
              $("#info_my_campaign").css("display","none");
              $("#info_my_module").css("display","inline");
              document.getElementById(module_from).scrollIntoView();
            }

            //$('#course-index-tabs .microsite-tab').bind('click', showTab('microsite'));
        };

        domReady(onReady);

        return {
            onReady: onReady
        };
    });
