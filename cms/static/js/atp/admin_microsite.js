define(['domReady', 'jquery', 'underscore','jquery.ui','tinymce','jquery.tinymce'],function(domReady, $, _) {
  class update_microsite {
    constructor(data) {
      this.data = data;
    }
    get_value(id,Class) {
      var This = $('#'+id);
      var data = new FormData($('#'+id).get(0));
      var That = $('.'+Class);
      $('.'+Class).each(function(){
        var val = $(this).attr('value');
        var name = $(this).attr('name');
        data.append(name,val);
      })
      this.data = data;
      return this.data;
    }
    save_action(update,cancel) {
      $('#new-microsite-logo,.'+update).on('change paste keyup',function(){
        $('#notification-warning').addClass('is-shown');
      })
      $('.'+cancel).click(function(){
        $('#notification-warning').removeClass('is-shown');
      })
    }
    success_ajax() {
      $('#notification-warning').removeClass('is-shown');
      var div = '<div class="wrapper wrapper-alert wrapper-alert-confirmation" id="alert-confirmation" aria-hidden="false" aria-labelledby="alert-confirmation-title" tabindex="-1"><div class="alert confirmation "><span class="feedback-symbol fa fa-check" aria-hidden="true"></span><div class="copy"><h2 class="title title-3" id="alert-confirmation-title">Your changes have been saved.</h2></div></div></div>';
      $('#page-alert').html(div);
      $.when($("html, body").animate({ scrollTop: 0 }, "slow")).done(function(){
        $('#page-alert').find('#alert-confirmation').slideDown(1000).delay(4000).slideUp(1000);
      })
    }
  }
  function delete_admin() {
    $('.microsite_admin_del').click(function(){
      var This = $(this);
      var data = This.data('user_id');
      var key = This.data('key');
      var url = '/add_microsite_admin'+'/'+key+'/';
      $.ajax({
        url:url,
        type:'DELETE',
        data:{
          data:data,
        },
        dataType:'json',
        success: function(retour) {
          var data = retour.context;
          if(data) {
            if(data.methods == 'DELETE') {
              if(data.delete) {
                This.parent().remove();
              }
              if($('.microsite_admin_del').length == 0) {
                $('#NoRegistred').removeClass('hide_message');
              }
            }
          }
        }
      });
    });
  }
  var onReady = function() {
    var updateMicrosite = new update_microsite();
    updateMicrosite.save_action('form_update','action-cancel');
    delete_admin();
    $('.action-save').click(function(){
      var This = $(this);
      var data = $('#micro_admin_email').val();
      var key = $('#micro_admin_email').data('key');
      var url = '/add_microsite_admin'+'/'+key+'/';
      $.ajax({
        url:url,
        type:'POST',
        data:{
          data:data,
        },
        dataType:'json',
        success: function(retour) {
          updateMicrosite.success_ajax();
          var data = retour.context;
          if(data) {
            var check = data.microsite_admin;
            if(check) {
              if($('.microsite_admin_del').length == 0) {
                $('#NoRegistred').addClass('hide_message');
              }
              var email = data.user_email;
              var user_id = data.user_id;
              var insert = $('#admin_management');
              var template = '<div><span>'+email+'</span><button data-type="DELETE" data-key="'+key+'" data-user_id="'+user_id+'" class="microsite_admin_del">Delete</button></div>';
              insert.append(template);
              $('#micro_admin_email').attr('value','');
              delete_admin();
            }
          }
        }
      })
    })
  };
  domReady(onReady);
  return {
      onReady: onReady
  };
})
