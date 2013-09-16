$(document).ready(function() {
	$(".clickme_winner").click(function() {
		$(".blind_winner").show("blind", {}, 1000);
	});
});
$(document).ready(function() {
	$(".clickme_mapoptions").click(function() {
		$(".blind_mapoptions").show("blind", {}, 1000);
	});
});
$(document).ready(function() {
	$(".clickme_modoptions").click(function() {
		$(".blind_modoptions").show("blind", {}, 1000);
	});
});
$(document).ready(function() {
	$('tr.linehl').hover(function() {
		$(this).css("background-color", "rgb(224, 224, 224)");
	}, function() {
		$(this).css("background-color", "inherit");
	});
});
