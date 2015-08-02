var api_url = 'https://swarfarm.com/api/';

//Initialize all bootstrap tooltips and popovers
$(function () {
    $('[data-toggle="tooltip"]').tooltip()
});

$(function () {
  $('[data-toggle="popover"]').popover({
      html:true
  })
});

//Modal management scripts
$('#addMonsterModal').on('shown.bs.modal', function () {
    $('#id_monster-autocomplete').focus()
});

//Automatically set attributes based on monster info
$('#id_monster-autocomplete').bind('selectChoice',
    function(e, choice, autocomplete) {
        var monster_id = choice[0].dataset['value'];

        $.getJSON(api_url + 'bestiary/' + monster_id, function(result){
            //Set stars
            $('#id_stars').rating('rate', result[0].fields['base_stars']);
            //Set fodder
            if (result[0].fields['archetype'] == 'material') {
                $('#id_priority').val('0');
                $('#id_fodder').prop('checked', true);
            }
        });
    }
);

//Update filter buttons on page load
var monster_table = $('#monster_table');
var filter_buttons = $('button.filter');
var active_filter_class = 'active';

monster_table.tablesorter({
    widgets: ['filter', 'saveSort'],
    ignoreCase: true,
    widgetOptions: {
        filter_columnFilters: true,
        filter_reset: 'button.reset',
        filter_external : '.search',
        filter_ignoreCase : true,
        filter_liveSearch : true,
        filter_searchDelay : 300,
        filter_saveFilters : true,
        filter_searchFiltered : true
    }
});

//Get list of current filters and set buttons properly
var current_filters = $.tablesorter.getFilters(monster_table);

if (current_filters) {
    filter_buttons.each(function () {
        var filter_col = $(this).data('filter-column');
        var filter_text = $(this).data('filter-text');

        if (current_filters[filter_col].indexOf(filter_text) > -1) {
            $(this).toggleClass(active_filter_class, true);
        }
    });
}

//Toggle text in filter field when button is pressed
filter_buttons.click(function() {
    $( this ).toggleClass(active_filter_class);

    var filters = $('#monster_table').find('input.tablesorter-filter'),
        col = $(this).data('filter-column'),
        txt = $(this).data('filter-text'),
        cur = filters.eq(col).val(),
        mult, i;

    if (cur && txt !== '') {
        mult = cur.split('|');
        i = $.inArray(String(txt), mult);
        if (i < 0) {
            mult.push(String(txt));
        } else {
            mult.splice(String(i),1);
        }
        txt = mult.join('|');
    }
    filters.eq(col).val(txt).trigger('search', false);
});

//Reset filters
$('button.reset').click(function() {
    $('button.filter').toggleClass(active_filter_class, false);
    $('#monster_table').trigger('saveSortReset').trigger("sortReset");
});