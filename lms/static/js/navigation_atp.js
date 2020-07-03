function toggleNav() {
  $('#logo_atp_redirect').click(function(){
    window.location.href = '/';
  })
 $('.sub_menu').click(function(){
  var This = $(this);
  var data = This.data('location');
  var other_location = $('.sub_menu').not(this).data('location');
  $('#'+other_location).attr('style','');
  $('#'+data).toggle();
 })

 $(document).bind('click', function(e) {
   if(!$(e.target).is('.sub_menu')) {
     $('.sub_menu').each(function(){
       var This = $(this);
       var data = This.data('location');
       $('#'+data).attr('style','');
     })
   }
 });

 $('#menu_module_apt').find('button').click(function(){
  var This = $(this);
  var data = This.data('location');
  var speed = 750;
  This.parent().toggle();
  $('html, body').animate( { scrollTop: $('#'+data).offset().top -= 148 }, speed );
  return false;
 })
}

function navChange() {
 var width = $(window).width();
 width = parseInt(width);
 if(width <= 1022) {
  $('#atp_menu_mobile').click(function(){
    $('#sub_menu').toggle();
  })
 }else{
  $('#sub_menu').attr('style','');
 }
}
function replace_log() {
  var width = $(window).width();
  if(width < 1022) {
    $( "#atp_menu_mobile" ).before( $("#log_user_action") );
  }
}
$(document).ready(function(){
 toggleNav();
 navChange();
 //replace_log();
})

$(window).resize(function(){
 navChange();
 //replace_log();
})
