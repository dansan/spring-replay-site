/*
 * This file is part of the "spring relay site / srs" program. It is published
 * under the GPLv3.
 * 
 * Copyright (C) 2016 Daniel Troeder (daniel #at# admin-box #dot# com)
 * 
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

$( "#more_replays_btn" ).click( function( event ) {
        event.preventDefault();
});

$( "#more_replays_btn" ).click( function() {
	var range_div     = $( ".range" );
	var range_end_div = $( ".range_end" );
	var range         = range_div.attr( "id" );
	var range_end     = range_end_div.attr( "id" );
	var fill_me = $( ".fill_me" );
	if ( ! fill_me.get(0) ) {
		$( ".more_replays_div" ).before( '<div class="fill_me"></div>' );
		fill_me = $( ".fill_me" );
	}
	fill_me.load( Django.url('srs/index_replay_range', range_end, game_pref) );
	range_div.remove()
	range_end_div.remove()
	fill_me.removeClass( "fill_me" );
});
