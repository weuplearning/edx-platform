/* courses cards generator */
var start_cible = "#start_courses_atp";
var progress_cible = "#progress_courses_atp";
var end_cible = "#end_courses_atp";

function render_course_cards(data,cible,status,action,category) {
  $(cible).html('');
  var rows = data.length;
  var effective_rows = 0;
  if(!status) {
      rows = 4;
    var Width = window.screen.width;
    if(Width <= 1600) {
      rows = 3;
    }
    if(Width <= 1196) {
      rows = 2;
    }
    if(Width <= 814) {
      rows = 1;
    }
    if(rows > data.length) {
      rows = data.length;
    }
  }
  if(category != 'all' && category != '') {
    rows = data.length;
  }
  for(var i=0;i<rows;i++) {
    var _cur = data[i];
    if(category == '') {
      course_card(
        _cur.category,
        _cur.course_id,
        _cur.course_img,
        _cur.course_progression,
        _cur.duration,
        _cur.required,
        _cur.display_name_with_default,
        _cur.content_data,_cur.percent,
        _cur.passed,
        action,
        cible
      );
      effective_rows = data.length;
    }else{
      if(_cur.category.replace(/ /g,'').toLowerCase() == "fundamentals") {
        _cur.category = "fundamental";
      }
      if(category == _cur.category.replace(/ /g,'').toLowerCase()) {
        course_card(
          _cur.category,
          _cur.course_id,
          _cur.course_img,
          _cur.course_progression,
          _cur.duration,
          _cur.required,
          _cur.display_name_with_default,
          _cur.content_data,
          _cur.percent,
          _cur.passed,action,cible
        );
        effective_rows++;
      }
    }
  }
  $(cible).append('<span style="display:block;clear:left"></span>');
  intervalDetectHeight();
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

//$('img.svg').show();
// show module button
button_views(effective_rows,cible);

}

function button_views(effective_rows,cible) {
  if(typeof effective_rows === "undefined") {
    effective_rows = 0;
  }
  var Width = window.screen.width;
  var number = 0;
  var devices = [
    {min_width:0,max_width:814,number:1},
    {min_width:814,max_width:1196,number:2},
    {min_width:1196,max_width:1600,number:3},
    {min_width:1600,max_width:100000,number:4}
  ];
  for(var i=0;i<devices.length;i++) {
    if(Width > devices[i].min_width && Width <= devices[i].max_width) {
      number = devices[i].number;
    }
  }
  //console.log(number+' '+cible+' '+effective_rows);
  if(number < effective_rows) {
    $(cible).parent().find('.atp_dashboard_active_course').removeClass('is_none_more');
  }else{
    $(cible).parent().find('.atp_dashboard_active_course').addClass('is_none_more');
  }
}

$(document).ready(function(){
  render_course_cards(
    courses_atp.progress_courses,
    progress_cible,
    course_status.progress_courses,
    "cours",
    course_category
  );
  render_course_cards(
    courses_atp.start_courses,
    start_cible,
    course_status.start_courses,
    "invite",
    course_category
  );
  render_course_cards(
    courses_atp.end_courses,
    end_cible,
    course_status.end_courses,
    "finish",
    course_category
  );
  button_views();
})
$(window).resize(function(){
  render_course_cards(
    courses_atp.progress_courses,
    progress_cible,
    course_status.progress_courses,
    "cours",
    course_category
  );
  render_course_cards(
    courses_atp.start_courses,
    start_cible,
    course_status.start_courses,
    "invite",
    course_category
  );
  render_course_cards(
    courses_atp.end_courses,
    end_cible,
    course_status.end_courses,
    "finish",
    course_category
  );
  button_views();
})
