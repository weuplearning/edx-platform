// For IE versions that does'nt support endswith
if (typeof String.prototype.endsWith !== 'function') {
    String.prototype.endsWith = function(suffix) {
        return this.indexOf(suffix, this.length - suffix.length) !== -1;
    };
}

// For tracking the HTML components for completion
trackHTMLComponent = function(){
    var usageIds = [];

    $(".vert .xblock-student_view-html").each(function(){
      usageIds.push($(this).attr('data-usage-id'));
    });

    if(usageIds.length > 0){

      $.post({
        url: customTrackUrl,
        data: {
	  'course_id': JSON.stringify(course_id),
          'usage_ids': JSON.stringify(usageIds),
        },
        success: function(data){
          getCompletionStatus();
        }
      }); // post

    }
}

// For completion dots on accordian
getCompletionStatus = function(){
  sequential_id=$("#main>div.xblock.xblock-student_view.xblock-student_view-sequential").attr("data-usage-id");
  var completionStatusUrl='/completion_status/?course_id='+encodeURIComponent(course_id)+'&sequential_id='+encodeURIComponent(sequential_id);
  $.get({
    url: completionStatusUrl,
    success: function(data) {
       //TODO : target all sequence_nav buttons
       var previous_completed=false;

       // Get all chapters by default validated
       chapter_list={}
       $(".tma_chapters").each(function(){
         chapter_id=$(this).attr('id')
         chapter_list[chapter_id]={'completed':true,'available':false};
       })

       //Change unit's title appearance if completed
       $(".sequence-nav .sequence-list-wrapper button.nav-item").each(function(){
         if(data['completion_status'][$(this).attr('data-id')]==100){
              $(this).removeClass('disabled_unit_tma');
              $(this).removeAttr("disabled");
              $(this).find('h3').addClass('secondary-color-text').removeClass('inactive-color-text').addClass('hover-primary-text');
              previous_completed=true;
              // if at least one unit is completed then chapter is available
              chapter_list[$(this).attr('data-seq')]['available']=true;
         }else{
           // keep previous completion for quiz chapter only
              if(previous_completed && $(this).hasClass('seq_problem')){
                  $(this).removeClass('disabled_unit_tma');
                  $(this).removeAttr("disabled");
                  chapter_list[$(this).attr('data-seq')]['available']=true;
              }
              previous_completed=false;
              //if a single unit is not completed then chapter cannot be completed
              chapter_list[$(this).attr('data-seq')]['completed']=false;
         }
       });

       //Activate next button for units if completed
       $(".sequence .seq_content_next").each(function(){
         if(data['completion_status'][$(this).attr('data-id')]==100){
              $(this).removeClass('disabled_tma');
              $(this).attr('onclick','$("#'+$(this).attr('id').replace('seq_content_next_','tab_')+'").click()');
         }
       });

       //Change chapter title appearance if all units completed
        $(".tma_chapters").each(function(){
          // Change title color for available chapters
          if(chapter_list[$(this).attr('id')]['available']==true){
            $(this).find('h3').addClass('primary-color-text').removeClass('inactive-color-text');
            //CHANGE AMUNDI : All units under it must be available if chapter is available
            //NEW CHANGE 07/12 : Candidate must click next to get to next unit / Do not unlock all units if chapter is available
            var tma_chapter_identifier=$(this).attr('id')
            $('button.seq_other').each(function(){
              if($(this).attr('data-seq')==tma_chapter_identifier){
                //ACTIVATE UNIT
                //$(this).removeClass('disabled_unit_tma');
                //$(this).removeAttr("disabled");
                //ACTIVATE BUTTON NEXT
                next_btn_identifier='seq_content_next_'+$(this).attr('data-element');
                $('#'+next_btn_identifier).removeClass('disabled_tma').attr('onclick','$("#'+$('#'+next_btn_identifier).attr('id').replace('seq_content_next_','tab_')+'").click()');
              }
            })
            // Add check sign for completed chapters
            if(chapter_list[$(this).attr('id')]['completed']==true){
              if($(this).find('h3 i').length <=0){
                $(this).find('h3').html($(this).find('h3').html()+" <i class='fa fa-check'></i>");
              }
            }
          }
        });
    }
  }); // get

}

// Call the functions on document ready
$(document).ready(function(){
  if(completionEnabled){
    trackHTMLComponent();
    getCompletionStatus();
  }
});

// Call the functions on specific events
$(document).ajaxSuccess(function(event, xhr, settings){
  if( settings.url.endsWith('goto_position') ) {
    if(completionEnabled){
      trackHTMLComponent();
    }
  } else {
      var seen_video = settings.url.endsWith('save_user_state');
      var attended_problem = settings.url.endsWith('problem_check');
      var seen_hint = settings.url.endsWith('hint_button');
      var graded_lti_v2 = settings.url.endsWith('lti_2_0_result_rest_handler');
      var got_grade = settings.url.endsWith('grade_handler');
      var rendered_grade = settings.url.endsWith('render_grade');
      var seen_html = settings.url.endsWith('track_html_component');
      if (seen_video || attended_problem || seen_hint || graded_lti_v2 || got_grade || rendered_grade || seen_html) {
          getCompletionStatus();
      }
  }
});
