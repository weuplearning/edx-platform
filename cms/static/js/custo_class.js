define(['domReady', 'jquery', 'underscore','jquery.ui','tinymce','jquery.tinymce'],
    function($) {
      'use strict';
      /* class elements du dom */
      /* class modèle */
      class base_class {
        // definir attributs
        hydrate(data) {
          var keys = Object.keys(data);
          for(var i=0; i<keys.length;i++) {
            this[keys[i]] = data[keys[i]];
          };
          return this;
        };
      };
      /* settings */
      class details_settings extends base_class {
        /* set all input values */
        init_date(id) {
          var This = $('#'+id);
          var status = id.replace('course-','').replace('-','_');
          var time_id = id.replace('date','time');
          time_id = $('#'+time_id);
          var datetime = this[status];
          if(typeof datetime != 'undefined' && datetime != null) {
            datetime = datetime.replace('Z').split('T');
            var date = datetime[0].split('-');
            var time = datetime[1].replace(':00','').replace('undefined','');
            date = date[1]+'/'+date[2]+'/'+date[0];
            This.attr('value',date);
            time_id.attr('value',time);
          }
        }
        /* update date */
        update_date(id) {
          var This = id;
          var status = id.replace('course-','').replace('-','_');
          var time_id = id.replace('date','time');
          var date = $('#'+id).val().split('/');
          date = date[2]+'-'+date[0]+'-'+date[1];
          var time = 'T'+$('#'+time_id).val()+':00Z';
          date = date+time;
          if(date.indexOf('undefined') == -1) {
            this[status] = date;
          };
        };
        /* update input course_id */
        update_course_id(id,course_id,run) {
          var This = $('#'+id);
          var val = course_id+','+run;
          This.attr('value',val);
        };
        /*  function datepicker */
         datePicker(dom) {
          var This = $("#"+dom);
          var key = This.data('key');
          This.datepicker({
            onClose: function(dateText,datePickerInstance) {
                var oldValue = $(this).data('oldValue') || "";
                if (dateText !== oldValue) {
                    $(this).data('oldValue',dateText);
                    $(this).trigger('dateupdated');
                    $('#notification-warning').addClass('is-shown');
                };
            }
          });
        };
        /*  function timepicker */
         timePicker(dom) {
          var This = $("#"+dom);
          var key = This.data('key');
          This.timepicker({
            timeFormat: "H:i"
          });
          This.on('changeTime', function() {
            $('#notification-warning').addClass('is-shown');
          });
        };
        /* action return ajax call is successful */
        success_ajax() {
          $('#notification-warning').removeClass('is-shown');
          var div = '<div class="wrapper wrapper-alert wrapper-alert-confirmation" id="alert-confirmation" aria-hidden="false" aria-labelledby="alert-confirmation-title" tabindex="-1"><div class="alert confirmation "><span class="feedback-symbol fa fa-check" aria-hidden="true"></span><div class="copy"><h2 class="title title-3" id="alert-confirmation-title">Your changes have been saved.</h2></div></div></div>';
          $('#page-alert').html(div);
          $.when($("html, body").animate({ scrollTop: 0 }, "slow")).done(function(){
            $('#page-alert').find('#alert-confirmation').slideDown(1000).delay(4000).slideUp(1000);
          });
        };
        /* tinymce init */
        init_tinymce(id) {
          tinymce.init({
            selector: id
          });
        };
      };
      /* advanced settings */
      class advanced_stettings extends base_class {
        /* update is required policie */
        update_current_advanced(Class) {
          var q = false;
          $('.'+Class).each(function(){
            var This = $(this);
            if(This.is(':checked')) {
              alert(This.val());
              if(This.val() == 'mandatory') {
                q = true;
              };
            };
          });
          this.is_required_atp.value = q;
        };
      };
      /* grade policie */
      class grade_settings extends base_class {
      /* set data with obj key entries */
      /* grade_change method */
      addResizable(id,id_content) {
        // resizable
        var start_grade = $('#'+id_content).data('grade');
        this.current_grade = parseFloat(start_grade);
        $( "#"+id ).css('width', parseFloat(start_grade) * 100+'%');
        $('#fail_grade').find('span').text(parseFloat(start_grade) * 100);
        $('#passed_grade').find('span').text(parseFloat(start_grade) * 100);
        $( "#"+id ).resizable({
          maxHeight: 50,
          maxWidth: $('#'+id_content).width(),
          minHeight: 50,
          minWidth: 0,
          resize: function( event, ui ) {
            if(ui.size.width <= 0) {
              ui.size.width = 0;
            };
            var current_grade = parseFloat((ui.size.width / $('#'+id_content).width()));
            var width_fail = $('#fail_grade').width();
            $( "#"+id_content ).attr('data-grade',current_grade);
            $('#notification-warning').addClass('is-shown');
            current_grade = parseInt(current_grade * 100);
            if(width_fail > ui.size.width) {
              $('#fail_grade').css('right','0');
              $('#fail_grade').css('left','-'+ui.size.width+'px');
            }else{
              $('#fail_grade').attr('style','');
            };
            $('#fail_grade').find('span').text(current_grade);
            $('#passed_grade').find('span').text(current_grade);
          }
        });
      };
      /* update grading value */
      update_current_grade(id_content) {
        this.grade_cutoffs.Pass = parseInt(parseFloat($('#'+id_content).attr('data-grade')) * 100) / 100;
      };
    };
  return {
      details_settings: details_settings,
      advanced_stettings: advanced_stettings,
      grade_settings: grade_settings
  };
})
