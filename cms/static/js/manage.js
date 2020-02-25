define(['domReady', 'jquery', 'underscore','jquery.ui','tinymce','jquery.tinymce'],
    function(domReady, $, _) {
      var onReady = function() {
        /* definition des urls de call */
        var path = window.location.pathname;
        url = path.replace('manage','details');
        /* call ajax en get d'initialisation */
        var get = $.ajax({
          url:url,
          type:'GET',
          dataType:'json',
          success:function(retour) {

          }
        });
        var grade = $.ajax({
          url:path.replace('manage','grading'),
          type:'GET',
          dataType:'json',
          success: function(retour) {
          }
        });
        var advanced = $.ajax({
          url:path.replace('manage','advanced'),
          type:'GET',
          dataType:'json',
          success: function(retour) {

          }
        });
        /* get de depart */
        /* classe data de donnée reçu et envoyé sur le cours */
        class manageCLass {
          constructor(current_grade) {
            this.current_grade = current_grade;
          }
          /* set data with obj key entries */
          hydrate(data) {
            var keys = Object.keys(data);
            for(var i=0; i<keys.length;i++) {
              this[keys[i]] = data[keys[i]];
            }
            return this;
          }
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
            if(time == 'T:00Z') {
	        time = 'T00:00:00Z'
            }
            date = date+time;
            if(date.indexOf('undefined') == -1) {
              this[status] = date;
            }
          }
          /* update input course_id */
          update_course_id(id_1,id_2,course_id,run) {
            var This1 = $('#'+id_1);
            var This2 = $('#'+id_2);
            //var val = course_id+','+run;
            This1.attr('value',course_id);
            This2.attr('value',run);
          }
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
                  }
              }
            });
          }
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
          }
          /* action return ajax call is successful */
          success_ajax() {
            $('#notification-warning').removeClass('is-shown');
            var div = '<div class="wrapper wrapper-alert wrapper-alert-confirmation" id="alert-confirmation" aria-hidden="false" aria-labelledby="alert-confirmation-title" tabindex="-1"><div class="alert confirmation "><span class="feedback-symbol fa fa-check" aria-hidden="true"></span><div class="copy"><h2 class="title title-3" id="alert-confirmation-title">Your changes have been saved.</h2></div></div></div>';
            $('#page-alert').html(div);
            $.when($("html, body").animate({ scrollTop: 0 }, "slow")).done(function(){
              $('#page-alert').find('#alert-confirmation').slideDown(1000).delay(4000).slideUp(1000);
            })
          }
        }
        /* advanced class */
        class advancedClass {
          /* set data with obj key entries */
          hydrate(data) {
            var keys = Object.keys(data);
            for(var i=0; i<keys.length;i++) {
              this[keys[i]] = data[keys[i]];
            }
            return this;
          }
          update_current_acvanced(Class) {
            var q = false;
            $('.'+Class).each(function(){
              var This = $(this);
              if(This.is(':checked')) {
                if(This.val() == 'mandatory') {
                  q = true;
                }
              }
            })
            this.is_required_atp.value = q;
          }
        }
        /* grading class */
        class gradingClass {
          /* set data with obj key entries */
          hydrate(data) {
            var keys = Object.keys(data);
            for(var i=0; i<keys.length;i++) {
              this[keys[i]] = data[keys[i]];
            }
            return this;
          }
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
                }
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
                }
                $('#fail_grade').find('span').text(current_grade);
                $('#passed_grade').find('span').text(current_grade);
              }
            });
          }
          /* update grading value */
          update_current_grade(id_content) {
            this.grade_cutoffs.Pass = parseInt(parseFloat($('#'+id_content).attr('data-grade')) * 100) / 100;
          }
        }
        /* initialisation de data */
        var data = new manageCLass();
        var grade_data = new gradingClass();
        var advanced_data = new advancedClass();
        /* action au retour du get d'initialisation */
        $.when(get,grade, advanced).done(function(results1,results2,result3) {
          // resizable
          grade_data.addResizable('resizable','content_resize');
          /* hydrate object */
          data.hydrate(results1[0]);
          grade_data.hydrate(results2[0]);
          advanced_data.hydrate(result3[0]);
          /* all date & time pickers */
          data.datePicker("course-start-date");
          data.datePicker("course-end-date");
          data.timePicker('course-start-time');
          data.timePicker('course-end-time');
          /* init forms values */
          data.init_date('course-start-date');
          data.init_date('course-end-date');
          data.update_course_id('course_identity','course_session_top',data.course_id,data.run);
          /* action on campaign click */
          $('.campaign_type_check').click(function(){
            $('#notification-warning').addClass('is-shown');
          })
          /* action au click save */
          $('.action-save').click(function(){
            data.update_date("course-start-date");
            data.update_date("course-end-date");
            grade_data.update_current_grade('content_resize');
            advanced_data.update_current_acvanced('campaign_type_check');
            $.ajax({
              url:url,
              type: 'POST',
              contentType: "application/json; charset=utf-8",
              data : JSON.stringify(data),
              dataType:'json',
              success: function(retour) {
                $.ajax({
                  url:path.replace('manage','advanced'),
                  type:'POST',
                  contentType: "application/json; charset=utf-8",
                  data: JSON.stringify(advanced_data),
                  dataType:'json',
                  success: function(retour) {
                    $.ajax({
                      url:path.replace('manage','grading'),
                      type:'POST',
                      contentType: "application/json; charset=utf-8",
                      data : JSON.stringify(grade_data),
                      dataType:'json',
                      success: function(retour) {
                        data.success_ajax();
                      }
                    });
                  }
                })
              }
            })
          })
          $('.action-cancel').click(function(){
            $('#notification-warning').removeClass('is-shown');
          })
        })

      };
      domReady(onReady);

      return {
          onReady: onReady
      };
    })
