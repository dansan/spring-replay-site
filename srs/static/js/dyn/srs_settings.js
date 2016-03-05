/*
 * This file is part of the "spring relay site / srs" program. It is published
 * under the GPLv3.
 * 
 * Copyright (C) 2016 Daniel Troeder (daniel #at# admin-box #dot# com)
 * 
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

function toggle_game_choice( checkbox ) {
	if ( checkbox.checked ) {
		$( "#id_game_choice" ).attr( "disabled", "" );
	} else {
		$( "#id_game_choice" ).removeAttr( "disabled" );
	}
}

toggle_game_choice( $( "input[id='id_auto']" )[0] );
