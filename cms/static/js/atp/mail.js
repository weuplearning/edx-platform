define(['domReady', 'jquery', 'underscore','jquery.ui','tinymce','jquery.tinymce'],function(domReady, $, _) {
  var onReady = function() {
    function mail() {
      this.constructor = function(adress,object,body,action,tinyMce,data,checkbox) {
        this.adress = adress;
        this.object = object;
        this.body = body;
        this.action = action;
        this.data = data;
        this.tinyMce = tinyMce;
        this.checkbox = checkbox;
      },
      // set tinyMce
      this.setTinyMce = function(obj) {
        this.tinyMce = obj;
      },
      // set action
      this.setAction = function(val) {
        this.action = val;
      },
      // action on input adress
      this.actionAdress = function(id) {
        var This = $(id);
        This.on('change keyup paste',function(){
          var text = This.attr('value');
          var split = text.trim().split(/\s+/);
          var re =/^(([^<>()[\]\\.,;:\s@\"]+(\.[^<>()[\]\\.,;:\s@\"]+)*)|(\".+\"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/;

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
      },
      // return file adress action
      this.actionAdressOnLoad = function(email,id) {
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
      },
      // set custom adress from input
      this.setAdress = function(Class) {
        var This = $('.'+Class);
        var mails = [];
        This.each(function(){
          var data = $(this).data('mail');
          mails.push(data);
        })
        this.adress = mails;
      },
      /* get tinymce value method */
      this.tinyMceContent = function() {
        var content = this.tinyMce.activeEditor.getContent();
        this.body = content;
      },
      /* set checkbox */
      this.setCheckbox = function(Class) {
        var data = [];
        $(Class).each(function(){
          var This = $(this);
          var val = This.val();
          var check = This.is(':checked');
          if(check) {
            data.push({name:val,value:true});
            console.log("email"+val);
          }else{
            data.push({name:val,value:false});
          }
        })
        this.checkbox = data;
      },
      /* set object and body method */
      this.setObjectBody = function(object) {
        this.object = $(object).val();
      },
      /* get this .data */
      this.getData = function() {
        return this.data;
      },
      // sendMailData
      this.sendMailData = function(adress) {
        var data = new FormData();
        // check_actions required
        for(var i=0;i<this.checkbox.length;i++) {
          data.append(this.checkbox[i].name,this.checkbox[i].value);
          console.log('adding mails '+this.checkbox[i].name);
          console.log('adding mails '+this.checkbox[i].value);
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
    };
    /* init tinymce */
    tinymce.init({
      selector: '#mytextarea',
      plugins: "textcolor colorpicker link",
      //menubar: "insert",
      toolbar: "|forecolor backcolor link alignleft aligncenter alignright alignjustify |",
      target_list: false,
      init_instance_callback: insert_contents,
    });
    var lang_code = $('#fil_ariane').data('lang');
    var atp_mail = "";
    if(lang_code == 'fr') {
      atp_mail = "";
    }else if(lang_code == 'en') {
      atp_mail = "";
    }
    /*
    function insert_contents(inst) {
      inst.setContent('<p style="margin: 10px 0;"> </p><p style="margin: 10px 0;"><span style="color:#06144d"><span style="font-size:14px"> </span></span><span style="color:#06144d"><span style="font-size:14px">Vous êtes invité à participer au module de formation<b> GLOBAL DISRUPTIVE OPPORTUNITIES.</b></span></span></p><p style="margin: 10px 0;"><span style="color:#06144d"><span style="font-size:14px"> </span></span></p><p style="margin: 10px 0;"><span style="color:#06144d"><span style="font-size:14px"><b>Vous avez jusqu’au 15 octobre 2017 </b>pour compléter le module de formation.</span></span></p><p style="margin: 10px 0;"><span style="color:#06144d"><span style="font-size:14px">Ce module de formation est<b> obligatoire.</b></span></span></p><p style="margin: 10px 0;"><span style="color:#06144d"><span style="font-size:14px"> </span></span></p><p style="margin: 10px 0;"><span style="color:#06144d"><span style="font-size:14px">Un score de<b> 80% </b>minimum est requis pour valider le module de formation.</span></span></p><p style="margin: 10px 0;"><span style="color:#06144d"><span style="font-size:14px"> </span></span></p><p style="margin: 10px 0;"><span style="color:#06144d"><span style="font-size:14px">Pour accédez au module de formation GLOBAL DISRUPTIVE OPPORTUNITIES, veuillez cliquer sur le lien suivant : <a href="">Ligne Métier Marketing Retail</a></span></span></p>');
    }
    */
    function insert_contents(inst) {
      inst.setContent(atp_mail);
    }
    /* action on submit form */
    var submit = '#upload_form_participant';
    var mail_invite = new mail();
    mail_invite.actionAdress('#email_1');
    /* end file upload submit */
    $('#send_email').click(function(){
      /*check for errors */
      var lang=document.documentElement.lang;
      var erreurs_form=false;
      $('#error-field').css('display','none').html('');
      /* Check diffusion list */
      if($('input[class="checkbox_mail_field"]:checked').length==0) {
          if(lang=='fr'){
            $('#error-field').append('<p>Veuillez sélectionner un destinataire.</p>');
          }
          else if(lang=="cs"){
            $('#error-field').append('<p>Vyberte příjemce emailu. </p>');
          }
          else{
            $('#error-field').append('<p>Select a receiver for your email. </p>');
          }
          erreurs_form=true;
      }
      /* Check object */
      if(!$('#email_2').val()){
        if(lang=='fr'){
          $('#error-field').append("<p>L'objet du mail est obligatoire. </p>");
        }
        else if(lang=="cs"){
          $('#error-field').append('<p>Vyplňte předmět emailu</p>');
        }
        else{
          $('#error-field').append('<p>Field object of the email is mandatory. </p>');
        }
          erreurs_form=true;
      }
      /* Check Message */
      if(!$('#email_2').val()){
        if (lang=="fr"){
          $('#error-field').append('<p>Le corps du mail est obligatoire. </p>');
        }
        else if(lang=="cs"){
          $('#error-field').append('<p>Vyplňte text emailu</p>');
        }
        else{
          $('#error-field').append('<p>Field body of the email is mandatory. </p>');
        }
          erreurs_form=true;
      }
      if(erreurs_form){
      $('#error-field').css('display','block');
      }
      else{
        var submit = '#upload_form_participant';
        /* use invit class */
        var mail_invite = new mail();
        mail_invite.actionAdress('#email_1');
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
            $('.cell_title').addClass('not_margin_bottom');
            $('.pop_up_mail').addClass('is_show');
            $('#email_2').attr('value','');
            $('#email_2').attr('value','');
            $('.data_mail').parent().remove();
            $('html').scrollTop(0);
            tinyMCE.activeEditor.setContent('');
          }
        });
      }
    })
  };
  domReady(onReady);
  return {
      onReady: onReady
  };
})
