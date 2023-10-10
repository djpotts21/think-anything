$(document).ready(function(){
    $('.sidenav').sidenav({
        edge: 'right',
        preventScrolling: true,
        draggable: true
    });
  });
  // Hide flash messages after 5 seconds
  $('#flash-selector').delay(5000).fadeOut('slow');