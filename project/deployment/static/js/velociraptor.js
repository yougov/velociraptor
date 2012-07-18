$(document).ready(function() {
    $(".chzn-select").chosen({ search_contains: true });

    // Go to new page when selecting from the nav Chosen dropdowns.
    $('.nav-select').change(function(ev){
        window.location = $(this).val();
    });
});
