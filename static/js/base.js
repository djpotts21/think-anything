$(document).ready(function () {
    $('.sidenav').sidenav({
        edge: 'right',
        preventScrolling: true,
        draggable: true
    });
    $('.modal').modal();
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