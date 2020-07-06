/* DISPLAY ANSWERS ON QUIZ */

$(document).ajaxSuccess(function(event, xhr, settings){
  if( settings.url.endsWith('problem_check') ) {
    var url_check_pb=settings.url;
    var url_base_problem=url_check_pb.replace('/problem_check','')
    var url_show_pb=url_base_problem+'/problem_show';
    ajax_problem_show(url_show_pb);
    // translate correct incorrect
    if(course_language =='de'){
      setInterval(function(){
        var message_faux=$('.notification.error.notification-submit span.notification-message');
        var message_vrai=$('.notification.success.notification-submit span.notification-message');
        if(message_vrai.lenght>0){
          message_vrai.html(message_vrai.html().replace('Correct','Korrekt'));
        }
        if(message_faux.length>0){
          message_faux.html(message_faux.html().replace('Incorrect','Falsch'));
        }
      },300);
    }
  }
});
function ajax_problem_show(url_show_pb){
  $.ajax({
      url:url_show_pb,
      type:'POST',
      dataType:'json',
      success:function(data){
        //prepare answers
        answers=data['answers'];
         $.each(answers, function(key, value) {
           if ($.isArray(value)) {
             for (i = 0, len = value.length; i < len; i++) {
               $('#'+key+'-'+value[i]+'-label').addClass('choicegroup_correct');
             }
           }
           else{
            $('#'+key+'-'+value[i]+'-label').addClass('choicegroup_correct');
           }
         });
      }
    });
}


error_div='<div class="notification error notification-submit" tabindex="-1"><span class="icon fa fa-close" aria-hidden="true"></span><span class="notification-message">'+incorrect_wording+'</span><div class="notification-btn-wrapper"><button type="button" class="btn btn-default btn-small notification-btn review-btn sr">Review</button></div></div>';
success_div='<div class="notification success notification-submit " tabindex="-1"><span class="icon fa fa-check" aria-hidden="true"></span><span class="notification-message">'+correct_wording+'</span><div class="notification-btn-wrapper"><button type="button" class="btn btn-default btn-small notification-btn review-btn sr">Review</button></div></div>';

/* display answers on questions first attempt quiz */
$('.problems-wrapper').live('click', function(){
  if ($(this).hasClass('finished')){
    console.log('ok finished');
    if($(this).hasClass('fail_quiz_atp') && $(this).find('div.notification.error').length<=0){
      $(this).find('.action').before(error_div);
      //afficher réponse si faux
      url_show_pb=$(this).attr('data-url')+'/problem_show';
      ajax_problem_show(url_show_pb);
    }
    else if($(this).hasClass('success_quiz_atp') && $(this).find('div.notification.success').length<=0){
      $(this).find('.action').before(success_div);
    }
  }
})

/* SCROLL TO NEXT QUES IN QUIZ*/
problem_ids_list=[]
$( document ).ready(function() {
  $('.problems-wrapper').each(function() {
    problem_ids_list.push($(this).attr('id'));
  });

});
function scroll_to_ques(question_id){
    console.log($('#'+question_id))
    $(document).scrollTo($('#'+question_id).offset().top-80+'px',500);
    console.log($('#'+question_id).offset().top)
}
// on next click
$('.question_next').live("click",function () {
  next_id=$(this).parents('.vert').next('.vert').find('.problems-wrapper').attr('id');
  scroll_to_ques(next_id);
  console.log(next_id)
  $('#'+next_id).find('.hd.hd-2.problem-header').trigger( "click" );
});

$('.button-next').live("click",function () {
  console.log('next')
  next_id=$(this).parent().parent('.tma_tab').next().attr('id');
  console.log($(this))
  scroll_to_ques(next_id);
  console.log(next_id)
  $('#'+next_id).find('.hd.hd-2.problem-header').trigger( "click" );
});

// on question title click
$('.hd.hd-2.problem-header').live("click", function(){
  question_id="problem_"+$(this).attr('id').replace('-problem-title','');
  console.log('ques id on click h2'+question_id);
  scroll_to_ques(question_id);
  if($(this).parent().hasClass('finished','fail_quiz_atp')){
    url_show_pb=$(this).parent().attr('data-url')+'/problem_show';
    ajax_problem_show(url_show_pb);
  }
})

/* RESET QUIZ */
function get_all_questions(){
  problem_xblock_list=[];
  $('div.vert').each(function(){
   if($(this).attr('data-id').split('@')[1]=="problem+block"){
    problem_xblock_list.push($(this).attr('data-id'));
   }
  })
  return problem_xblock_list;
};

function reset_all_problems() {
  var i=0;
  problem_xblock_list=get_all_questions();
  console.log(user)
  problem_xblock_list.forEach(function(xblock_id) {
    i++;
    reset_problem(xblock_id,i,problem_xblock_list.length)
  })
};


