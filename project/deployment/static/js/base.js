$(document).ready(function() {
    $(".chzn-select").chosen({ search_contains: true });

    var swarmlist = $('#swarm-list');
    swarmlist.change(function(ev){
        window.location = $(this).val();
      });
});
