function clickInfo() {
 $('.up_block').find('h4').click(function(){
  var This = $(this);
  if(This.find('.arrow_course_about').hasClass('arrow-right')) {
   This.find('.arrow_course_about').removeClass('arrow-right');
   This.find('.arrow_course_about').addClass('arrow-bottom');
  }else if(This.find('.arrow_course_about').hasClass('arrow-bottom')) {
   This.find('.arrow_course_about').removeClass('arrow-bottom');
   This.find('.arrow_course_about').addClass('arrow-right');
 };
  if(!This.hasClass('border_atp_course_about')) {
   This.addClass('border_atp_course_about');
  }else{
   This.removeClass('border_atp_course_about');
 };
  This.parent().parent().find('.down_block').slideToggle(1200);
});
};
// repport code aurelien
function ariane_click() {
  $('#atp_ariane_about_dashboard').click(function(){
    window.location.href='/dashboard';
  });
};

$(document).ready(function(){
 clickInfo();
 ariane_click();
})