/* RESULT PANEL GENERATION */
// Add a result panel title
var result_panel_title = '<a href="#holding-section-child" role="button" class="button-chapter chapter" id="holding-section-result" aria-controls="holding-section-child" aria-expanded="false"><span class="group-heading" aria-label="holding section"><span class="icon fa fa-caret-right" aria-hidden="true"></span>results_wording</span></a>';
$('.course-navigation').append(result_panel_title);
//Messages for finished modules
var picto_success = trophy_img;
var picto_failed = failed_img;
var template_and_title = '<div id="final_score"></div>';
var congrats = "<div id='congrats_score' class='primary-color-text'>"+congratulation_wording+" !</div>";
var picto = '<div id="score_picto"><img src="" class="svg"/></div>';
var first_par = ['<div id="score_first_para" class="primary-color-text">'+completed_wording+'<br>« '+course_default_name+' »</div>','<div id="score_first_para">'+started_wording+'<br>« '+course_default_name+' ».</div>'];
var second_par = ['<div id="second_par_score" class="primary-color-text">'+unfortunately_wording+'</div>','<div id="second_par_score">'+to_end_wording+'</div>'];
var score_div = '<div id="score_div_info"><span class="primary-color-text">'+score_wording+'</span><span id="insert_score"></span></div>';
var boutton_certificat = '<div id="score_button"><button class="primary-color-bg" onclick=\"followClickEvents(this,\'certificate\',\'download\')\">'+certificate_wording+'</button></div>';
// Messages for modules over
var message_termine='<div id="module-over" class="primary-color-text">'+training_over_wording+'</div>';
var reset_bouton='<div onclick="reset_all_problems()"><a id="reset_bouton" class="reset-btn primary-color-bg reset" >'+start_again_wording+'</a></div>';

function generate_certif() {
  var url_certif = '/api/atp/check/certificate/'+course_id+'/';
  $.ajax({
    url:url_certif,
    type:'GET',
    dataType:'json',
    success:function(data){
      window.open(data.certificate_url,'_self');
    }
  })
}

function is_course_over(){
  var end_date=new Date(course_end);
  var today = new Date();
  course_over=false;
  if (today>end_date){
    course_over=true;
  }
  return course_over;
}

function generate_result_success(score){
  $('#second_par_score').hide();
  $('#final_score').append(congrats);
  $('#insert_score').css('color','#dc9e29');
  $('#score_picto').find('img').attr('src',picto_success);
  $('#score_picto').find('img').attr('class','svg picto_add_success');
  $('#insert_score').html(score+'%');
  $('#final_score').append(first_par[0]);
  $('#final_score').append(boutton_certificat);
  $('#score_button').find('button').click(function(){
    generate_certif();
  });
  if(is_course_over()){
    $('#final_score').append(message_termine);
  }
};

function generate_result_fail(score){
  $('#final_score').append(first_par[0]);
  $('#final_score').append(second_par[0]);
  $('#insert_score').html(score+'%');
  $('#insert_score').css('color','red');
  $('#score_picto').find('img').attr('src',picto_failed);
  $('#score_picto').find('img').attr('class','svg picto_add_failed');
  if(is_course_over()){
    $('#final_score').append(message_termine);
  }
  else{
    $('#final_score').append(reset_bouton);
  }
};

function insert_info_score(value) {
  $('#result-content').append(template_and_title);
  $('#final_score').append(picto);
  $('#final_score').append(score_div);
}

// Display/Hide score panel on title click
$('.result-score').live('click', function(){
  console.log('click')
  $(this).toggleClass('active');
  if($(this).hasClass('active')){
    $("#result-content").html('');
    console.log('result score active');
    returnScore();
  }
  else{
    $("#result-content").html('');
  }
})
//Display score Panel on next last question click
function open_result_panel(){
  if(!$('#holding-section-result').hasClass('active')){
    $('.result-score').trigger( "click" );
  }
}

