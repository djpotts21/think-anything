$(document).ready(function () {
  $('.sidenav').sidenav({
    edge: 'right',
    preventScrolling: true,
    draggable: true
  });
  $('.modal').modal();
  $('select').formSelect();
  $('.tooltipped').tooltip();
  $("#ConfirmPassword").on('keyup', function () {
    var password = $("#Password").val();
    var confirmPassword = $("#ConfirmPassword").val();
    if (password != confirmPassword)
      $("#CheckPasswordMatch").html("Password does not match !").css("color", "white");
    else
      $("#CheckPasswordMatch").html("");
  });
  $('input[id="water_log"]').val(function (i, val) {
    return parseInt(val.replace('+', '').replace('-', ''));
  });
  $("#messages").scrollTop($("#messages").prop("scrollHeight"));

});
// Plus and minus buttons for quantity input 
jQuery(document).ready(function () {
  // This button will increment the value
  $('[data-quantity="plus"]').click(function (e) {
    // Stop acting like a button
    e.preventDefault();
    // Get the field name
    fieldName = $(this).attr('data-field');
    // Get its current value
    var currentVal = parseInt($('input[name=' + fieldName + ']').val());
    // If is not undefined
    if (!isNaN(currentVal)) {
      // Increment
      $('input[name=' + fieldName + ']').val(currentVal + 1);
    } else {
      // Otherwise put a 0 there
      $('input[name=' + fieldName + ']').val(0);
    }
  });
  // This button will decrement the value till 0
  $('[data-quantity="minus"]').click(function (e) {
    // Stop acting like a button
    e.preventDefault();
    // Get the field name
    fieldName = $(this).attr('data-field');
    // Get its current value
    var currentVal = parseInt($('input[name=' + fieldName + ']').val());
    // If it isn't undefined or its greater than 0
    if (!isNaN(currentVal) && currentVal > 0) {
      // Decrement one
      $('input[name=' + fieldName + ']').val(currentVal - 1);
    } else {
      // Otherwise put a 0 there
      $('input[name=' + fieldName + ']').val(0);
    }
  });
});


// Hide flash messages after 5 seconds
  $('.row.flashes').delay(5000).fadeOut(2000, function() { $(this).remove(); });

// Limit file upload to 32MB for IMGBB Limit

$(function () {
  $("#file").on("change", function () {
    if (this.files && this.files.length == 1 && this.files[0].size > 32000000) {
      $(":button").attr('disabled', 'disabled');
      alert("The file size must be no more than " + parseInt(32000000 / 1024 / 1024) + "MB");
      return false;
    } else {
      $(":button").removeAttr('disabled');
    }
    return true;
  });
});