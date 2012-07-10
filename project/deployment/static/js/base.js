$(document).ready(function() {
    $(".chzn-select").chosen();

    var swarmlist = $('#swarm-list');
    swarmlist.change(function(ev){
        window.location = $(this).val();
      });
});
