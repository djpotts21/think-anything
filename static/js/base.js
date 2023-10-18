$(document).ready(function () {
    $('.sidenav').sidenav({
        edge: 'right',
        preventScrolling: true,
        draggable: true
    });
    $('.modal').modal();
    $('.tooltipped').tooltip();
    $("#ConfirmPassword").on('keyup', function(){
      var password = $("#Password").val();
      var confirmPassword = $("#ConfirmPassword").val();
      if (password != confirmPassword)
          $("#CheckPasswordMatch").html("Password does not match !").css("color","white");
      else
          $("#CheckPasswordMatch").html("");
     });
});
// Hide flash messages after 5 seconds
$('#flash-selector').delay(5000).fadeOut('slow');

// Limit file upload to 32MB for IMGBB Limit

$(function() {
    $("#file").on("change", function() {
      if (this.files && this.files.length == 1 && this.files[0].size > 32000000) {
        $(":button").attr('disabled','disabled');
        alert("The file size must be no more than " + parseInt(32000000 / 1024 / 1024) + "MB");
        return false;
      }
      else {
        $(":button").removeAttr('disabled');
      }
      return true;
    });
  });