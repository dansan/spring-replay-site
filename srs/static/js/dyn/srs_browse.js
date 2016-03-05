/*
 * This file is part of the "spring relay site / srs" program. It is published
 * under the GPLv3.
 * 
 * Copyright (C) 2016 Daniel Troeder (daniel #at# admin-box #dot# com)
 * 
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

// initialize DataTable
var browse_table = $( "#browse-table" ).dataTable({
	"bAutoWidth": false,
	"iDisplayLength": 25,
	"aaSorting": [[ 1, "desc" ]],
	"bPaginate": true,
	"sPaginationType": "bootstrap",
	"bScrollCollapse": true,
	"bProcessing": true,
	"bServerSide": true,
	"sAjaxSource": Django.url( "browse_tbl_src" ),
	"bRegex" : true,
	"aoColumns": [
	              null,
	              { "bSearchable": false },
	              null,
	              { "bSearchable": false },
	              { "bSearchable": false }
	              ],
	"aoColumnDefs": [
         {
		  "aTargets": [ 0 ],
		  "mData": 0,
		  "mRender": function ( data, type, full ) {
			  if ( data == "" ) {
				  data = "no name";
				  }
			  console.log( )
			  return '<a href="' + Django.url('replay_detail', full[5] ) + '"><img class="img-rounded" height=32 itemprop="image" src="' + Django.context.STATIC_URL + 'maps/' + full[6] + '_home.jpg" alt="pic of map ' + full[6] + '"/> ' + data + '</a>';
			  }
         },
         {
		  "aTargets": [ 1 ],
		  "mData": function ( data, type, val ) {
    		  if (type === "set") {
    	            data[1] = moment(data[1]);
    	            return;
    	            } else if (type === "display") {
    	            	return data[1].format( "YYYY-MM-DD HH:mm" );
	            	}
    		  return data[1];
    		  },
    		  "mRender": function ( data, type, full ) {
    			  return data;
    			  }
	     }],
//	              "oSearch": {"sSearch": "Global search"}

});
$( "div#browse-table_filter.dataTables_filter" ).attr("title", "Search title and game columns")
$( "div#browse-table_filter.dataTables_filter > label" ).wrapInner( '<h4></h4>' );
$( "div#browse-table_filter.dataTables_filter input" ).addClass( "form-control" );
$( "div#browse-table_length.dataTables_length > label" ).wrapInner( "<h4></h4>" );
$( "div#browse-table_length.dataTables_length select" ).addClass( "form-control" );

var oSettings      = browse_table.dataTable().fnSettings();
var aoServerParams = oSettings.aoServerParams;

function removeFilter( btngrp ) {
	for (index = 0; index < aoServerParams.length; ++index) {
		if ( aoServerParams[index].hasOwnProperty("sName") ) {
			if ( aoServerParams[index]["sName"] == btngrp ) {
				// remove only entries from same filter group
				aoServerParams.splice(index, 1);
			}
		}
	}
}

function addFilter( btngrp, btnid ) {
	var index;
	// remove previous entry
	removeFilter( btngrp );
	// add filter
	aoServerParams.push({
        "sName": btngrp,
        "fn": function ( aoData ) {
            aoData.push({
                "name": "btnfilter " + btngrp,
                "value":  btnid
            });
        }
	});
	browse_table.dataTable().fnDraw();
}

// date range widget
var daterangepicker = $('.mydatepicker')
var oldestreplay = $( 'meta[name="oldestreplay"]' ).attr( "content" );
var newestreplay = $( 'meta[name="newestreplay"]' ).attr( "content" );
daterangepicker.click( function( event ) {
	event.preventDefault();
	});
function daterange_action(start, end, label) {
	$( "a[id^='date']" ).removeClass("active");
	daterangepicker.button('toggle');
	$( "#datepicker_label" ).html( "<small>" + start.format("YYYY-MM-DD") + "<br/> - " + end.format("YYYY-MM-DD") + "</small>" );
	addFilter("date", "date daterange " + start.unix() + " " + end.unix() );
}
daterangepicker.daterangepicker(
		{
			format: 'YYYY-MM-DD',
			startDate: moment(newestreplay).subtract('days', 7),
			endDate: moment(newestreplay),
			minDate: moment(oldestreplay),
			maxDate: moment(newestreplay),
			showDropdowns: true
		},
		daterange_action
		);

// search field for maps
var select_map = $( '#select-map' ).selectize({
    valueField: 'id',
    labelField: 'name',
    searchField: 'name',
    create: false,
    render: {
        option: function(item, escape) {
            return '<div>' + escape(item.name) + '<span class="pull-right"><img src="' + Django.context.STATIC_URL + 'maps/' + escape(item.name) + '_home.jpg" height="35"/></span></div>' ;
        }
    },
    load: function(query, callback) {
        if (!query.length) return callback();
        $.ajax({
            url: '/ajax_map_lookup/' + encodeURIComponent(query) + '/',
            type: 'GET',
            error: function() {
                callback();
            },
            success: function(res) {
                callback(JSON.parse(res).maps);
            }
        });
    },
    onChange: function() {
    	if (this.items[0]) {
	    	$( "a[id^='map']" ).removeClass("active");
	    	addFilter("map", "map " + this.items[0])
    	}
    }
});

var selectize_map = select_map[0].selectize;
// list of selected players
var selected_players = new Object();
// search field for players
var select_player_filter = $( '#select-player-filter' ).selectize({
    valueField: 'accountid',
    labelField: 'player__name',
    searchField: 'player__name',
    create: false,
    render: {
        option: function(item, escape) {
            return '<div class="name">' + escape(item.player__name) + '</div>';
        }
    },
    load: function(query, callback) {
        if (!query.length) return callback();
        $.ajax({
            url: '/ajax_player_lookup/' + encodeURIComponent(query) + '/',
            type: 'GET',
            error: function() {
                callback();
            },
            success: function(res) {
                callback(JSON.parse(res).player);
            }
        });
    },
    onDropdownOpen: function(dropdown){
    	$( '#playerfilterpanel' ).attr("style", "height: 280px");
    },
    onChange: function(value){
        if (value) {
        	var item = $( "#select-player-filter-btn-group div.item" );
        	var name = item[0].innerText;
        	// don't add, if already in list
        	if (!selected_players.hasOwnProperty(value)) {
        		// add to selected_players
        		selected_players[value] = name;
        		// add entry below input
        		$( "#selectedplayers" ).append( '<li class="list-group-item">' + name + '<span class="pull-right"><button type="button" class="btn btn-default btn-sm selectedplayer" id="spec' + value + '" data-toggle="button">spec <span class="ionicons ion-android-close"></span></button> <button type="button" class="btn btn-default btn-sm selectedplayer" id="rm' + value + '">remove <span class="glyphicon glyphicon-remove-circle"></span></button></span>' );
        		// add to DataTables filter list and redraw table
		    	addFilter( "player" + value, "player " + value);
		    	// remove player button
		    	var rm_player   = $( 'button[id="rm'   + value + '"]' );
		    	rm_player.click( function( event ) {
		    		event.preventDefault();
		    		// remove from selected_players
		    		if ( selected_players.hasOwnProperty( value ) ) {
	    					delete selected_players[ value ];
	    			}
		    		// remove from DataTables filter list and redraw table
		    		removeFilter( "player" + value );
		    		browse_table.dataTable().fnDraw();
		    		// remove entry from page
		    		$( this ).parents( "li.list-group-item" ).remove();
		    	});
		    	// spec toggle button
		    	var spec_player = $( 'button[id="spec' + value + '"]' );
		    	spec_player.click( function( event ) {
		    		event.preventDefault();
		    		if ( $( this ).hasClass( "active" ) ) {
		    			// button WAS active, will be deactivated after this callback
		    			$( this ).html( 'spec <span class="ionicons ion-android-close"></span>' );
		    			selected_players[ value ] = name;
		    			removeFilter( "player" + value );
		    			addFilter( "player" + value, "player " + value );
		    		} else {
		    			// button WAS passive, will be active (pressed in) after this callback
		    			$( this ).html( 'spec <span class="ionicons ion-checkmark"></span>' );
		    			selected_players[ value ] = name + " spec";
		    			removeFilter( "player" + value );
		    			addFilter( "player" + value, "player " + value + " spec" );
		    		}
		    	});
        	}
    	}
    }
});

var selectize_player_filter = select_player_filter[0].selectize;

// cache some selectors
var gameversion0       = $( "a[id='gameversion 0']" )
var gameversionbtn     = $( "a[id='gameversionbtn']" );
// save original button texts
var ddbtn_autohost_str = $( "#btn_autohost" ).html();
var ddbtn_uploader_str = $( "#btn_uploader" ).html();
var gameversion0txt    = gameversion0.html();

// use when game is set
function set_gameversionbtn_url() {
	var game_id = $( "a.browse_filter.active[id^='game']" ).attr( "id" ).split( " " )[1];
	gameversionbtn.attr( "href", Django.url( 'gamerelease_modal', game_id ) );
}

// apply to almost all filter buttons and the autohost & uploader dropdowns
$( ".browse_filter" ).click( function( event ) {
	event.preventDefault();
	// add filter from button to GET parameters
	var btnid = $( this ).attr( "id" );
	var btngrp = btnid.split( " " )[0];
	var val = btnid.split( " " )[1];
	//console.log( "btnid: '" + btnid + "' btngrp: '" + btngrp + "' val: '" + val + "'");
	if ( btngrp == "autohost" || btngrp == "uploader" ) {
		var ddbtn = $( "#btn_" + btngrp );
		ddbtn.html( eval("ddbtn_" + btngrp + "_str") + ' <span class="pull-right">' + val + '</span>' );
	} else {
		// deactivate all buttons in this btngrp
		$( "a[id^='" + btngrp + "']" ).removeClass("active");
		// activate used button
		$( this ).button('toggle');
	}
	if ( btngrp == "date" ) {
		$( "#datepicker_label" ).html( " date range" );
	}
	if ( btngrp == "map" ) {
		selectize_map.clear();
	}
	if ( btngrp == "game" ) {
		// new game filter chosen, no specific version
		removeFilter( "gameversion" );
		gameversion0.addClass( "disabled" );
		gameversion0.html( gameversion0txt );
		if ( val == "0" ) {
			gameversionbtn.attr( "href", "#" );
			gameversionbtn.addClass( "disabled" );
		} else {
			gameversionbtn.attr( "href", Django.url( 'gamerelease_modal', val ) );
			gameversionbtn.removeClass( "disabled" );
		}
	}
	if ( btnid == "gameversion 0" ) {
		gameversion0.html( gameversion0txt );
		set_gameversionbtn_url();
		gameversionbtn.removeClass( "disabled" );
	}
	addFilter(btngrp, btnid);
});

// clear autohost & uploader dropdowns
function ddn_clear( ddn ) {
	var btnid = ddn.attr( "id" );
	var btngrp = btnid.split( " " )[0];
	var val = btnid.split( " " )[1];
	var ddbtn = $( "#btn_" + btngrp );
	ddbtn.html( eval("ddbtn_" + btngrp + "_str") );
	removeFilter( btngrp );
}

// clear autohost & uploader dropdowns
$( ".ddn_clear" ).click( function( event ) {
	event.preventDefault();
	ddn_clear( $( this ) );
	browse_table.dataTable().fnDraw();
});

// clear all
$( "a[id='clear_all']" ).click( function( event ) {
	event.preventDefault();
	removeFilter( "date" );
	removeFilter( "map" );
	selectize_map.clear();
	removeFilter( "tag" );
	removeFilter( "game" );
	gameversionbtn.attr( "href", "#" );
	gameversionbtn.addClass( "disabled" );
	removeFilter( "gameversion" );
	gameversion0.addClass( "disabled" );
	gameversion0.html( gameversion0txt );
	// player
	for (key in selected_players) {
		removeFilter( "player" + key );
		delete selected_players[ key ];
	}
	$( "ul[id='selectedplayers'] li" ).remove();
	selectize_player_filter.clear();
	// autohost & uploader
	var ddns = $( ".ddn_clear" );
	for (var i=0; i<ddns.length; i++) {
		ddn_clear( $( ddns[i] ) );
	}
	// deselect all filter buttons
	$( "a.browse_filter" ).removeClass("active");
	// select all "Clear filter" buttons
	$( "a.browse_filter[id$='0']" ).addClass("active");
	// close all drawers
	$( "div.panel-collapse[id^='collapse']" ).removeClass( "in" );
	// redraw table
	browse_table.dataTable().fnDraw();
});

// apply filters from GET arguments (passed through URL to view to <meta> tags)
var bfilter = $( 'meta[name="bfilter"]' );
var map_name = $( 'meta[name="map_name"]' ).attr( "content" );
var game_abbreviation = $( 'meta[name="game_abbreviation"]' ).attr( "content" );
var ran_once = false;
if (ran_once == false) {
	ran_once = true;
	for (index = 0; index < bfilter.length; ++index) {
		var filter_name  = bfilter[index].content.split(" ")[0];
		var filter_value = bfilter[index].content.split(" ")[1];
		if ( filter_name == "map" ) {
			selectize_map.addOption({"id": filter_value, "name": map_name})
			selectize_map.setValue( filter_value );
		} else if (filter_name == "date" ) {
			var sdate = filter_value.split("_")[1];
			daterange_action(moment(sdate + " 00:00:00"), moment(sdate + " 23:59:59"));
		} else {
			if ( filter_name == "autohost" || filter_name == "uploader" ) {
				var ddbtn = $( "#btn_" + filter_name );
				ddbtn.html( eval("ddbtn_" + filter_name + "_str") + ' <span class="pull-right">' + filter_value + '</span>' );
			} else {
				// activate button for this filter
				$( "a.browse_filter[id='" + filter_name + " " + filter_value + "']" ).addClass( "active" );
				// deactivate clear button for this filter group
				$( "a[id='" + filter_name + " 0']" ).removeClass("active");
			}
			if (filter_name == "gameversion" ) {
				set_gameversionbtn_url();
				gameversionbtn.removeClass( "disabled" );
				set_gameversion( null, filter_value, game_abbreviation );
			}
			addFilter( filter_name, filter_name + " " + filter_value )
		}
		$( "#collapse_" + filter_name ).addClass( "in" );
	}
}

// destroy gameversion modal on hide, so it reloads each time (possibly with a new url)
$('body').on('hidden.bs.modal', '.modal', function () {
	console.log($(this));
    $( this ).removeData('bs.modal');
});

// gameversion filter from modal or GET argument
function set_gameversion( event, gvid, name ) {
	if (event != null) {
		event.preventDefault();
		$( ".modal" ).modal('hide');
	}
	//set_gameversion_( gvid, name );
	addFilter( "gameversion", "gameversion " + gvid );
	gameversion0.html( gameversion0txt + " (" + name + ")" );
	gameversion0.removeClass( "disabled" );
	gameversion0.removeClass( "active" );	
}
