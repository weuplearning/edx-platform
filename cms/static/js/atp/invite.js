define(['domReady', 'jquery', 'underscore','js/utilitaires/dynatable/jquery.dynatable','js/utilitaires/papaparse/papaparse.min','jquery.ui'],function(domReady, $, _, dynatable, Papa) {
  var onReady = function() {



//////////////////////////////////////////// ACTIONS //////////////////////////////////////

//Check csv on submit
$(document).ready(function () {
  times_displayed=0;
  required_fields = ['email','first_name','last_name'];
  header_fields = ['email','first_name','last_name','level_1','level_2','level_3','level_4'];
  $("#invite_participant").change(ParseCsvFile);

  // register users from csv
  $('#register_from_csv').on('click',function(){

    $('#header-error-details').html('');
    $('#incorrect-error-detail').html('');
    $('#missing-error-detail').html('');
    $('#csv_import_feedback').css('display','none');
    var csrftoken = $("#csrf").html();
    var path = window.location.path;
    var data = new FormData();
    data.append('file',$('#invite_participant')[0].files[0])
    data.append('notify_participants',document.getElementById('notify_participants_chkbox').checked);
    data.append('request_type','register_only');
    $.ajax({
      url:path,
      type: 'POST',
      processData: false,
      contentType: false,
      headers:{
        "X-CSRFToken": csrftoken
      },
      data:data,
      success:function(data){
        $('#csv_import_feedback').css('display','block');
        $('#csv_import_preview').css('display','none');
        $('#register_user_btn').css('display','none');
      }
    })
  })
});

//////////////////////////////////////////////////// CHECK CSV FILE //////////////////////////////////////////////////
function ParseCsvFile(evt) {
  $("#csv_import_error").css('display','none');
  $('#csv_import').html('').css('display','none');
  $('#csv_import_preview').css('display','none');
  $('#csv_import_feedback').css('display','none');
  $('#header-error-details').html('');
  final_valid_records={};
  final_error_records={};
  final_total_records={};
  $('#register_user_btn').css('display','none');
  var file = evt.target.files[0];
  var fileread = new FileReader();
  fileread.onload = function(e) {
    if(e.target.result.indexOf('ï¿½')>-1){
      encoding_type="ascii"
    }
    else{
      encoding_type="utf-8"
    }
    Papa.parse(file, {
      header: true,
      dynamicTyping: true,
      encoding: encoding_type,
      skipEmptyLines:'greedy',
      trimHeaders: true,
      complete: function(results) {
        csv_users = clean_maj(results['data']);
        errors = check_csv_header(csv_users);
        if(errors['missing_header'].length===0){
          check_results = check_csv_errors(csv_users);
          error_records = check_results['errors'];
          total_records=check_results['total'];
          display_csv_rows(total_records);
          if(error_records.length==0){
            $('#register_user_btn').css('display','block');
          }
          else{
            manage_error_display(error_records);
          }
        }
        else{
          manage_error_display(errors['missing_header']);
        }
      }
    });
  };
  fileread.readAsText(file);
}

function clean_maj(csv_users){
  i=0;
  csv_users_cleaned={};
  for (user in csv_users){
    user_obj =csv_users[user];
    var key, keys = Object.keys(user_obj);
    var n = keys.length;
    var new_user_obj={}
    while (n--) {
      key = keys[n];
      new_user_obj[key.toLowerCase()] = user_obj[key];
    }
    csv_users_cleaned[i]=new_user_obj;
    i+=1;
  }
  return csv_users_cleaned;
}

function check_csv_header(csv_users_cleaned){
  errors={};
  errors['missing_header']=[];
  for(i=0;i<required_fields.length;i++){
    if (!(required_fields[i] in csv_users_cleaned[0])){
      errors['missing_header'].push(required_fields[i]);
    }
  }
  return errors;
}

function check_csv_errors(csv_users){
  errors=[];
  total_records=[];
  check_results={};
  for(user in csv_users){
    user_data=csv_users[user];
    valid=true
    user_data['missing_fields']=[];
    user_data['line']=parseInt(user)+2;

    for (var i = 0; i < required_fields.length; i++){
      if(user_data[required_fields[i]]==undefined || user_data[required_fields[i]]==null){
        valid=false;
        user_data['missing_fields'].push(required_fields[i]);
      }
      else if(required_fields[i]=='email' && !validateEmail(user_data['email'])){
        valid=false;
        user_data['invalid_email']=true;
      }
    }

    if(!valid){
      errors.push(user_data);
    }
    total_records.push(user_data)
    
  }
  check_results['errors']=errors;
  check_results['total']=total_records;
  return check_results;
}


function display_csv_rows(results){
  $('#csv_import').css('display','block');
  set_header();
  if(times_displayed<1){
    dynatable = $('#csv_import').dynatable({
    dataset: {
        records: results
    }
    }).data('dynatable');
  }
  else{
    dynatable.settings.dataset.originalRecords = results;
    dynatable.process();
  }
  times_displayed+=1;
  $('.dynatable-active-page a').addClass('primary-color-bg');
  $('#csv_import_preview').css('display','block');

  //Add classes to columns
  j=1;
  $('#csv_import tr').each(function(){
    for(i=0;i<header_fields.length;i++){
      $(this).find('td').eq(i).attr('id',header_fields[i]+'_'+j);
    }
    j+=1;
  })
}

function manage_error_display(errors){
  $('#csv_import_error').css('display','block');
  $('.error-message').each(function(){
    $(this).css('display','none');
  })

  if('missing_header' in errors){
    header_error='';
    $("#incorrect_header").css('display','block');
    header_error+='<ul>';
    for(missing_header in errors['missing_header']){
      header_error+='<li>'+errors['missing_header'][missing_header]+'</li>';
    }
    header_error+='</ul>';
    $('#header-error-details').html(header_error);
  }
  else{
    for(user in errors){
      if('invalid_email' in errors[user]){
        $("#incorrect-data").css('display','block');
        id_name="email_"+errors[user]['line'];
        $('#'+id_name).css('background-color','red').css('color','white');
      }
      else if ('missing_fields' in errors[user]){
        $("#required-data").css('display','block');
        for(i=0;i<errors[user]['missing_fields'].length;i++){
          id_name=errors[user]['missing_fields'][i]+'_'+errors[user]['line'];
          $('#'+id_name).css('background-color','red').css('color','white');
        }
      }
    }
  }

}



/////////////////////////////////////////////////////////// SUPPORT FUNCTIONS //////////////////////////////////////////////////////////////
function set_header(){
  $('#csv_import').append('<thead><tr></tr></thead>');
  for (i=0;i<header_fields.length;i++){
      $('#csv_import thead tr').append('<th class="primary-color-bg white-border white-text">'+header_fields[i]+'</th>');
  }
}

function validateEmail(email) {
    var re = /^(([^<>()\[\]\\.,;:\s@"]+(\.[^<>()\[\]\\.,;:\s@"]+)*)|(".+"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/;
    return re.test(String(email).toLowerCase());
}

  };
  domReady(onReady);
  return {
      onReady: onReady
  };
})
