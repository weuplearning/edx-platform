define(['domReady', 'jquery', 'underscore','jquery.ui','tinymce','jquery.tinymce'],function(domReady, $, _) {
  function update_microsite() {
    this.constructor = function(data) {
      this.data = data;
    },
    this.get_value = function(idWhite, idCouleur,Class) {
      var data = new FormData();
      var logo = $('#'+idWhite).find('input')[0].files[0];
      data.append('logo',logo);
      var logo_couleur = $('#'+idCouleur).find('input')[0].files[0];
      data.append('logo_couleur',logo_couleur);

      var That = $('.'+Class);
      $('.'+Class).each(function(){
        var val = $(this).attr('value');
        var name = $(this).attr('name');
        data.append(name,val);
      })
      this.data = data;
      return this.data;
    },
    this.save_action = function(update,cancel) {
      $('#new-microsite-logo,.'+update).on('change paste keyup',function(){
        $('#notification-warning').addClass('is-shown');
      })
      $('.'+cancel).click(function(){
        $('#notification-warning').removeClass('is-shown');
      })
    },
    this.success_ajax = function() {
      $('#notification-warning').removeClass('is-shown');
      var div = '<div class="wrapper wrapper-alert wrapper-alert-confirmation" id="alert-confirmation" aria-hidden="false" aria-labelledby="alert-confirmation-title" tabindex="-1"><div class="alert confirmation "><span class="feedback-symbol fa fa-check" aria-hidden="true"></span><div class="copy"><h2 class="title title-3" id="alert-confirmation-title">Your changes have been saved.</h2></div></div></div>';
      $('#page-alert').html(div);
      $.when($("html, body").animate({ scrollTop: 0 }, "slow")).done(function(){
        $('#page-alert').find('#alert-confirmation').slideDown(1000).delay(4000).slideUp(1000);
      })
    }
  };
  var onReady = function() {
    var updateMicrosite = new update_microsite();
    updateMicrosite.save_action('form_update','action-cancel');
    $('.action-save').click(function(){
      var values = updateMicrosite.get_value('upload_microsite_logo','upload_microsite_logo_couleur','input_update');
      var path = window.location.path;
      $.ajax({
        url:path,
        type:'POST',
        data: values,
        cache: false,
        contentType: false,
        processData: false,
        dataType:'json',
        success: function(retour) {
          updateMicrosite.success_ajax();
          $('#micro_primary_color').attr('value','');
          $('#micro_secondary_color').attr('value','');
          var primary_color = retour.primary_color;
          $('#pre_primary').find('label').text(primary_color);
          $('#primary_color_preview').css('background-color',primary_color);
          var secondary_color = retour.secondary_color;
          $('#pre_secondary').find('label').text(secondary_color);
          $('#secondary_color_preview').css('background-color',secondary_color);
          if(retour.amundi_brand=="true"){
            var amundi_brand="La marque AmundiBrand est affichée";
          }
          else{
            var amundi_brand="La marque AmundiBrand est affichée";
          }
          $('#pre_amundibrand').find('label').text(amundi_brand);

          var trademark = retour.trademark;
          $('#pre_trademark').find('label').text(trademark);

          var src = $('#logo_preview').find('img').attr('src');
          base= src.split('/media/')[0];

          var logo_couleur_url = retour.logo_couleur;
          $('#logo_preview_couleur').find('img').attr('src',base+logo_couleur_url +"?"+ new Date().getTime());

          var logo_url = retour.logo;
          $('#logo_preview').find('img').attr('src',base+logo_url +"?"+ new Date().getTime());
        }
      })
    })
  };
  domReady(onReady);
  return {
      onReady: onReady
  };
})