function get_completion_status_tma(username,course_key,subsection_id){
  console.log('entering ajax call')
  $.ajax({
      url:"/api/completion/v1/subsection-completion/"+username+"/"+ course_key +"/"+subsection_id+'/',
      type:'GET',
      dataType:'json',
      success:function(data){
           console.log('completion state')
           console.log(data)
      },
      error: function(error){
        console.log(error)
      }
    });
}
function get_completion_status_tma_for_quiz(username,course_key,subsection_id){
  console.log('entering ajax call')
  $.ajax({
      url:"/api/completion/v1/subsection-completion/"+username+"/"+ course_key +"/"+subsection_id+'/',
      type:'GET',
      dataType:'json',
      success:function(data){
        console.log('completin state for subsection')
        console.log(data)
      },
      error: function(error){
        console.log(error)
      }
    });
}
function returnScore() {
  $.ajax({
    url:'/api/atp/couseware_certif/'+course_id+'/',
    type:'GET',
    dataType:'json',
    success:function(data) {
      console.log('Entering courseware certif')
      console.log(data)
      var passed = data.passed;
      var is_graded = data.is_graded;
      var score = parseFloat(data.percent);
      if(score.toString().indexOf('.') == -1) {
        score=score+'.0'
      }
      $('#insert_score').text(score+'%');
      var grade_cutoffs = data.grade_cutoffs;
      var overall_progress = data.overall_progress;
      insert_info_score();
      if(passed && score >= grade_cutoffs) {
          generate_result_success(score);
      }else{
          generate_result_fail(score);
      }
      $('img.svg').each(function(){
          var $img = $(this);
          var imgID = $img.attr('id');
          var imgClass = $img.attr('class');
          var imgURL = $img.attr('src');
          $.get(imgURL, function(data) {
              // Get the SVG tag, ignore the rest
              var $svg = $(data).find('svg');
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
      $('#result-content').show();
    }
  });
};

/* XITI */
$('.seq_content_next a').each(function(){
  $(this).attr('onclick','followClickEvents(this,\'next\',\'navigation\')');
});
/* ENABLE SCORE PANEL AFTER QUIZ*/
function enable_score_panel(url_last_question){
  $(".problems-wrapper").each(function(){
    if($(this).attr('data-url')==url_last_question){
      $(this).find('.next_button').attr('onclick','open_result_panel()');
    }
  })
  //Change colors of result section to make it available
  $('.result-score-title h3').addClass('primary-color-text');
  $('.result-score h3.disabled_score').removeClass('disabled_score');
  $('.result-score').removeAttr("disabled");
  $('.result-score h3').addClass('secondary-color-text');
};

function all_questions_answered(){
  var all_answered=false;
  // All questions answered only if all have class finished and quiz is accessible
  if($('.problems-wrapper.finished').length==$('.problems-wrapper').length && $('.problems-wrapper').length!=0){
    all_answered=true;
    console.log(all_answered)
  }
  return all_answered;
}

$(document).ready(function() {
  //to change
  url_last_question=$('.sequence-nav').last().attr('data-url');
  // Last question has been answered
  $(document).ajaxSuccess(function(event, xhr, settings) {
      url_last_question=$('.problems-wrapper').last().attr('data-url');
      if ($('.sequence-nav').eq(-2).html().indexOf('Completed') > -1) {
        enable_score_panel(url_last_question);
        result_enabled=true;
        }
  });
  //or all questions are answered
  if(all_questions_answered()){
    console.log("all")
    console.log($('#result-content').offset())
    $(document).scrollTo($('#result-content').offset().top);
    enable_score_panel(url_last_question);
    result_enabled=true;
  }else{
   scroll_to_ques($('.last_finished').last().attr('data-problem-id'))
  }
});


/* DISABLE QUIZ IF COURSE IS OVER */
$(document).ajaxSuccess(function(event, xhr, settings) {
  if (settings.url.indexOf('/completion_status') > -1) {
    if(is_course_over()){
      $('.seq_problem').each(function(){
        $(this).attr('disabled', 'disabled');
        $(this).addClass('inactive').removeClass('active');
        $(this).addClass('disabled_unit_tma');
        if($('#seq_content').attr('aria-labelledby')==$(this).attr('id')){
          $('#seq_content').html('');
        }
        id_quiz_tab=$(this).attr('id').replace('tab_','');
      });
      id_next_button="#seq_content_next_"+id_quiz_tab;
      $(id_next_button).hide();
      enable_score_panel(url_last_question);
    }
  }
});

    function reset_problem(location,count,problem_lengt) {
        var pdata = {
            problem_to_reset: location,
            unique_student_identifier: user,
            delete_module: true
        };
        $.ajax({
            type: 'POST',
            url: getURL("reset_student_attempts"),
            data: pdata,
            success: function(data) {
               console.log('reset')
                    var countt = count +1;
                    console.log(countt)
                    console.log(problem_lengt)
                    if(countt>=problem_lengt){
                        window.location.reload(true);
                     }
            },
            error: function(request, status, error) {
 	 	console.log(erro)
            },
            dataType: 'json'
        });
    };


    var getURL = function(action) {
        var pathname = window.location.pathname;
        var index = pathname.indexOf('/courseware');
        if (index <= 0) {
            index = pathname.indexOf('/', '/courses/'.length);
        }
        return pathname.substr(0, index) + '/instructor/api/' + action;
    };

