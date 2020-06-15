/*average chapter results menu action*/
$('.chapter_box').find('h3').click(function(){
  var Parent = $(this).parent();
  var This = $(this);
  $('.chapter_box').not(Parent).find('.section_box').slideUp(800);
  $('.chapter_box').not(Parent).find('.vertical_box').slideUp(800);
  $('.chapter_box').find('h3').not(this).css('border-bottom-color','#fff');
  $(this).css('border-bottom-color','#c8c8c8');
  $.when(Parent.find('.section_box').slideToggle(800)).then(function(data,textStatus,jqXR){
    if(Parent.find('.section_box').attr('style') == 'display: none;' || Parent.find('.section_box').attr('style') === undefined) {
      This.css('border-bottom-color','#fff');
    }
    $('html, body').animate({
        scrollTop: $(this).offset().top -= 153
    }, 600);
    alignCells();
  })
})


/* get averages grades per problems */
$('#block_average').find('.section_box').find('h4').click(function(){
  $('#voile').show();
  var This_h4 = $(this);
  var Parent_h4 = $(this).parent();
  var user_grade_cell_length = Parent_h4.find('.user_grade_cell').length;
  var user_li_length = Parent_h4.find('.problem_box').find('li').length;
  var cible = Parent_h4.find('.problem_box');
  var data_id = [];
  var course_id = $('#participant_search').data('courseid');
  var url = '/courses/'+course_id+'/stat_dashboard/get_course_blocks_grade/';
  Parent_h4.find('.data_content').each(function(){
    var id = $(this).data('children');
    var title = $(this).data('title');
    var obj = {id:id,title:title};
    data_id.push(obj);
  })
  data = {data_id:data_id};
  data = JSON.stringify(data);
  if(user_grade_cell_length == 0 && user_li_length == 0){
  $.when($.ajax({
      url:url,
      contentType: "application/json; charset=utf-8",
      type:'POST',
      dataType:'json',
      data:data,
      success:function(data) {
        cible.html('');
        console.log(data.course_grade);
        i=0;
        for (i;i<question_orders.length;i++){
          current_question = data.course_grade[question_orders[i]];
          display_name = current_question.display_name;
          vertical_name = current_question.vertical_name;
          moyenne = current_question.moyenne;
          max_grade = current_question.max_grade;
          avg = Math.round((moyenne / max_grade) * 100);
          stat = 100 - avg;
          if(stat == 100) {
            style = "background:#CB5744;";
          }
          var div = '<div class="user_grade_cell"><div class="vertical_name">'+vertical_name+'</div><h6>'+display_name+'</h6><div class="bart_chat" ><div class="success_chart_bart" style="width:'+avg+'%;"></div></div><div class="score_line"><div class="chart_success">'+avg+'%</div><div class="chart_fail">'+stat+'%</div><span style="display:block;clear:both;"></span></div>';
          cible.append(div);
        }
        cible.append('<div style="clear:left;"></div>');
      }
    })).then(function(data,textStatus,jqXHR) {
    $('#voile').delay(800).fadeOut();
    $('.problem_box').hide();
    cible.show();
    alignCells();
    $('html, body').animate({
        scrollTop: Parent_h4.offset().top -= 153
    }, 600);
  })
}else{
  $('#voile').delay(800).fadeOut();
  $('.problem_box').hide();
  cible.show();
  $('html, body').animate({
      scrollTop: Parent_h4.offset().top -= 153
  }, 600);
}
})

