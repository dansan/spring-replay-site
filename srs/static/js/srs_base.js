/*
 * This file is part of the "spring relay site / srs" program. It is published
 * under the GPLv3.
 * 
 * Copyright (C) 2014 Daniel Troeder (daniel #at# admin-box #dot# com)
 * 
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

$('#select-player').selectize({
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
    onChange: function(){
        window.location = '/player/' + this.items[0];
    }
});
