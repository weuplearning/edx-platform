define(['domReady', 'jquery', 'underscore','jquery.ui','tinymce','jquery.tinymce'],function(domReady, $, _) {
  var onReady = function() {
    class invite {
      constructor(adress,object,body,action,tinyMce,data,checkbox) {
        this.adress = adress;
        this.object = object;
        this.body = body;
        this.action = action;
        this.data = data;
        this.tinyMce = tinyMce;
        this.checkbox = checkbox;
      }
      // set tinyMce
      setTinyMce(obj) {
        this.tinyMce = obj;
      }
      // set action
      setAction(val) {
        this.action = val;
      }
      // upload and pre-register only users
      register_only(id,file) {
        var This = $('#'+id);
        This.click(function(){
          var data = new FormData($(file).get(0));
          data.append('request_type','register_only');
          this.data = data;
        })
      }
      // load csv file to custom user input
      load_csv(file,action) {
        var data = new FormData($(file).get(0));
        data.append('request_type',action);
        //data
        this.data = data;
      }
      // action on use file upload
      file_up_input(id,next) {
        var This = $('#'+id);
        This.change(function(){
          var val = This.attr('value');
          var split = val.split('.');
          var long = split.length - 1;
          var check = split[long];
          if(check.indexOf('csv') == -1) {
            alert('fichier au format incorect');
          }else{
            $('#'+next).show();
          }
        })
      }
      // action on input adress
      actionAdress(id) {
        var This = $(id);
        This.on('change keyup paste',function(){
          var text = This.attr('value');
          var split = text.trim().split(/\s+/);
          var re = /^(([^<>()\[\]\\.,;:\s@"]+(\.[^<>()\[\]\\.,;:\s@"]+)*)|(".+"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))+[\s]$/;

          if(re.test(text)) {
            var span = "<div class='vr'><div class='data_mail' data-mail='"+text+"'><span>"+text+"</span><div class='close_span'></div></div></div>";
            This.parent().prepend(span);
            This.attr('value','');
            $('.close_span').click(function(){
              var That = $(this);
              That.parent().parent().remove();
            })
          }else{
            if(text.indexOf(' ') != -1){
              var split = text.trim().split(/\s+/);
              for(var i = 0;i<split.length;i++) {
                var str = split[i];
                var reg = /^(([^<>()\[\]\\.,;:\s@"]+(\.[^<>()\[\]\\.,;:\s@"]+)*)|(".+"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/;
                if(reg.test(str)) {
                  var span = "<div class='vr'><div class='data_mail' data-mail='"+str+"'><span>"+str+"</span><div class='close_span'></div></div></div>";
                  This.parent().prepend(span);
                }
              }
              This.attr('value','');
              $('.close_span').click(function(){
                var That = $(this);
                That.parent().parent().remove();
              })
           }
          }
        })
      }
      // return file adress action
      actionAdressOnLoad(email,id) {
        var re = /^(([^<>()\[\]\\.,;:\s@"]+(\.[^<>()\[\]\\.,;:\s@"]+)*)|(".+"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/;
        if(re.test(email)) {
          var span = "<div class='vr'><div class='data_mail' data-mail='"+email+"'><span>"+email+"</span><div class='close_span'></div></div></div>";
          var check = true;
          $('#'+id).find('.data_mail').each(function(){
            var data = $(this).attr('data-mail');
            if(data == email) {
              check = false;
            }
          })
          if(check) {
            $('#'+id).prepend(span);
          }
        }
        $('.close_span').click(function(){
          var That = $(this);
          That.parent().parent().remove();
        })
      }
      // set custom adress from input
      setAdress(Class) {
        var This = $('.'+Class);
        var mails = [];
        This.each(function(){
          var data = $(this).data('mail');
          mails.push(data);
        })
        this.adress = mails;
      }
      /* get tinymce value method */
      tinyMceContent() {
        var content = this.tinyMce.activeEditor.getContent();
        this.body = content;
      }
      /* set checkbox */
      setCheckbox(Class) {
        var data = [];
        $(Class).each(function(){
          var This = $(this);
          var val = This.val();
          var check = This.is(':checked');
          if(check) {
            data.push({name:val,value:true});
          }else{
            data.push({name:val,value:false});
          }
        })
        this.checkbox = data;
      }
      /* set object and body method */
      setObjectBody(object) {
        this.object = $(object).val();
      }
      /* get this .data */
      getData() {
        return this.data;
      }
      // sendMailData
      sendMailData(adress) {
        var data = new FormData();
        // check_actions required
        for(var i=0;i<this.checkbox.length;i++) {
          data.append(this.checkbox[i].name,this.checkbox[i].value);
        }
        // get all adresses
        this.setAdress(adress);
        data.append('adress',this.adress);
        // get object value
        data.append('object',this.object);
        // append body to data
        data.append('body',this.body);
        // data request_type
        data.append('request_type','send_mail');
        // get body value
        this.data = data;
      }
    }
    /* init tinymce */
    tinymce.init({
      selector: '#mytextarea',
      plugins: "textcolor colorpicker link",
      toolbar: "forecolor backcolor link",
      target_list: false,
      init_instance_callback: insert_contents,
    });
    function insert_contents(inst) {
      inst.setContent('<p style="margin: 10px 0;"> </p><p style="margin: 10px 0;"><span style="color:#06144d"><span style="font-size:14px"> </span></span><span style="color:#06144d"><span style="font-size:14px">Vous êtes invité à participer au module de formation<b> GLOBAL DISRUPTIVE OPPORTUNITIES.</b></span></span></p><p style="margin: 10px 0;"><span style="color:#06144d"><span style="font-size:14px"> </span></span></p><p style="margin: 10px 0;"><span style="color:#06144d"><span style="font-size:14px"><b>Vous avez jusqu’au 15 octobre 2017 </b>pour compléter le module de formation.</span></span></p><p style="margin: 10px 0;"><span style="color:#06144d"><span style="font-size:14px">Ce module de formation est<b> obligatoire.</b></span></span></p><p style="margin: 10px 0;"><span style="color:#06144d"><span style="font-size:14px"> </span></span></p><p style="margin: 10px 0;"><span style="color:#06144d"><span style="font-size:14px">Un score de<b> 80% </b>minimum est requis pour valider le module de formation.</span></span></p><p style="margin: 10px 0;"><span style="color:#06144d"><span style="font-size:14px"> </span></span></p><p style="margin: 10px 0;"><span style="color:#06144d"><span style="font-size:14px">Pour accédez au module de formation GLOBAL DISRUPTIVE OPPORTUNITIES, veuillez cliquer sur le lien suivant : <a href="">Ligne Métier Marketing Retail</a></span></span></p>');
    }
    /* action on submit form */
    var submit = '#upload_form_participant';
    var mail_invite = new invite();
    mail_invite.file_up_input('invite_participant','choise_from_file');
    mail_invite.actionAdress('#email_1');
    // register users from csv
    $('#register_from_csv').click(function(){
      mail_invite.load_csv(submit,'register_only');
      var path = window.location.path;
      var data = mail_invite.getData();
      $.ajax({
        url: path,
        data: data,
        cache: false,
        contentType: false,
        processData: false,
        type: 'POST',
        success: function(data){
          var retour = data.message;
          for(var i = 0;i<retour.length;i++) {
            var email = retour[i].email;
            mail_invite.actionAdressOnLoad(email,'custom_mail_box');
          }
          $('#checkbox_custom').prop( "checked", true );
        }
      })
    })
    $(submit).submit(function(e){
      e.preventDefault();
      /* use invit class */
      mail_invite.setTinyMce(tinymce);
      mail_invite.setObjectBody('#email_2');
      mail_invite.setCheckbox('.checkbox_mail_field');
      mail_invite.tinyMceContent();
      mail_invite.sendMailData('data_mail');
      var data = mail_invite.getData();
      var path = window.location.path;
      $.ajax({
        url: path,
        data: data,
        cache: false,
        contentType: false,
        processData: false,
        type: 'POST',
        success: function(data){

        }
      });
      return false;
    })
    /* end file upload submit */
    $('#send_email').click(function(){
      $(submit).submit();
    })
  };
  domReady(onReady);
  return {
      onReady: onReady
  };
})
