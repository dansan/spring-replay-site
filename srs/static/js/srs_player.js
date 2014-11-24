/*
 * This file is part of the "spring relay site / srs" program. It is published
 * under the GPLv3.
 * 
 * Copyright (C) 2014 Daniel Troeder (daniel #at# admin-box #dot# com)
 * 
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */


var accountid = $( "meta[name='accountid']" ).attr( "content" );

var playerrating_table = $( "#playerrating-table" ).dataTable({
	"bAutoWidth": false,
	"bLengthChange": false,
	"bFilter": false,
	"bPaginate": false,
	"bSort": false,
	"bInfo": false,
	"bProcessing": true,
	"bServerSide": true,
	"sAjaxSource": Django.url('ajax_playerrating_tbl_src', accountid),
});

var winloss_table = $( "#winloss-table" ).dataTable({
	"bAutoWidth": false,
	"bLengthChange": false,
	"bFilter": false,
	"bPaginate": false,
	"bSort": false,
	"bInfo": false,
	"bProcessing": true,
	"bServerSide": true,
	"sAjaxSource": Django.url( "ajax_winloss_tbl_src", accountid ),
});

var playerreplays_table = $( "#playerreplays-table" ).dataTable({
	"bAutoWidth": false,
	"iDisplayLength": 25,
	"aaSorting": [[ 1, "desc" ]],
	"bDeferRender": true,
	"bPaginate": true,
	"sPaginationType": "bootstrap",
	"bScrollCollapse": true,
	"bProcessing": true,
	"bServerSide": true,
	"sAjaxSource": Django.url( "ajax_playerreplays_tbl_src", accountid ),
	"bRegex" : true,
	"aoColumns": [
	              null,
	              { "bSearchable": false},
	              { "bSearchable": false, "bSortable": false },
	              { "bSearchable": false, "bSortable": false },
	              { "bSearchable": false, "bSortable": false },
	              { "bSearchable": false, "bSortable": false },
	              { "bSearchable": false, "bSortable": false },
	              ],
	  "aoColumnDefs": [
       {
		  "aTargets": [ 0 ],
		  "mData": 0,
		  "mRender": function ( data, type, full ) {
			  if ( data == "" ) {
				  data = "no name"
			  }
			  return '<a href="' + Django.url('replay_detail', full[7] ) + '">' + data + '</a>';
		  }
	  },
	  {
		  "aTargets": [ 1 ],
		  "mData": function ( data, type, val ) {
    		  if (type === "set") {
    	            data[1] = moment(data[1]);
    	            return;
    	        }
    	        else if (type === "display") {
    	            return data[1].format( "YYYY-MM-DD HH:mm" );
    	        }
	          return data[1];
    	  },
		  "mRender": function ( data, type, full ) {
			  return data;
		  }
	  }],
});

// destroy ratinghistory modal on hide, so it reloads each time (possibly with a new url)
$('body').on('hidden.bs.modal', '.modal', function () {
	console.log($(this));
    $( this ).removeData('bs.modal');
});

// show "loading" image until graph has been loaded from SLDB
function fix_size( alt_txt ) {
    $( 'img[id="loader_img"]' ).remove();
    $( 'img[id="ts_graph"]' ).attr("height", 512).attr("width", 1024);
}