/* function aligner cellules */
function alignCells() {
  $('.vertical_name').attr('style','');
  $('.user_grade_cell').find('h4').attr('style','');
  $('.user_grade_cell').find('h6').attr('style','');
  $('.user_grade_cell').find('p').attr('style','');
  var z = 0;
  var p = 0;
  var s = 0;
  var e = 0;
  $('.vertical_name').each(function(){
    var This = $(this);
    var i = This.height();
    if(i > e) {
      e = i;
    }
  })
  $('.user_grade_cell').find('h4').each(function(){
    var This = $(this);
    var i = This.height();
    if(i > z) {
      z = i;
    }
  })
  $('.user_grade_cell').find('h6').each(function(){
    var This = $(this);
    var i = This.height();
    if(i > s) {
      s = i;
    }
  })
  $('.user_grade_cell').find('p').each(function(){
    var This = $(this);
    var i = This.height();
    if(i > p) {
      p = i;
    }
  })
  $('.user_grade_cell').find('h4').css('height',z+'px');
  $('.user_grade_cell').find('h6').css('height',s+'px');
  $('.user_grade_cell').find('p').css('height',p+'px');
  $('.vertical_name').css('height',e+'px');
}
/* function call ajax recuperation de données utilisateur */
function callUser(username,course_id) {
  $('#inside_user_content').hide();
  var url = window.location.href;
  url = url+'/get_grade/'+username+'/';
  console.log(url);
  $.ajax({
    type: 'GET',
    dataType:'json',
    url:url,
    success:function(data) {
      $('#content_participant').find('.problem_box').each(function(){
        if($(this).find('li').length == 0) {
         $(this).html('');
        }
      });
      var user_info = data.user_info;
      var th = '';
      var td = '';
      for(var j=0;j<user_info.length;j++) {
        var keys_user_info = Object.keys(user_info[j]);
        var _insert = '';
        if(keys_user_info[0] == "First_name") {
         _insert = stat_first;
        }else if(keys_user_info[0] == "Last_name") {
         _insert = stat_last;
        }else if(keys_user_info[0] == "Grade") {
         _insert = stat_grade;
        }else{
         _insert = keys_user_info[0].replace('_',' ');
        }
        th = th+'<th>'+_insert+'</th>';
        td = td+'<td id="'+keys_user_info[0].toLowerCase()+'">'+user_info[j][keys_user_info[0]]+'</td>';
      };
      th = '<thead><tr>'+th+'</tr></thead>';
      td = '<tbody><tr>'+td+'</tr></tbody>';
      var table = '<table>'+th+td+'</table>';
      $('#table_participant').html(table);
      var course_grade = data.course_grade;
      var course_grade_length = course_grade.length;
      var i = 0;
      for(i;i<course_grade_length;i++) {
        var name = course_grade[i].display_name;
        var earned = course_grade[i].earned;
        var possible = course_grade[i].possible;
        var root = course_grade[i].root;
        /* get vertical name */
        var vertical_name = '';
        var cible = '';
        $('#content_participant').find('.data_content').each(function(){
          var This = $(this);
          var values = This.data('children');
          if(values.indexOf(root) != -1) {
            vertical_name = This.data('title');
            cible = This.parent().find('.problem_box');
          }
        })
        var avg = parseInt(earned / possible * 100);
        var div = '<div class="user_grade_cell"><div class="vertical_name">'+vertical_name+'</div><h6>'+name+'</h6><div class="bart_chat" ><div class="success_chart_bart" style="width:'+avg+'%;"></div></div><div class="score_line"><div class="chart_success">'+earned+'</div><div class="chart_fail">'+possible+'</div><span style="display:block;clear:both;"></span></div>';
        if(cible != '') {
          cible.append(div);
        }
      }
      $('#content_participant').find('.problem_box').each(function(){
        $(this).append('<div style="clear:left"></div>');
      });
      $('#inside_user_content').show();
      alignCells();
    }
  })
}
/* call ajax au click sur le bouton du form des données user */
$('#participant_search').click(function(){
  var username = $("#name_participant").val();
  var course_id = $('#participant_search').data('courseid');
  if(username != '') {
    callUser(username,course_id);
    $('#list_participant').html('');
    $('#list_participant').attr('style','');
  }
})

/* function get usrs from all_user on #name_participant keyup */
$('#nav_block_stat_question').find('button').click(function(){
  var This = $(this);
  var data = This.data('position');
  $('#nav_block_stat_question').find('button').not(this).css('opacity','0.6');
  This.css('opacity','1');
  $('.block_question').hide();
  $('#block_'+data).show();
})

/* function recuperation username */
$("#name_participant").on('keyup', function(event) {
  var This = $(this);
  var val = This.val();
  if(val.length >= 3) {
    var course_id = $('#participant_search').data('courseid');
    var url = '/courses/'+course_id+'/stat_dashboard/get_user/'+val+'/';
    $.ajax({
      type:'GET',
      dataType:'json',
      url:url,
      success:function(data) {
        var i = 0;
        all_user = data.usernames
        var length = all_user.length;
        var array_save = [];
        for(i;i<length;i++) {
          var _user = all_user[i];
          var _array = _user.values
          var _id = _user.id
          for(var c=0;c<_array.length;c++) {
            if(_array[c].indexOf(val) != -1) {
              var q = {
                id: _array[0],
                value:_array[1]+' - '+_array[2]+' - '+_array[0]
              }
              array_save.push(q);
            }
          }
        }
        var j = 0;
        var array_length = array_save.length;
        if(array_length < 11 && array_length > 0) {
          $('#list_participant').html('');
          for(j;j<array_length;j++) {
            console.log(array_save[j]);
            $('#list_participant').append('<span data-id="'+array_save[j].id+'" >'+array_save[j].value+'</span>');
          }
          $('#list_participant').show();
        }else{
          $('#list_participant').attr('style','');
        }
        $('#list_participant').find('span').click(function(){
          var This = $(this);
          var course_id = $('#participant_search').data('courseid');
          var id = This.data('id');
          $('#name_participant').attr('value',id);
          $('#list_participant').html('');
          $('#list_participant').attr('style','');
          callUser(id,course_id);
        })
      }
    });
  }else{
    $('#list_participant').attr('style','');
  }
});
/* function action appuyer entree sur input text donnee user */
$('#name_participant').keypress(function (e) {
  if(e.which == 13) {
    var username = $("#name_participant").val();
    var course_id = $('#participant_search').data('courseid');
    if(username != '') {
      callUser(username,course_id);
      $('#list_participant').html('');
      $('#list_participant').attr('style','');
    }
  }
});
/* function click on <h3> on user's dashboard */
$('#content_participant').find('h3').click(function(){
  var This = $(this);
  var Parent = This.parent();
  var problem = Parent.find('.problem_box');
  $('#content_participant').find('.problem_box').not(problem).hide();
  problem.show();
})
