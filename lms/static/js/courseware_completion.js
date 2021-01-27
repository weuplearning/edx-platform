function completion_nav_handler(course_id,user,item) {

        var urlCompletion ="/tma_apps/" + course_id +"/completion/get_course_completion";
        var url = $(location).attr("href").split('/')[4];
        get_completion_status_tma(user,url,item)
        // Get all chapters and assign them useful information for handling style dynamicaly

        check_unit_completion(chapter_state())
        check_score()
         //Change unit's title appearance if completed

        
         $(document).ajaxSuccess(function(event, xhr, settings) {
            var currentUnit = $(".xblock.xblock-student_view.xblock-student_view-vertical.xblock-initialized").data("usage-id");
            var  url ="/tma_apps/" + course_id +"/" + currentUnit +"/completion/get_unit_completion";

            if (settings.url.indexOf('/publish_completion') > -1 || settings.url.indexOf('/problem_check') > -1 && xhr.responseJSON.success === "correct") {
            $.ajax({
              type: "get",
              url: url,
              success: function (response) {
                if(response.success){
                  check_unit_completion(chapter_state(true))
                  //check_score()
                }
              }
          });
        
        };
      });

    function chapter_state(newEl){
      chapter_list={}
      if(newEl){
        chapter_id=$($(".tma_tab.active")).attr('id')
        chapter_list[chapter_id]={'completed':true,'available':true};
      }else{
      $(".tma_tab").each(function(){
        if($(this).hasClass('completed')){
          chapter_id=$(this).attr('id')
          chapter_list[chapter_id]={'completed':true,'available':true};
        }else{
          chapter_id=$(this).attr('id')
          chapter_list[chapter_id]={'completed':false,'available':false};
        }
      })
      }
      return chapter_list;
    }
  function check_unit_completion(chapter){
      Object.keys(chapter).forEach(function(key){
        if(chapter[key].available){
          console.log($('#'+key))
          $('#'+key).removeClass('disabled_unit_tma');
          $('#'+key).removeAttr("disabled");
          $('#'+key).children('.sequence-bottom').children('.button-next').removeAttr('disabled')
          $('#'+key).children('.sequence-bottom').children('.button-next').removeClass('disabled')
        }
      });
    }

  function check_score(){
    $.ajax({
      type: "get",
      url: urlCompletion,
      success: function (response) {
      console.log(response.completion_rate)
        if(response.completion_rate === 1){
            $('.result-score').removeClass('disabled')
            returnScore()
        }
      },error : function(error){
            console.log('error')
      }
    });
  }

  function returnScore() {
    $.ajax({
      url:'/api/atp/courseware_certif/'+course_id+'/',
      type:'GET',
      dataType:'json',
      success:function(data) {
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
};

