odoo.define('table_header_freeze.freeze_view', function (require) {
	"use strict";

	document.addEventListener('scroll', stickIt, true);
	
	function stickIt(event) {
		var orgElementPos = $('.original').offset();
		if($('.cloned').length == 0){
			var clone_children = $('.table_header_freeze table.o_list_view thead tr').children();
			var clone = $('.table_header_freeze table.o_list_view thead tr').addClass('original').clone().insertAfter('.table_header_freeze table.o_list_view thead tr').addClass('cloned').css('position','fixed').css('top','0').css('margin-top','0').css('z-index','1').removeClass('original').hide();
			var target_children = clone.children();
			clone.children().width(function(i,val) {
			    return clone_children.eq(i).width();
			});
		}
		if(orgElementPos){
	  		var orgElementTop = orgElementPos.top;  
		
			var offsetHeight_panel = $('.o_control_panel').offset();
	    	var offsetHeight_menu = document.getElementById('odooMenuBarNav').offsetHeight;
	    	var offsetHeight_footer = $('.table_header_freeze table.o_list_view tfoot').offset();
	    	var total_height = offsetHeight_menu+offsetHeight_panel.top + 80
	  		if (total_height >= (orgElementTop)) {
		  	  	var orgElement = $('.table_header_freeze table.o_list_view thead tr');
		    	var coordsOrgElement = orgElement.offset();
		  	 	var leftOrgElement = coordsOrgElement.left;  
		    	var widthOrgElement = orgElement.css('width');

			    $('.cloned').css('left',leftOrgElement+'px').css('top',total_height).css('width',widthOrgElement).show();
			    $('.table_header_freeze table.o_list_view thead tr.original').css('visibility','hidden');
		  	} else {
		    	$('.cloned').hide();
		    	$('.table_header_freeze table.o_list_view thead tr').css('visibility','visible');
		  	}
		  	// Arilgax
		  	if(offsetHeight_footer.top < $('.cloned').offset().top){
		  		$('.cloned').hide();
		  	}
	  	}
	}

});
